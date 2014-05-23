import re


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
        self.default_ps = 100
        self.allowed_ps = (100, 200, 500)
        self.allowed_sort_fields = ('id', )
        self.allowed_sort_dirs = ('asc', 'desc')

    @property
    def inp(self):
        return self._inp

    @inp.setter
    def inp(self, value):
        self._inp = value

    @property
    def page(self):
        try:
            pg = int(self.inp.get('pg', self.default_pg))
        except TypeError:
            raise ViewstateError("Invalid pg")
        return pg

    @property
    def page_size(self):
        try:
            ps = int(self.inp.get('ps', self.default_ps))
            # Constrain ps to the bounds defined in allowed_ps
            if ps < self.allowed_ps[0]:
                ps = self.allowed_ps[0]
            elif ps > self.allowed_ps[-1]:
                ps = self.allowed_ps[-1]
        except (TypeError, ValueError):
            raise ViewstateError("Invalid ps")
        return ps

    @property
    def filter_text(self):
        return self.RE_WHITESPACE.sub(' ', self.inp.get('q', '').strip())

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
