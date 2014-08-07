import configparser
import logging
import logging.config
import sys
import yaml
from collections import OrderedDict
import pyramid.paster
import pyramid.config
import pyramid.request
import json
import os
from prettytable import PrettyTable

from pym.rc import Rc
import pym.models
import pym.lib
import pym.testing


mlgg = logging.getLogger(__name__)


class DummyArgs(object):
    pass


class Cli(object):

    def __init__(self):
        self.dump_opts_json = dict(
            sort_keys=False,
            indent=4,
            ensure_ascii=False,
            cls=pym.lib.JsonEncoder
        )
        self.dump_opts_yaml = dict(
            allow_unicode=True,
            default_flow_style=False
        )
        self.lgg = mlgg
        self.rc = None
        self.rc_key = None
        self.args = None
        self.env = None
        self.request = None
        self.unit_tester = None
        self.settings = None
        self.lang_code = None
        self.encoding = None

        self._config = None
        self._sess = None

    @staticmethod
    def add_parser_args(parser, which=None):
        """
        Adds default arguments to given parser instance.

        :param parser: Instance of a parser
        :param which: List of 2-Tuples. 1st elem tells which argument to add,
            2nd elem tells requiredness True/False
        """
        parser.add_argument(
            '--root-dir',
            default=os.getcwd(),
            help="Use this directory as root/work"
        )
        parser.add_argument(
            '--etc-dir',
            help="Directory with config, defaults to ROOT_DIR/etc"
        )
        if not which:
            which = [('config', True), ('locale', False)]
        for x in which:
            if x[0] == 'config':
                parser.add_argument(
                    '-c',
                    '--config',
                    required=x[1],
                    help="""Path to INI file with configuration,
                        e.g. 'production.ini'"""
                )
            elif x[0] == 'locale':
                parser.add_argument(
                    '-l',
                    '--locale',
                    required=x[1],
                    help="""Set the desired locale.
                        If omitted and output goes directly to console, we automatically use
                        the console's locale."""
                )
            elif x[0] == 'alembic-config':
                parser.add_argument(
                    '--alembic-config',
                    required=x[1],
                    help="Path to alembic's INI file"
                )
            elif x[0] == 'format':
                parser.add_argument('-f', '--format', default='yaml',
                    choices=['yaml', 'json', 'tsv', 'txt'],
                    required=x[1],
                    help="Set format for input and output"
                )

    def init_app(self, args, lgg=None, rc=None, rc_key=None, setup_logging=True):
        """
        Initialises Pyramid application.

        Loads config settings. Initialises SQLAlchemy and a session.
        """
        self.args = args
        fn_config = os.path.abspath(args.config)
        self.rc_key = rc_key
        if setup_logging:
            logging.config.fileConfig(
                fn_config,
                dict(
                    __file__=fn_config,
                    here=os.path.dirname(fn_config)
                )
            )
        if lgg:
            self.lgg = lgg

        self.lang_code, self.encoding = pym.lib.init_cli_locale(args.locale)
        self.lgg.debug("TTY? {}".format(sys.stdout.isatty()))
        self.lgg.debug("Locale? {}, {}".format(self.lang_code, self.encoding))

        #settings = pyramid.paster.get_appsettings(args.config)
        p = configparser.ConfigParser()
        p.read(fn_config)
        settings = dict(p['app:main'])
        if 'environment' not in settings:
            raise KeyError('Missing key "environment" in config. Specify '
                'environment in INI file "{}".'.format(args.config))
        if not rc:
            if not args.etc_dir:
                args.etc_dir = os.path.join(args.root_dir, 'etc')
            rc = Rc(
                environment=settings['environment'],
                root_dir=args.root_dir,
                etc_dir=args.etc_dir
            )
            rc.load()
        settings.update(rc.data)
        settings['rc'] = rc
        self.rc = rc
        self.settings = settings
        self._config = pyramid.config.Configurator(
            settings=settings
        )

        pym.models.init(settings, 'db.pym.sa.')
        self._sess = pym.models.DbSession()
        pym.init_auth(rc)

    def init_web_app(self, args, lgg=None, rc=None, rc_key=None, setup_logging=True):
        self.init_app(args, lgg=lgg, rc=rc, rc_key=rc_key,
            setup_logging=setup_logging)

        self._config.include(pym)
        self._config.include('pyramid_redis')

        req = pyramid.request.Request.blank('/',
            base_url='http://localhost:6543')
        self.env = pyramid.paster.bootstrap(
            os.path.join(
                self.rc.root_dir,
                args.config
            ),
            request=req
        )
        self.request = self.env['request']
        self.request.root = self.env['root']

    def impersonate_root(self):
        self.request.user.impersonate('root')

    def impersonate_unit_tester(self):
        sess = pym.models.DbSession()
        ut = pym.testing.create_unit_tester(self.lgg, sess)
        self.request.user.impersonate(ut)
        self.unit_tester = ut

    # noinspection PyUnresolvedReferences
    @staticmethod
    def _db_data_to_list(rs, fkmaps=None):
        """
        Transmogrifies db data into list including relationships.

        We use :func:`~.pym.models.todict` to turn an entity into a dict,
        which will only catch regular field, not foreign keys (relationships).
        Parameter ``fkmaps`` is a dict that maps relationship names to
        functions.  The function must have one input parameter which obtains a
        reference to the processed foreign entity. The function then returns
        the computed value.

        E.g.::

            class Principal(DbBase):
                roles = relationship(Role)

        If accessed, member ``roles`` is a list of associated roles. For each
        role the mapped function is called and the current role given::

            for attr, func in fkmaps.items():
                r[attr] = [func(it) for it in getattr(obj, attr)]

        And the function is defined like this::

            fkmaps=dict(roles=lambda it: it.name)

        :param rs: Db resultset, like a list of entities
        :param fkmaps: Dict with foreign key mappings
        """
        rr = []
        for obj in rs:
            it = pym.models.todict(obj)
            r = OrderedDict()
            r['id'] = it['id']
            for k in sorted(it.keys()):
                if k in ['id', 'owner', 'ctime', 'editor', 'mtime']:
                    continue
                r[k] = it[k]
            for k in ['owner', 'ctime', 'editor', 'mtime']:
                try:
                    r[k] = it[k]
                except KeyError:
                    pass
            if fkmaps:
                for attr, func in fkmaps.items():
                    r[attr] = [func(it) for it in getattr(obj, attr)]
            rr.append(r)
        return rr

    def _print(self, data):
        fmt = self.args.format.lower()
        if fmt == 'json':
            self._print_json(data)
        elif fmt == 'tsv':
            self._print_tsv(data)
        elif fmt == 'txt':
            self._print_txt(data)
        else:
            self._print_yaml(data)

    def _print_json(self, data):
        print(json.dumps(data, **self.dump_opts_json))

    @staticmethod
    def _print_tsv(data):
        try:
            hh = data[0].keys()
            print("\t".join(hh))
        except KeyError:  # missing data[0]
            # Data was not a list, maybe a dict
            hh = data.keys()
            print("\t".join(hh))
            print("\t".join([str(v) for v in data.values()]))
        except AttributeError:  # missing data.keys()
            # Data is just a list
            print("\t".join(data))
        else:
            # Data is list of dicts (like resultset from DB)
            for row in data:
                print("\t".join([str(v) for v in row.values()]))

    @staticmethod
    def _print_txt(data):
        # We need a list of hh for prettytable, otherwise we get
        # TypeError: 'KeysView' object does not support indexing
        try:
            hh = data[0].keys()
        except KeyError:  # missing data[0]
            # Data was not a list, maybe a dict
            hh = data.keys()
            t = PrettyTable(list(hh))
            t.align = 'l'
            t.add_row([data[h] for h in hh])
            print(t)
        except AttributeError:  # missing data.keys()
            # Just a simple list
            # PrettyTable *must* have column headers and the headers *must*
            # be str, not int or else!
            t = PrettyTable([str(i) for i in range(len(data))])
            t.align = 'l'
            t.add_row(data)
            print(t)
        else:
            # Data is list of dicts (like resultset from DB)
            t = PrettyTable(list(hh))
            t.align = 'l'
            for row in data:
                t.add_row([row[h] for h in hh])
            print(t)

    def _print_yaml(self, data):
        yaml.dump(data, sys.stdout, **self.dump_opts_yaml)

    def _parse(self, data):
        fmt = self.args.format.lower()
        if fmt == 'json':
            return self._parse_json(data)
        if fmt == 'tsv':
            return self._parse_tsv(data)
        if fmt == 'txt':
            raise NotImplementedError("Reading data from pretty ASCII tables"
                "is not implemented")
        else:
            return self._parse_yaml(data)

    @staticmethod
    def _parse_json(data):
        return json.loads(data)

    @staticmethod
    def _parse_tsv(s):
        data = []
        for row in "\n".split(s):
            data.append([x.strip() for x in "\t".split(row)])
        return data

    @staticmethod
    def _parse_yaml(data):
        return yaml.load(data)

    @property
    def sess(self):
        """
        Initialised DB session.

        The session is created from the web app's default settings and therefore
        is in most cases a scoped session with transaction extension. If you need
        a different session, caller may create one itself and set this property

        """
        return self._sess

    @sess.setter
    def sess(self, v):
        self._sess = v
