import datetime
import re
from pym.exc import ValidationError
from pym.lib import json_deserializer


class PagerValidator(object):

    def __init__(self, parent):
        self.parent = parent

        self.default_page = 0
        """Default for current page"""
        self.default_page_size = 100
        """Default page size"""
        self.allowed_page_sizes = (100, 200, 500)
        """Default list of allowed page sizes"""

    @property
    def page(self):
        pg = self.parent.fetch_int('pg', default=self.default_page,
            required=False, multiple=False)
        if pg < 0:
            raise ValidationError('Invalid pg: {}'.format(pg))
        return pg

    @property
    def page_size(self):
        ps = self.parent.fetch_int('ps', default=self.default_page_size,
            required=False, multiple=False)
        # Constrain ps to the bounds defined in allowed_page_sizes
        if ps < self.allowed_page_sizes[0]:
            ps = self.allowed_page_sizes[0]
        elif ps > self.allowed_page_sizes[-1]:
            ps = self.allowed_page_sizes[-1]
        return ps


class SorterValidator(object):

    def __init__(self, parent):
        self.parent = parent

        self.allowed_fields = ('id', )
        """List of field names that are allowed in a sort expression"""
        self.allowed_directions = ('asc', 'desc')
        """List of sort directions"""

    @property
    def fields(self):
        sort_fields = self.parent.fetch('sf', default=None, required=True,
            multiple=True)
        for sf in sort_fields:
            if not sf in self.allowed_fields:
                raise ValidationError("Invalid sort field: '{}'".format(sf))
        return sort_fields

    @property
    def directions(self):
        sort_dirs = [x.lower() for x in
            self.parent.fetch('sd', default=None, required=True, multiple=True)]
        for sd in sort_dirs:
            if not sd in self.allowed_directions:
                raise ValidationError("Invalid sort dir: '{}'".format(sd))
        return sort_dirs


class FilterValidator(object):

    RE_WHITESPACE = re.compile(r'\s+')

    def __init__(self, parent):
        self.parent = parent

        self.allowed_fields = ('id', )
        """List of field names that are allowed in a filter expression"""
        self.allowed_operators = (
            '=', '<', '<=', '>', '>=', 'like', '~',
            '!=', '!like', '!~'
            '=*', '<*', '<=*', '>*', '>=*', 'like*', '~*',
            '!=*', '!like*', '!~*'
        )
        """List of (prefix '!' means negation, suffix '*' means
        case-insensitive)"""
        self.allowed_conjunctions = ('a', 'o')  # And, Or
        """List of conjunctions."""
        self.allowed_case_sensitivity = ('s', 'i')  # case Sensitive, Insensitive
        """List of choices for case sensitivity."""

    @property
    def filter(self):
        try:
            fil = self.parent.inp['fil']
        except KeyError:
            raise ValidationError("Missing filter")
        try:
            fil = json_deserializer(fil)
        except ValueError:
            raise ValidationError("Invalid filter")
        # Expect be [CONJ, TAIL]
        if len(fil) != 2:
            raise ValidationError("Invalid filter")

        aconj = self.allowed_conjunctions
        aops = self.allowed_operators
        acase = self.allowed_case_sensitivity
        aff = self.allowed_fields

        # (country='f' and plz >=1 and plz <=2)
        # or
        # (country='d' and ((plz >=5 and plz <=8) or (plz > 2 and plz < 4)))
        #
        # [or, [
        #   [and, [
        #     [country, =, 'f'],
        #     [plz, >=, 1],
        #     [plz, <=, 2]
        #   ],
        #   [and, [
        #     [country, =, 'd'],
        #     [or, [
        #       [and, [
        #         [plz, >=, 5],
        #         [plz, <=, 8]
        #       ],
        #       [and, [
        #         [plz, >, 2],
        #         [plz, <, 4]
        #       ]
        #     ]
        #   ]
        # ]
        def check(conj, tail):
            # check conjunction
            if conj not in aconj:
                raise ValidationError("Invalid conjunction: '{}'".format(conj))
            # tail must be list
            if not isinstance(tail, list):
                raise ValidationError("Invalid tail: '{}'".format(tail))
            # tail is itself CONJ + TAIL
            if len(tail) == 2 and tail[0] in aconj:
                check(tail[0], tail[1:])
            # consider tail to be list of things
            else:
                for thing in tail:
                    l = len(thing)
                    # this thing is CONJ + TAIL
                    if l == 2:
                        check(thing[0], thing[1:])
                    # this thing is filter expression
                    elif l == 4:
                        fld, op, case, val = thing
                        if not fld in aff:
                            raise ValidationError("Invalid field: '{}'".format(fld))
                        if not op in aops:
                            raise ValidationError("Invalid op: '{}'".format(op))
                        if not case in acase:
                            raise ValidationError("Invalid case: '{}'".format(case))
                    # this thing is garbage
                    else:
                        raise ValidationError("Invalid thing: '{}'".format(thing))

        check(fil[0], fil[1:])
        return fil

    def build_filter(self, fil, allowed_fields, col_map):
        pass
        # TODO Implement this

    @property
    def text(self):
        q = self.parent.fetch('q', default=None, required=False, multiple=False)
        return None if q is None else self.RE_WHITESPACE.sub(' ', q).strip()

    @property
    def field(self):
        f = self.parent.fetch('f', default=None, required=True, multiple=False)
        if f not in self.allowed_fields:
            raise ValidationError("Invalid filter field: '{}'".format(f))
        return f


class Validator(object):

    def __init__(self, inp):
        """
        Represents a validator object.

        :param inp: MultiDict, e.g. ``request.GET``
        """
        self._inp = inp

        self.pager = PagerValidator(self)
        self.sorter = SorterValidator(self)
        self.filter = FilterValidator(self)

    def fetch(self, k, default=None, required=True, multiple=False):
        """
        Fetches an input parameter.

        :param k: Parameter to fetch from input
        :param multiple: If true, return list, else scalar
        :param default: Default value if ``k`` was not present
        :param required: Raises ValidationError if parameter is missing
        :return: Fetched value
        """
        if multiple:
            v = self.inp.getall(k)
            if not v:
                # Parameter missing, but required
                if required:
                    raise ValidationError("Missing: '{}'".format(k))
                # Parameter missing, but not required --> return default
                return default
            # Parameter was given...
            # ... if we need it, make sure, all elements are set
            if required:
                for x in v:
                    if x is None or len(str(x)) == 0:
                        raise ValidationError("Missing: '{}'".format(k))
        else:
            try:
                v = self.inp[k]
            except KeyError:
                # Parameter missing, but required
                if required:
                    raise ValidationError("Missing: '{}'".format(k))
                # Parameter missing, but not required
                return default
            # Parameter was given
            if v is None or len(str(v)) == 0:
                # Parameter empty, but required
                if required:
                    raise ValidationError("Missing: '{}'".format(k))
                # Parameter empty, but not required
                return default
        # Yeah, we actually have a value
        return v

    def fetch_int(self, k, default=None, required=True, multiple=False):
        """
        Fetches an input parameter as integer.

        :param k: Parameter to fetch from input
        :param multiple: If true, return list, else scalar
        :param default: Default value if ``k`` was not present
        :return: Int or list of ints
        """
        v = self.fetch(k, default=default, required=required, multiple=multiple)
        if v is None:
            return None
        if multiple:
            r = []
            for x in v:
                try:
                    r.append(int(x))
                except ValueError:
                    raise ValidationError(
                        "Not an integer: '{}'->'{}'".format(k, x))
            return r
        else:
            try:
                r = int(v)
            except ValueError:
                raise ValidationError("Not an integer: '{}'->'{}'".format(k, v))
        return r

    def fetch_bool(self, k, default=None, required=True, multiple=False):
        """
        Fetches an input parameter as boolean.

        :param k: Parameter to fetch from input
        :param multiple: If true, return list, else scalar
        :param default: Default value if ``k`` was not present
        :return: Bool or list of bools
        """
        v = self.fetch(k, default=default, required=required, multiple=multiple)
        if v is None:
            return None
        if multiple:
            r = []
            for x in v:
                try:
                    if x[0].lower() in ('t', 'true', 'on', '1'):
                        r.append(True)
                    elif x[0].lower() in ('f', 'false', 'off', '0'):
                        r.append(False)
                    else:
                        r.append(bool(x))
                except (TypeError, ValueError):
                    raise ValidationError(
                        "Not a boolean: '{}'->'{}'".format(k, x))
            return r
        else:
            try:
                if v.lower() in ('t', 'true', 'on', '1'):
                    r = True
                elif v[0].lower() in ('f', 'false', 'off', '0'):
                    r = False
                else:
                    r = bool(v)
            except (TypeError, ValueError):
                raise ValidationError("Not a boolean: '{}'->'{}'".format(k, v))
        return r

    def fetch_float(self, k, default=None, required=True, multiple=False):
        """
        Fetches an input parameter as float.

        We use the right-most dot or comma as decimal separator.

        :param k: Parameter to fetch from input
        :param multiple: If true, return list, else scalar
        :param default: Default value if ``k`` was not present
        :return: Float or list of floats
        """
        v = self.fetch(k, default=default, required=required, multiple=multiple)
        if v is None:
            return None
        if multiple:
            r = []
            for x in v:
                if isinstance(x, str):
                    dp = x.rfind('.')
                    cp = x.rfind(',')
                    if dp > cp:  # English: dot is right of optional commas
                        x = x.replace(',', '')  # Need only to remove commas
                    else:  # German: comma is right of optional dots
                        # Remove dots and replace comma with dot
                        x = x.replace('.', '').replace(',', '.')
                try:
                    r.append(float(x))
                except ValueError:
                    raise ValidationError(
                        "Not a float: '{}'->'{}'".format(k, x))
            return r
        else:
            if isinstance(v, str):
                dp = v.rfind('.')
                cp = v.rfind(',')
                if dp > cp:  # English: dot is right of optional commas
                    v = v.replace(',', '')  # Need only to remove commas
                else:  # German: comma is right of optional dots
                    # Remove dots and replace comma with dot
                    v = v.replace('.', '').replace(',', '.')
            try:
                r = float(v)
            except ValueError:
                raise ValidationError("Not a float: '{}'->'{}'".format(k, v))
        return r

    def fetch_date(self, k, default=None, required=True, multiple=False,
            fmt='%Y-%m-%d'):
        """
        Fetches an input parameter as a date.

        :param k: Parameter to fetch from input
        :param multiple: If true, return list, else scalar
        :param default: Default value if ``k`` was not present
        :return: Date or list of dates
        """
        v = self.fetch(k, default=default, required=required, multiple=multiple)
        if v is None:
            return None
        if multiple:
            r = []
            for x in v:
                try:
                    r.append(datetime.datetime.strptime(x, fmt).date())
                except ValueError:
                    raise ValidationError(
                        "Not a date: '{}'->'{}'".format(k, x))
            return r
        else:
            try:
                r = datetime.datetime.strptime(v, fmt).date()
            except ValueError:
                raise ValidationError("Not a date: '{}'->'{}'".format(k, v))
        return r

    @property
    def inp(self):
        return self._inp

    @inp.setter
    def inp(self, value):
        self._inp = value
