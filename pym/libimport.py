import re
import collections
import csv
import sqlalchemy as sa
from pym.models import DbBase
from pym.lib import json_serializer, json_deserializer


class ImportHelper():

    RE_WHITESPACES = re.compile(r'\s+')
    RE_NON_WORDCHARS = re.compile(r'\W+')
    RE_STARTS_WITH_DIGIT = re.compile(r'^\d')
    RE_UNDERSCORES = re.compile(r'_+')

    def __init__(self, lgg, sess):
        self.lgg = lgg
        self.sess = sess
        self.char_map = {
            ord('ä'): 'ae',
            ord('ö'): 'oe',
            ord('ü'): 'ue',
            ord('ß'): 'ss',
        }
        self.types = (int, float)
        self.type2sql = {
            'int': 'integer',
            'float': 'decimal(14, 2)',
            'str': 'varchar(255)',
            'NoneType': 'varchar(255)'
        }
        self.orig_cols = []
        """List of original column names"""
        self.my_cols = []
        """List of my column names after cleansing"""
        self.col_map = []
        """
        List of 2-tuples mapping column names: (orig, my)
        It may happen that the name of an original column appears more than
        once. Therefore we cannot use a dict here.
        """
        self.col_types = []
        """List of data types of columns."""
        self.reader = []
        """Data reader."""
        self.header_row_num = 0
        """Row number of header row"""
        self.data_row_num = 1
        """
        Row number of a data row.
        On determining data types, we use this row.
        On importing data, we start at this row.
        """

    def open(self):
        raise NotImplementedError()

    def close(self):
        raise NotImplementedError()

    def rewind(self):
        raise NotImplementedError()

    def iter_rows(self):
        for row in self.reader:
            yield row

    def iter_values(self, row):
        # If we are reading a data row, i.e. column types are defined
        if self.col_types:
            for i, v in enumerate(row):
                cast = self.col_types[i]
                yield cast(v)
        # If we are reading the column headers, we do not have types yet
        else:
            for v in row:
                yield v

    def build_cols(self):
        raise NotImplementedError()

    def _build_col_map(self):
        """
        Builds map of column names

        ``self.orig_cols`` must be initialised with list of original column
        names.

        Sets up ``self.my_cols`` and ``self.col_map``.
        """
        # Clean invalid chars for column names
        my_cols = [
            self.RE_UNDERSCORES.sub(  # reduce multiple _
                '_',
                self.RE_NON_WORDCHARS.sub(  # replace non word chars with _
                    '_',
                    self.RE_WHITESPACES.sub(  # replace whitespace with _
                        '_',
                        # translate characters
                        c.strip().lower().translate(self.char_map)
                    )
                )
            )
            for c in self.orig_cols
        ]
        # Column name must not start with digit
        my_cols = [('n' + c) if self.RE_STARTS_WITH_DIGIT.match(c)
            else c for c in my_cols]
        # Make sure, each column name is unique
        seen = collections.defaultdict(lambda: 0)
        for i in range(len(my_cols)):
            c = my_cols[i]
            seen[c] += 1
            if seen[c] > 1:
                my_cols[i] = c + '_' + str(seen[c])

        self.my_cols = my_cols
        self.col_map = list(zip(self.orig_cols, my_cols))

    def _detect_col_types(self, row):
        """
        Detects data type of each column.


        ``self.my_cols`` must be initialised.

        Sets ``self.col_types``.

        :param row: Row to use for detection
        """
        col_types = {}
        for i, v in enumerate(self.iter_values(row)):
            c = self.my_cols[i]
            self.lgg.debug("Detecting type for {}: '{}' ({})".format(c, v,
                type(v)))
            if not isinstance(v, str):
                ty = v.__class__.__name__
            else:
                ty = None
                for cast in self.types:
                    #self.lgg.debug("Trying '{}'".format(cast))
                    try:
                        cv = cast(v)
                        if str(cv) != v:
                            raise ValueError
                        ty = cv.__class__.__name__
                        break
                    except (ValueError, TypeError):  # TypeError if None
                        pass
                if not ty:
                    ty = 'str'
            self.lgg.debug("Detected type: '{}'".format(ty))
            col_types[c] = ty
        self.col_types = col_types

    def load_cols(self, fn):
        self.lgg.info('Reading columns from ' + fn)
        with open(fn, 'rt', encoding='utf-8') as fh:
            data = fh.read()
        data = json_deserializer(data)
        for k, v in data.items():
            setattr(self, k, v)

    def save_cols(self, fn):
        data = {
            'orig_cols': self.orig_cols,
            'my_cols': self.my_cols,
            'col_map': self.col_map,
            'col_types': self.col_types,
        }
        with open(fn, 'wt', encoding='utf-8') as fh:
            fh.write(json_serializer(data))
        self.lgg.info('Columns written to ' + fn)

    def create_table(self, tbl_name):
        self.lgg.info('Creating table {}...'.format(tbl_name))
        cols = []
        q = """DROP TABLE IF EXISTS {}""".format(tbl_name)
        self.sess.execute(q)
        for m in self.col_map:
            cols.append("{} {}".format(m[1],
                self.type2sql[self.col_types[m[1]]]))
        q = """CREATE TABLE {tbl} (
          id serial NOT NULL PRIMARY KEY,
          row_num integer NOT NULL UNIQUE,
          {cols}
        )""".format(tbl=tbl_name, cols=",\n".join(cols))
        self.sess.execute(q)

    def import_data(self, tbl_name):
        """
        Imports data into given table.

        :param tbl_name: Table, optionally with schema to import into.
        """
        self.lgg.info('Importing into table {}...'.format(tbl_name))
        a = tbl_name.split('.')
        if len(a) == 1:
            schema, tbl_name = 'public', a[0]
        else:
            schema, tbl_name = a
        tbl = sa.Table(tbl_name, DbBase.metadata, autoload=True,
            schema=schema)
        ins = tbl.insert()
        cols = [x[1] for x in self.col_map] + ['row_num']
        data = []
        self.open()
        try:
            for row_num, row in enumerate(self.iter_rows()):
                if row_num < self.data_row_num:
                    continue
                if row_num > 0 and row_num % 100 == 0:
                    print(row_num)
                    self.sess.execute(ins, data)
                    data = []
                vals = [v for v in self.iter_values(row)] + [row_num]
                data.append(dict(zip(cols, vals)))
            if data:
                self.sess.execute(ins, data)
        finally:
            self.close()


class CsvImporter(ImportHelper):

    def __init__(self, lgg, sess):
        super().__init__(lgg, sess)
        self.fn = ''
        self.newline = ''
        self.dialect = ''
        self.delim = "\t"
        self.quote_char = ''
        self.encoding = 'utf-8'
        self.f_opts = {}
        self.reader_options = {}
        self._fh = None

    def open(self):
        self._fh = open(self.fn, 'rt', **self.f_opts)
        if self.dialect == 'sniff':
            dialect = csv.Sniffer().sniff(self._fh.read(1024))
            self.rewind()
            self.lgg.info("Sniffed dialect: " + str(dialect))
            self.reader = csv.reader(self._fh, dialect)
        else:
            self.reader = csv.reader(self._fh, **self.reader_options)

    def rewind(self):
        self._fh.seek(0)

    def close(self):
        self._fh.close()

    def build_cols(self):
        self.lgg.info('Building columns...')
        self.open()
        try:
            self.orig_cols = next(self.reader)
            self._build_col_map()
            for i in range(self.data_row_num):
                row = next(self.reader)
            self._detect_col_types(row)
        finally:
            self.close()


class XlsxImporter(ImportHelper):

    def __init__(self, lgg, sess):
        super().__init__(lgg, sess)
        self.fn = ''
        self.encoding = 'utf-8'
        self.sheet_name = None

        self._lib = __import__('openpyxl')
        self._wb = None
        self._sh = None
        self._cur_row = 0

    def open(self):
        self._wb = self._lib.load_workbook(self.fn, use_iterators=True)
        if self.sheet_name:
            self._sh = self._wb.get_sheet_by_name(self.sheet_name)
        else:
            self._sh = self._wb.get_active_sheet()
        self._cur_row = 0

    def rewind(self):
        self._cur_row = 0

    def close(self):
        self._sh = None
        self._wb = None

    def iter_rows(self):
        for row in self._sh.iter_rows():
            yield row

    def iter_values(self, row):
        for cell in row:
            v = cell.value
            if isinstance(v, str):
                v = v.strip()
                if len(v) == 0:
                    v = None
            yield v

    def build_cols(self):
        self.lgg.info('Building columns...')
        self.open()
        try:
            for i, row in enumerate(self.iter_rows()):
                if i == self.header_row_num:
                    self.lgg.debug('Using row {} for headers'.format(i))
                    self.orig_cols = [str(v) for v in self.iter_values(row)]
                    self._build_col_map()
                elif i == self.data_row_num:
                    self.lgg.debug('Using row {} for data types'.format(i))
                    self._detect_col_types(row)
                if i > self.data_row_num:
                    break
        finally:
            self.close()
