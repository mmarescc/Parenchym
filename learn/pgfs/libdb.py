__author__ = 'dm'


import psycopg2 as dbdriver
from psycopg2.extras import DictCursor


# noinspection PyPep8Naming
class Db():
    def __init__(self, L, dsn, txmgr=None):
        self.L = L
        self._dsn = dsn
        if isinstance(dsn, str):
            # self._dbh = dbdriver.connect(dsn=dsn, cursor_factory=DictCursor)
            self._dbh = dbdriver.connect(dsn=dsn)
        else:
            # self._dbh = dbdriver.connect(cursor_factory=DictCursor, **dsn)
            self._dbh = dbdriver.connect(**dsn)
        self.txmgr = txmgr

    def cursor(self, **kw):
        return self._dbh.cursor(**kw)

    @property
    def dbh(self):
        return self._dbh