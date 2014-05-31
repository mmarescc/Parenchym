import re
from pym.lib import json_deserializer


class ViewstateError(Exception):
    pass


class ViewState(object):

    RE_WHITESPACE = re.compile(r'\s+')

    def __init__(self, inp):
        """
        Represents a viewstate.

        :param inp: MultiDict, e.g. ``request.GET``
        """
        self._inp = inp
        self.default_pg = 0
        """Default for current page"""
        self.default_ps = 100
        """Default page size"""
        self.allowed_ps = (100, 200, 500)
        """Default list of allowed page sizes"""
        self.allowed_filter_fields = ('id', )
        """List of field names that are allowed in a filter expression"""
        self.allowed_filter_ops = (
            '=', '<', '<=', '>', '>=', 'like', '~',
            '!=', '!like', '!~'
            '=*', '<*', '<=*', '>*', '>=*', 'like*', '~*',
            '!=*', '!like*', '!~*'
        )
        """List of filter operators (prefix '!' means negation, suffix '*' means
        case-insensitive)"""
        self.allowed_filter_conj = ('a', 'o')  # And, Or
        self.allowed_filter_case = ('s', 'i')  # case Sensitive, Insensitive
        """List of filter conjunctions."""
        self.allowed_sort_fields = ('id', )
        """List of field names that are allowed in a sort expression"""
        self.allowed_sort_dirs = ('asc', 'desc')
        """List of sort directions"""

    def _fetch(self, k, default=None, required=True, multiple=False):
        """
        Fetches an input parameter.

        :param k: Parameter to fetch from input
        :param multiple: If true, return list, else scalar
        :param default: Default value if ``k`` was not present
        :param required: Raises ViewstateError if parameter is missing
        :return: Fetched value
        """
        if multiple:
            v = self.inp.getall(k)
            if not v:
                if required:
                    raise ViewstateError("Missing: '{}'".format(k))
                return default
        else:
            try:
                v = self.inp[k]
            except KeyError:
                if required:
                    raise ViewstateError("Missing: '{}'".format(k))
                return default
        return v

    def fetch_int(self, k, default=None, required=True, multiple=False):
        """
        Fetches an input parameter as integer.

        :param k: Parameter to fetch from input
        :param multiple: If true, return list, else scalar
        :param default: Default value if ``k`` was not present
        :return: Int or list of ints
        """
        v = self._fetch(k, default=default, required=required, multiple=multiple)
        if multiple:
            r = []
            for x in v:
                try:
                    r.append(int(x))
                except TypeError:
                    raise ViewstateError(
                        "Not an integer: '{}'->'{}'".format(k, x))
            return r
        else:
            try:
                r = int(v)
            except TypeError:
                raise ViewstateError("Not an integer: '{}'->'{}'".format(k, v))
        return r

    @property
    def inp(self):
        return self._inp

    @inp.setter
    def inp(self, value):
        self._inp = value

    @property
    def page(self):
        pg = self.fetch_int('pg', default=self.default_pg, required=False,
            multiple=False)
        if pg < 0:
            raise ViewstateError('Invalid pg: {}'.format(pg))
        return pg

    @property
    def page_size(self):
        ps = self.fetch_int('ps', default=self.default_ps, required=False,
            multiple=False)
        # Constrain ps to the bounds defined in allowed_ps
        if ps < self.allowed_ps[0]:
            ps = self.allowed_ps[0]
        elif ps > self.allowed_ps[-1]:
            ps = self.allowed_ps[-1]
        return ps

    @property
    def filter(self):
        try:
            fil = self.inp['fil']
        except KeyError:
            raise ViewstateError("Missing filter")
        try:
            fil = json_deserializer(fil)
        except ValueError:
            raise ViewstateError("Invalid filter")
        # Expect be [CONJ, TAIL]
        if len(fil) != 2:
            raise ViewstateError("Invalid filter")

        aconj = self.allowed_filter_conj
        aops = self.allowed_filter_ops
        acase = self.allowed_filter_case
        aff = self.allowed_filter_fields

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
                raise ViewstateError("Invalid conjunction: '{}'".format(conj))
            # tail must be list
            if not isinstance(tail, list):
                raise ViewstateError("Invalid tail: '{}'".format(tail))
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
                            raise ViewstateError("Invalid field: '{}'".format(fld))
                        if not op in aops:
                            raise ViewstateError("Invalid op: '{}'".format(op))
                        if not case in acase:
                            raise ViewstateError("Invalid case: '{}'".format(case))
                    # this thing is garbage
                    else:
                        raise ViewstateError("Invalid thing: '{}'".format(thing))

        check(fil[0], fil[1:])
        return fil

    def build_filter(self, fil, allowed_fields, col_map):
        pass
        # TODO Implement this


    @property
    def filter_text(self):
        return self.RE_WHITESPACE.sub(' ', self.inp.get('q', '').strip())

    @property
    def filter_field(self):
        try:
            f = self.inp['f']
        except KeyError:
            raise ViewstateError("Missing filter field")
        if f not in self.allowed_filter_fields:
            raise ViewstateError("Invalid filter field: '{}'".format(f))
        return f

    @property
    def sort_fields(self):
        sort_fields = self.inp.getall('sf')
        for sf in sort_fields:
            if not sf in self.allowed_sort_fields:
                raise ViewstateError("Invalid sort field: '{}'".format(sf))
        return sort_fields

    @property
    def sort_dirs(self):
        sort_dirs = [x.lower() for x in self.inp.getall('sd')]
        for sd in sort_dirs:
            if not sd in self.allowed_sort_dirs:
                raise ViewstateError("Invalid sort dir: '{}'".format(sd))
        return sort_dirs
