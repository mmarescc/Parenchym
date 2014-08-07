#!/usr/bin/env python

"""
Dumps a table in PostgreSQL dump format.

Connects to database using the provided SQLAlchemy URL. Specify a table to dump
and optionally an SQL SELECT statement.
"""

import logging
import os
import argparse
import sys
import time
import datetime
import re
import sqlalchemy as sa

import pym.cli


class Runner(pym.cli.Cli):

    def __init__(self):
        super().__init__()
        self.table = None
        self.sql = None

    def run(self):
        self.process_args()
        engine = sa.create_engine(self.args.sa_url)
        url = re.sub(r':[^:]+?@', ':***@', self.args.sa_url)
        self.lgg.info('Connecting to {}'.format(url))
        conn = engine.connect()
        try:
            rs = conn.execute(self.sql)
            self.dump(self.table, rs)
        finally:
            conn.close()

    def dump(self, table, rs):
        self.lgg.info("Dumping '{}'".format(self.sql))
        kk = rs.keys()
        # COPY table (col1, col2, col3) FROM stdin;
        # \.
        print('COPY {} ({}) FROM stdin;'.format(table, ','.join(kk)))
        for i, r in enumerate(rs):
            a = []
            for k in kk:
                if r[k] is None:
                    v = '\\N'
                else:
                    if hasattr(r[k], 'decode'):
                        v = '\\N'  # Binary not supported: NULLify
                    else:
                        v = str(r[k])
                        v = v.strip()
                        v = v.replace("\\", '\\\\')
                        v = v.replace("\t", '\\T')
                        if not len(v):
                            v = '\\N'
                a.append(v)
            print("\t".join(a))
        print('\\.')
        self.lgg.info("Dumped {n} rows for table {t}".format(
            n=i, t=table
        ))

    def process_args(self):
        self.table = self.args.table
        if self.args.select:
            self.sql = sa.text(self.args.select)
        else:
            self.sql = sa.text("SELECT * FROM " + self.table)


def parse_args(app_class):
    parser = argparse.ArgumentParser(
        description=__doc__
    )
    app_class.add_parser_args(
        parser,
        (('config', True), ('locale', False), ('alembic-config', False))
    )
    parser.add_argument(
        '--sa-url',
        required=True,
        help="""The SQLAlchemy URL to connect to the database"""
    )
    parser.add_argument(
        '-t', '--table',
        required=True,
        help="""Name of the table to dump"""
    )
    parser.add_argument(
        '--select',
        help="""A select statement"""
    )

    return parser.parse_args()


def main(argv=None):
    start_time = time.time()
    if not argv:
        argv = sys.argv

    app_name = os.path.basename(argv[0])
    lgg = logging.getLogger('cli.' + app_name)
    args = parse_args(Runner)
    try:
        runner = Runner()
        runner.init_app(args, lgg=lgg, setup_logging=True)
        runner.run()
    except Exception as exc:
        lgg.exception(exc)
        lgg.fatal('Program aborted!')
    else:
        lgg.info('Finished.')
    finally:
        # Typically, perform some important clean-up here...
        lgg.info('Time taken: {}'.format(
            datetime.timedelta(seconds=time.time() - start_time))
        )

if __name__ == '__main__':
    main()