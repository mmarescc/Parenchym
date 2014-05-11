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
        self.default_ps = 10
        self.allowed_ps = (1, 1000)

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
    def query(self):
        return self.RE_WHITESPACE.sub(' ', self.inp.get('q', '').strip())

    # TODO Property filter