import collections
import datetime
import enum
import functools
import time
import re
import os
import sys
import locale
import uuid
import subprocess
import json
import decimal
import slugify as python_slugify
import sqlalchemy as sa
import sqlalchemy.orm.exc
import magic
import colander
import yaml
import pym.exc


ENV_DEVELOPMENT = 'development'
ENV_PRODUCTION = 'production'


RE_NAME_CHARS = re.compile('^[-a-zA-Z0-9_][-a-zA-Z0-9_.]*$')
"""
Valid characters for a filename. Filename is disallowed to start with a dot.
"""

RE_INVALID_FS_CHARS = re.compile(r'[\x00-\x1f\x7f]+')
"""
Invalid characters for a filename in OS filesystem, e.g. ext3.

- NULL byte
- Control characters 0x01..0x1f (01..31)
- Escape Character 0x7f (127)
"""

RE_BLANKS = re.compile('\s+')
RE_LEADING_BLANKS = re.compile('^\s+')
RE_TRAILING_BLANKS = re.compile('\s+$')


_CMD_SASSC = os.path.abspath(os.path.join(os.path.dirname(__file__),
    '..', 'bin', 'sassc'))
"""
Command-line to call sassc.
"""

_ = lambda s: s


RE_INTERVAL_DATETIME = re.compile(
    r'P'
    r'(?:(?P<years>\d+(?:[.]\d+)?)Y)?'
    r'(?:(?P<months>\d+(?:[.]\d+)?)M)?'
    r'(?:(?P<weeks>\d+(?:[.]\d+)?)W)?'
    r'(?:(?P<days>\d+(?:[.]\d+)?)D)?'
    r'(?:T'
    r'(?:(?P<hours>\d+(?:[.]\d+)?)H)?'
    r'(?:(?P<minutes>\d+(?:[.]\d+)?)M)?'
    r'(?:(?P<seconds>\d+(?:[.]\d+)?)S)?'
    r')?'
    r'$'
)


class Enum(enum.Enum):
    @classmethod
    def as_choices(cls, translate=None):
        """
        Returns members as list of 2-tuples suitable as choices for HTML select
        lists.

        Tuple[0] is the name of the member as string, and tuple[1] is its value.

        :param translate: Optional translation function. Assumes, member's value
            is a translation string.
        :return: Members as list of 2-tuples
        """
        if translate:
            return [(name, translate(member.value))
                for name, member in cls.__members__.items()]
        else:
            return [(name, member.value)
                for name, member in cls.__members__.items()]


class JsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


json_serializer = functools.partial(
    json.dumps,
    sort_keys=False,
    indent=2,
    ensure_ascii=False,
    cls=JsonEncoder
)

json_deserializer = json.loads


# Init YAML to dump an OrderedDict like a regular dict, i.e.
# without creating a specific object tag.
def _represent_ordereddict(self, data):
    return self.represent_mapping('tag:yaml.org,2002:map', data.items())

yaml.add_representer(collections.OrderedDict, _represent_ordereddict)


def trim_blanks(s):
    """
    Removes leading and trailing whitespace from string.
    """
    s = RE_LEADING_BLANKS.sub('', s)
    s = RE_TRAILING_BLANKS.sub('', s)
    return s


def is_string_clean(s):
    """
    Checks whether string has leading/trailing whitespace or illegal chars.
    """
    if RE_LEADING_BLANKS.search(s):
        return False
    if RE_TRAILING_BLANKS.search(s):
        return False
    if RE_INVALID_FS_CHARS.search(s):
        return False
    return True


def clean_string(s):
    """
    Cleans string by removing leading and trailing whitespace, illegal chars and
    folding consecutive whitespace to a single space char.
    """
    s = trim_blanks(s)
    s = RE_BLANKS.sub(' ', s)
    s = RE_INVALID_FS_CHARS.sub('', s)
    return s


def slugify(s, force_ascii=False, **kw):
    """
    Converts string into a 'slug' for use in URLs.

    Since nowadays we can use UTF-8 characters in URLs, we keep those intact,
    and just replace white space with a dash, except when you force ASCII by
    setting that parameter.

    If you ``force_ascii``, we use
    `python-slugify <https://github.com/un33k/python-slugify>`_ to convert the
    string. Additional keyword arguments are passed.

    We do not encode unicode in UTF-8 here, since most web frameworks do that
    transparently themselves.

    :param s: The string to slugify.
    :param force_ascii: If False (default) we allow unicode chars.
    :param **kw: Additional keyword arguments are passed to python-slugify.
    :return: The slug, still a unicode string but maybe just containing ASCII
        chars.
    """
    s = clean_string(s)
    s = RE_BLANKS.sub('-', s)
    if force_ascii:
        s = python_slugify.slugify(s, **kw)
    return s


class FileUploadTmpStoreFileSystem(object):

    def __init__(self, rootdir, timeout):
        """
        Temporary storage for uploaded files in the filesystem.

        :param rootdir: All files are stored here
        :param timeout; Seconds after which uploaded files are automatically
            purged,
        """
        self.rootdir = rootdir
        if not os.path.exists(rootdir):
            os.mkdir(rootdir)
        self.timeout = timeout
        self.chunk_size = 10240
        self.json_opts = dict(
            ensure_ascii=False
        )
        self.mime = magic.Magic(mime=True)

    def save(self, filename, fh_uploaded):
        """
        Saves an uploaded file in temporary store.

        :param filename: The file name
        :param fh_uploaded: File-like object of the uploaded file; must provide
            methods like read() etc.
        :return: Filename of the temporary file
        """
        tmpfilename = uuid.uuid4().hex
        fn_data = os.path.join(self.rootdir, tmpfilename)
        fn_rc = os.path.join(self.rootdir, tmpfilename) + '.rc'
        rc = {
            'filename': filename
        }
        with open(fn_data, 'wb') as fh:
            while True:
                x = fh_uploaded.read(self.chunk_size)
                if not x:
                    break
                fh.write(x)
        rc['mime_type'] = self.mime.from_file(fn_data.encode('utf-8')) \
            .decode('utf-8')
        rc['size'] = os.path.getsize(fn_data)
        rc['tmpfilename'] = tmpfilename
        with open(fn_rc, 'w', encoding='utf-8') as fh:
            json.dump(rc, fh, **self.json_opts)
        return rc

    def load(self, tmpfilename):
        fn_data = os.path.join(self.rootdir, tmpfilename)
        with open(fn_data, 'rb') as fh:
            x = fh.read()
        return x

    def open(self, tmpfilename):
        """
        Returns settings and an opened file handle

        DO NOT FORGET TO CLOSE THE FILE HANDLE AFTER USE!
        """
        fn_data = os.path.join(self.rootdir, tmpfilename)
        fn_rc = os.path.join(self.rootdir, tmpfilename) + '.rc'
        with open(fn_rc, 'r', encoding='utf-8') as fh:
            rc = json.load(fh)
        fh = open(fn_data, 'rb')
        return rc, fh

    def delete(self, tmpfilename):
        fn_data = os.path.join(self.rootdir, tmpfilename)
        fn_rc = os.path.join(self.rootdir, tmpfilename) + '.rc'
        try:
            os.remove(fn_data)
        except OSError:
            pass
        try:
            os.remove(fn_rc)
        except OSError:
            pass

    def purge(self, timeout=None):
        if not timeout:
            timeout = self.timeout
        now = time.time()
        ff = os.listdir(self.rootdir)
        for f in ff:
            if f.endswith('.rc'):
                continue
            fn_data = os.path.join(self.rootdir, f)
            if now - timeout > os.path.getctime(fn_data):
                self.delete(f)


def interval2timedelta(v):
    v = v.replace(',', '.').upper()
    m = RE_INTERVAL_DATETIME.match(v)
    if not m:
        raise ValueError
    if not m.groups():
        raise ValueError
    d = m.groupdict()

    def g(x):
        v = d.get(x, 0)
        if v is None:
            v = 0
        else:
            v = float(v)
        return v

    days = g('years') * 365.25 \
        + g('months') * (365.25 / 12.0) \
        + g('weeks') * 7 \
        + g('days')
    hours = g('hours')
    minutes = g('minutes')
    seconds = g('seconds')
    return datetime.timedelta(
        days=days, hours=hours, minutes=minutes, seconds=seconds
    )


class EmailValidator(colander.Regex):

    def __init__(self, msg=None):
        if msg is None:
            msg = _("Invalid email address")
        super().__init__(
            '(?i)^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,4}$',
            msg=msg
        )

    def __call__(self, node, value):
        lcv = value.lower()
        if lcv.endswith('@localhost') or lcv.endswith('@localhost.localdomain'):
            return
        super().__call__(node, value)


def compile_sass(in_, out):
    resp = JsonResp()
    # in_ is string, so we have one input file
    # Convert it into list
    if isinstance(in_, str):
        infiles = [safepath(in_)]
        # in_ is str and out is string, so treat out as file:
        # Build list of out filenames.
        if isinstance(out, str):
            outfiles = [safepath(out)]
    else:
        infiles = [safepath(f) for f in in_]
        # in_ is list and out is string, so treat out as directory:
        # Build list of out filenames.
        if isinstance(out, str):
            outfiles = []
            out = safepath(out)
            for f in in_:
                bn = os.path.splitext(os.path.basename(f))[0]
                outfiles.append(os.path.join(out, bn) + '.css')
        # in_ and out are lists
        else:
            outfiles = [safepath(f) for f in out]
    for i, inf in enumerate(infiles):
        # noinspection PyUnboundLocalVariable
        outf = outfiles[i]
        if not os.path.exists(inf):
            raise pym.exc.SassError("Sass infile '{0}' does not exist.".format(inf))
        result = compile_sass_file(inf, outf)
        if not result is True:
            resp.error("Sass compilation failed for file '{0}'".format(inf))
            resp.add_msg(dict(kind="error", title="Sass compilation failed",
                text=result))
            continue
        resp.ok("Sass compiled to outfile '{0}'".format(outf))
    if not resp.is_ok:
        raise pym.exc.SassError("Batch compilation failed. See resp.", resp)
    return resp


def compile_sass_file(infile, outfile, output_style='nested'):
    try:
        _ = subprocess.check_output([_CMD_SASSC, '-t',
            output_style, infile, outfile],
            stderr=subprocess.STDOUT)
        return True
    except subprocess.CalledProcessError as exc:
        raise pym.exc.SassError("Compilation failed: {}".format(
            exc.output.decode('utf-8')))


def safepath(path, sep=os.path.sep):
    """
    Returns safe version of path.

    Safe means, path is normalised with func:`normpath`, and all parts are
    sanitised like this:

    - cannot start with dash ``-``
    - cannot start with dot ``.``
    - cannot have control characters: 0x01..0x1F (0..31) and 0x7F (127)
    - cannot contain null byte 0x00
    - cannot start or end with whitespace
    - cannot contain '/', '\', ':' (slash, backslash, colon)
    - consecutive whitespace are folded to one blank

    See also:

    - http://www.dwheeler.com/essays/fixing-unix-linux-filenames.html
    - http://www.dwheeler.com/secure-programs/Secure-Programs-HOWTO/file-names.html
    """
    path = RE_INVALID_FS_CHARS.sub('', path)
    path = RE_BLANKS.sub(' ', path)
    aa = path.split(sep)
    bb = []
    for a in aa:
        if a == '':
            continue
        b = a.strip().lstrip('.-').replace('/', '').replace('\\', '').replace(':', '')
        bb.append(b)
    res = normpath(sep.join(bb))
    return res


def normpath(path):
    """
    Returns normalised version of user defined path.

    Normalised means, relative path segments like '..' are resolved and leading
    '..' are removed.
    E.g.::
        "/../../foo/../../bar"  --> "bar"
        "/../../foo/bar"        --> "foo/bar"
        "/foo/bar"              --> "foo/bar"
    """
    return os.path.normpath(os.path.join(os.path.sep, path)).lstrip(
        os.path.sep)


# Stolen from Pelican
def truncate_html_words(s, num, end_text='&hellip;'):
    """Truncates HTML to a certain number of words (not counting tags and
    comments). Closes opened tags if they were correctly closed in the given
    html. Takes an optional argument of what should be used to notify that the
    string has been truncated, defaulting to ellipsis (...).

    Newlines in the HTML are preserved.
    From the django framework.
    """
    length = int(num)
    if length <= 0:
        return ''
    html4_singlets = ('br', 'col', 'link', 'base', 'img', 'param', 'area',
                      'hr', 'input')

    # Set up regular expressions
    re_words = re.compile(r'&.*?;|<.*?>|(\w[\w-]*)', re.U)
    re_tag = re.compile(r'<(/)?([^ ]+?)(?: (/)| .*?)?>')
    # Count non-HTML words and keep note of open tags
    pos = 0
    end_text_pos = 0
    words = 0
    open_tags = []
    while words <= length:
        m = re_words.search(s, pos)
        if not m:
            # Checked through whole string
            break
        pos = m.end(0)
        if m.group(1):
            # It's an actual non-HTML word
            words += 1
            if words == length:
                end_text_pos = pos
            continue
        # Check for tag
        tag = re_tag.match(m.group(0))
        if not tag or end_text_pos:
            # Don't worry about non tags or tags after our truncate point
            continue
        closing_tag, tagname, self_closing = tag.groups()
        tagname = tagname.lower()  # Element names are always case-insensitive
        if self_closing or tagname in html4_singlets:
            pass
        elif closing_tag:
            # Check for match in open tags list
            try:
                i = open_tags.index(tagname)
            except ValueError:
                pass
            else:
                # SGML: An end tag closes, back to the matching start tag,
                # all unclosed intervening start tags with omitted end tags
                open_tags = open_tags[i + 1:]
        else:
            # Add it to the start of the open tags list
            open_tags.insert(0, tagname)
    if words <= length:
        # Don't try to close tags if we don't need to truncate
        return s
    out = s[:end_text_pos]
    if end_text:
        out += ' ' + end_text
    # Close any tags still open
    for tag in open_tags:
        out += '</%s>' % tag
    # Return string
    return out


def rreplace(s, old, new, occurrence):
    """
    Replaces the last n occurrences of a thing.

    >>> s = '1232425'
    '1232425'
    >>> rreplace(s, '2', ' ', 2)
    '123 4 5'
    >>> rreplace(s, '2', ' ', 3)
    '1 3 4 5'
    >>> rreplace(s, '2', ' ', 4)
    '1 3 4 5'
    >>> rreplace(s, '2', ' ', 0)
    '1232425'

    http://stackoverflow.com/a/2556252

    :param s: Haystack
    :param old: Needle
    :param new: Replacement
    :param occurrence: How many
    :returns: The resulting string
    """
    li = s.rsplit(old, occurrence)
    return new.join(li)


class BaseNode(dict):
    __parent__ = None
    __name__ = None
    __acl__ = []

    def __init__(self, parent):
        super().__init__()
        self.__parent__ = parent
        self._title = None

    def __setitem__(self, name, other):
        other.__parent__ = self
        other.__name__ = name
        super().__setitem__(name, other)

    def __delitem__(self, name):
        other = self[name]
        if hasattr(other, '__parent__'):
            del other.__parent__
        if hasattr(other, '__name__'):
            del other.__name__
        super().__delitem__(name)
        return other

    def __str__(self):
        s = self.__name__ if self.__name__ else '/'
        o = self.__parent__
        while o:
            s = (o.__name__ if o.__name__ else '') + '/' + s
            o = o.__parent__
        return str(type(self)).replace('>', ": '{}'>".format(s))

    @property
    def title(self):
        return self._title if self._title else self.__name__


class JsonResp(object):

    def __init__(self):
        """
        Constructs data structure in a standard response format for AJAX
        services.

        Rationale:

        If the service involves a lengthy operation, use this object as a
        minimalistic logger on the way. If the result data is ready, add it to
        this object too. The service view can now respond with the result data
        and all occurred messages in a well-defined structure.
        """
        self._msgs = []
        self._is_ok = True
        self._data = None

    def add_msg(self, msg):
        """
        Adds a message of user-defined kind.

        :param msg: The message
        :type msg: Dict(kind=..., text=...)
        """
        if msg['kind'] in ['error', 'fatal']:
            self._is_ok = False
        self._msgs.append(msg)

    def notice(self, txt):
        self.add_msg(dict(kind='notice', text=txt))

    def info(self, txt):
        self.add_msg(dict(kind='info', text=txt))

    def warn(self, txt):
        self.add_msg(dict(kind='warning', text=txt))

    def error(self, txt):
        self.add_msg(dict(kind='error', text=txt))

    def fatal(self, txt):
        self.add_msg(dict(kind='fatal', text=txt))

    def ok(self, txt):
        self.add_msg(dict(kind='success', text=txt))

    def print(self):
        for m in self._msgs:
            print(m['kind'].upper(), m['text'])

    @property
    def is_ok(self):
        """
        Returns True is no error messages are present, else False
        """
        return self._is_ok

    @property
    def msgs(self):
        """
        Returns the list of messages.

        Each message is a dict with at least keys ``kind`` and ``text``. This
        format is suitable for the PYM.growl() JavaScript.

        ``kind`` is one of (notice, info, warning, error, fatal, success).
        """
        return self._msgs

    @property
    def data(self):
        """
        Returns the data
        """
        return self._data

    @data.setter
    def data(self, v):
        """
        Sets the data
        """
        self._data = v

    @property
    def resp(self):
        """
        The response is::

            resp = {
                'ok': True/False,
                'msgs': [ {'kind': 'success', 'text': 'foo'}, ... ]
                'data: ... # arbitrary response data
            }
        """
        return dict(
            ok=self._is_ok,
            msgs=self._msgs,
            data=self._data
        )

    @property
    def is_ok(self):
        return self._is_ok


def init_cli_locale(locale_name):
    """
    Initialises CLI locale and encoding.

    Sets a certain locale. Ensures that output is correctly encoded, whether
    it is send directly to a console or piped.

    :param locale_name: A locale name, e.g. "de_DE.utf8".
    :return: active locale as 2-tuple (lang_code, encoding)
    """
    # Set the locale
    if locale_name:
        locale.setlocale(locale.LC_ALL, locale_name)
    else:
        if sys.stdout.isatty():
            locale.setlocale(locale.LC_ALL, '')
        else:
            locale.setlocale(locale.LC_ALL, 'en_GB.utf8')
    #lang_code, encoding = locale.getlocale(locale.LC_ALL)
    lang_code, encoding = locale.getlocale(locale.LC_CTYPE)
    # If output goes to pipe, detach stdout to allow writing binary data.
    # See http://docs.python.org/3/library/sys.html#sys.stdout
    if not sys.stdout.isatty():
        import codecs
        sys.stdout = codecs.getwriter(encoding)(sys.stdout.detach())
    return lang_code, encoding


def validate_name(s):
    if RE_NAME_CHARS.match(s) is None:
        raise KeyError("Invalid name: '{0}'".format(s))


def build_breadcrumbs(request):
    # Ensure that our context still has a session.
    # It may have lost its session if we are called from an error page after
    # an exception that closed the current session.
    sess = sa.inspect(request.context).session
    if not sess:
        sess = pym.models.DbSession()
        sess.add(request.context)

    from pyramid.location import lineage
    # If context has no session, this raises a DetachedInstanceError:
    linea = list(lineage(request.context))
    bcs = []
    for i, elem in enumerate(reversed(linea)):
        bc = [request.resource_url(elem)]
        if i == 0:
            bc.append('Home')
        else:
            bc.append(elem.title)
        bcs.append(bc)
    if request.view_name:
        bcs.append([None, request.view_name.capitalize()])
    return bcs


def flash_ok(*args, **kw):
    kw['kind'] = 'success'
    if not 'title' in kw:
        kw['title'] = 'Success'
    flash(*args, **kw)


def flash_error(request, text, *args, **kw):
    kw['kind'] = 'error'
    if not request.registry.settings['full_db_errors']:
        text = re.sub(r'DETAIL:.+$', '', text, flags=re.DOTALL)
    flash(request, text, *args, **kw)


def flash(request, text, kind='notice', title=None, status=None):
    """Flashes a message as JSON.

    :param request: Current request
    :param text: The message
    :param kind: Kind of message, one of notice, info, warning, error, fatal
    :param status: A status ID
    """
    kind = kind.lower()
    tt = dict(
        i='Info',
        w='Warning',
        e='Error'.upper(),
        f='Fatal Error'.upper()
    )
    if not title and kind != 'notice':
        title = tt[kind[0]]
        # JS expects UTC!
    d = dict(text=text, kind=kind, status=status, title=title,
        time=list(datetime.datetime.utcnow().timetuple()))
    request.session.flash(d)


def build_growl_msgs(request):
    mq = []
    for m in request.session.pop_flash():
        if isinstance(m, dict):
            mq.append(json.dumps(m))
        else:
            mq.append(json.dumps(dict(kind="notice", text=m)))
    return mq


def build_growl_msgs_nojs(request):
    from datetime import datetime
    mq = []
    for m in request.session.pop_flash():
        if isinstance(m, dict):
            msg = m
        else:
            msg = dict(kind="notice", text=m)
        if not 'kind' in msg:
            msg['kind'] = 'notice'
        if not 'title' in msg:
            msg['title'] = msg['kind']
        # Put timestamp into title
        # We get time as UTC
        if 'time' in msg:
            dt = datetime(
                msg['time'][0], msg['time'][1], msg['time'][2],
                msg['time'][3], msg['time'][4], msg['time'][5]
            )
        else:
            dt = datetime.now()

        msg['title'] = (
            '<span style="font-weight:normal;font-size:xx-small;">'
            + dt.strftime('%c')
            + '</span>&nbsp;'
            + msg['title'])
        # Setup type, icon and persistence according to kind
        k = msg['kind'][0]
        icon = None
        if k == 'n':
            msg['type'] = 'notice'
            icon = 'ui-icon ui-icon-comment'
        elif k == 'i':
            msg['type'] = 'info'
            icon = 'ui-icon ui-icon-info'
        elif k == 'w':
            msg['type'] = 'warning'
            icon = 'ui-icon ui-icon-notice'
        elif k == 'e':
            icon = 'ui-icon ui-icon-alert'
            msg['type'] = 'error'
        elif k == 'f':
            icon = 'ui-icon ui-icon-alert'
            msg['type'] = 'error'
        elif k == 's':
            icon = 'ui-icon ui-icon-check'
            msg['type'] = 'success'
        if not 'icon' in msg:
            msg['icon'] = icon

        mq.append(msg)
    return mq


def fmt_size(num):
    for x in ['bytes', 'KB', 'MB', 'GB']:
        if 1024.0 > num > -1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0
    return "%3.1f %s" % (num, 'TB')


class SingletonType(type):
    def __call__(cls, *args, **kwargs):
        try:
            return cls.__instance
        except AttributeError:
            cls.__instance = super(SingletonType, cls).__call__(*args, **kwargs)
            return cls.__instance
