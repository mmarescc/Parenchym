#!/usr/bin/env python
import csv
import time
import argparse
import logging
import sys
import os

import sqlalchemy as sa
import sqlalchemy.orm
import sqlalchemy.ext.declarative
from zope.sqlalchemy import ZopeTransactionExtension
import pym.cli
import pym.lib
import pym.models
import pym.auth.const
import pym.libimport


# Do not use the scoped session from the framework
DbSession = sa.orm.sessionmaker(extension=ZopeTransactionExtension())
DbBase = sa.ext.declarative.declarative_base()


class Runner(pym.cli.Cli):

    def __init__(self):
        super().__init__()
        self._sess = None
        self.office = None
        self.doc = None
        self.worker = None

    @property
    def sess(self):
        return self.sess

    @sess.setter
    def sess(self, v):
        self._sess = v
        if self.worker:
            self.worker.sess = v

    def run(self):
        self._setup()
        if self.args.cmd == 'col-map':
            self.worker.build_cols()
            if self.args.map:
                self.worker.save_cols(self.args.map)
        elif self.args.cmd == 'create-table':
            if not self.args.map:
                raise Exception("Need arg --map")
            if not self.args.table:
                raise Exception("Need arg --table")
            self.worker.create_table(self.args.table)
        elif self.args.cmd == 'import':
            if not self.args.map:
                raise Exception("Need arg --map")
            if not self.args.table:
                raise Exception("Need arg --table")
            self.worker.import_data(self.args.table)
        else:
            raise NotImplementedError("Command not implemented: '{}'"
                .format(self.args.cmd))

    def _setup(self):
        # Determine file format to import
        fn_ = self.args.fn.lower()
        format = self.args.format
        if not format:
            if fn_.endswith(('.txt', '.csv', '.tsv')):
                format = 'csv'
            elif fn_.endswith('.xlsx'):
                format = 'xlsx'
            elif fn_.endswith('.xls'):
                format = 'xls'
            else:
                format = None
        if format == 'csv':
            self.worker = pym.libimport.CsvImporter(self.lgg, self._sess)
            self.worker.quote_char = self.args.quote_char
            self.worker.dialect = self.args.dialect
            delim = self.args.delimiter
            if delim == '{TAB}':
                delim = "\t"
            self.worker.delim = delim
            f_opts = {
                'encoding': self.worker.encoding,
                'newline': self.worker.newline
            }
            rd_opts = {}
            if self.worker.dialect:
                rd_opts['dialect'] = self.worker.dialect
            if self.worker.delim:
                rd_opts['delimiter'] = self.worker.delim
            if self.worker.quote_char:
                rd_opts['quotechar'] = self.worker.quote_char
            self.worker.f_opts = f_opts
            self.worker.reader_options = rd_opts
        elif format == 'xlsx':
            self.worker = pym.libimport.XlsxImporter(self.lgg, self._sess)
            self.worker.sheet_name = self.args.sheet
        elif format == 'xls':
            raise NotImplementedError('Alas, XLS is not yet implemented.')
        else:
            raise Exception("Unknown file format: '{}'.".format(format))

        # Set general worker options
        self.worker.fn = self.args.fn
        self.worker.encoding = self.args.encoding
        self.worker.header_row_num = self.args.header_row
        self.worker.data_row_num = self.args.data_row

        # Load column definition if needed
        if self.args.map and self.args.cmd in ('create-table', 'import'):
            self.worker.load_cols(self.args.map)


def parse_args(app_class):
    # Main parser
    parser = argparse.ArgumentParser(
        description="""Imports data of product mgmt."""
    )
    app_class.add_parser_args(parser, (('config', True),
        ('locale', False), ('alembic-config', False)))
    parser.add_argument(
        '--dialect',
        default="",
        choices=csv.list_dialects() + ['sniff'],
        help="""CSV dialect. Default empty."""
    )
    parser.add_argument(
        '-d', '--delimiter',
        default="{TAB}",
        help="""Delimiter. Write '{TAB}' for tab, which is default"""
    )
    parser.add_argument(
        '-q', '--quote-char',
        default="",
        help="""Quote character. Default empty."""
    )
    parser.add_argument(
        '-e', '--encoding',
        default="utf-8",
        help="""Encoding. Default 'utf-8'."""
    )
    parser.add_argument(
        '-t', '--table',
        help="""Name of table to use/create"""
    )
    parser.add_argument(
        '-m', '--map',
        help="""Filename for column map"""
    )
    parser.add_argument(
        '-f', '--format',
        choices=['xls', 'xlsx', 'csv'],
        help="""Format of input file"""
    )
    parser.add_argument(
        '--sheet',
        help="""Import this worksheet"""
    )
    parser.add_argument(
        '--header-row',
        default=0,
        type=int,
        help="""Row number of header"""
    )
    parser.add_argument(
        '--data-row',
        default=1,
        type=int,
        help="""Number of first data row"""
    )
    parser.add_argument(
        'cmd',
        choices=['col-map', 'create-table', 'import'],
        help="""Command"""
    )
    parser.add_argument(
        'fn',
        help="""Filename"""
    )
    return parser.parse_args()


def main(argv=None):
    if not argv:
        argv = sys.argv

    start_time = time.time()
    app_name = os.path.basename(argv[0])
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(name)s %(levelname)-8s %(message)s'
    )
    lgg = logging.getLogger('cli.' + app_name)

    args = parse_args(Runner)
    runner = Runner()
    runner.init_app(args, lgg=lgg, setup_logging=True)
    # Init session after app!
    DbSession.configure(bind=pym.models.DbEngine, autocommit=True)
    DbBase.metadata.bind = pym.models.DbEngine
    runner.sess = DbSession()
    # noinspection PyBroadException
    try:
        runner.run()
    except Exception as exc:
        lgg.exception(exc)
        lgg.fatal('Program aborted!')
    else:
        lgg.info('Finished.')
    finally:
        lgg.debug('{} secs'.format(time.time() - start_time))
        pass


if __name__ == '__main__':
    main()
