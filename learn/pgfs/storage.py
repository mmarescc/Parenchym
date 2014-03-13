import argparse
import datetime
import magic
import os
import sys

__author__ = 'dm'

"""
Stores file in PostgresQL table
"""

import libdb


class Storage():

    SCHEMA = 'pympgfs'

    def __init__(self, L, rc, db):
        self.L = L
        self.rc = rc
        self.db = db
        self.args = None

    def run(self, args):
        self.args = args
        if args.cmd == 'init':
            self.create_tables()
        elif args.cmd == 'drop':
            self.drop_tables()
        elif args.cmd == 'store':
            filename = args.filename
            type_ = args.type
            self.store(filename, type_)
        elif args.cmd == 'dump':
            filename = args.filename
        elif args.cmd == 'unlink':
            id_ = args.filename
            self.unlink(id_)
        elif args.cmd == 'clear':
            self.clear()
        else:
            raise Exception("Invalid command: '{}'".format(args.cmd))

    def clear(self):
        self.L.info("Clearing file system...")
        with self.db.cursor() as cr:
            cr.execute("SELECT id, lob_oid FROM {schema}.node".format(schema=self.SCHEMA))
            for r in cr:
                if r[1]:
                    self._unlink_lob(r[0])
                else:
                    self._unlink_bytea(r[0])

    def store(self, filename, type_, parent_id=None, attr=None, acl=None):
        self.L.info("Storing file '{}'".format(filename))
        info = dict(
            parent_id=parent_id,
            attr=attr,
            acl=acl,
            lob_oid=None,
            data_id=None
        )
        info['name'] = os.path.basename(filename)
        dirname = os.path.dirname(filename)
        if dirname:
            pass  # TODO Determine parent_id from dirname
        info['mime_type'] = magic.from_file(filename, mime=True).decode('ASCII')
        si = os.stat(filename)
        info['size'] = si.st_size
        info['ctime'] = datetime.datetime.fromtimestamp(si.st_ctime)
        info['mtime'] = datetime.datetime.fromtimestamp(si.st_mtime)
        info['atime'] = datetime.datetime.fromtimestamp(si.st_atime)

        with self.db.cursor() as cr:
            if os.path.isfile(filename):
                if type_ == 'lob':
                    lob = self._store_lob(filename)
                    info['lob_oid'] = lob.oid
                elif type_ == 'bytea':
                    with open(filename, 'rb') as fh:
                        data = fh.read()
                        cr.execute("INSERT INTO {schema}.nodedata (data)"
                            " VALUES(%s) RETURNING id".format(schema=self.SCHEMA),
                            (data, )
                        )
                    info['data_id'] = cr.fetchone()[0]
                else:
                    raise Exception("Invalid type '{}'".format(type_))

            cols = list(info.keys())
            ff = ['%s'] * len(cols)
            vv = [info[c] for c in cols]
            q = "INSERT INTO {schema}.node ({cols}) VALUES ({fields}) RETURNING id".format(
                schema=self.SCHEMA, cols=','.join(cols), fields=','.join(ff)
            )
            #print(cr.mogrify(q, vv))
            cr.execute(q, vv)
            id_ = cr.fetchone()[0]
            self.L.debug('Node ID: {}'.format(id_))
            return id_

    def _store_lob(self, filename):
        self.L.debug("Storing as large object")
        lob = self.db.dbh.lobject(oid=0, mode='w', new_oid=0, new_file=filename)
        # self.L.debug("LOB OID: {}".format(lob.oid))
        lob.seek(0, 2)
        self.L.debug("LOB OID: {}, size: {}".format(lob.oid, lob.tell()))
        lob.seek(0, 0)
        return lob

    def unlink(self, id_):
        self.L.info("Unlinking file '{}'".format(id_))
        with self.db.cursor() as cr:
            cr.execute("SELECT lob_oid FROM {schema}.node WHERE id=%s".format(
                schema=self.SCHEMA), (id_, ))

            if cr.fetchone()[0]:
                self._unlink_lob(id_)
            else:
                self._unlink_bytea(id_)

    def _unlink_lob(self, id_):
        self.L.info("Unlinking large object file: '{}'".format(id_))
        with self.db.cursor() as cr:
            cr.execute("SELECT lob_oid FROM {schema}.node WHERE id=%s".format(schema=self.SCHEMA), (id_, ))
            lob_oid = cr.fetchone()[0]
            lob = self.db.dbh.lobject(oid=lob_oid, mode='r')
            lob.unlink()
            cr.execute("DELETE FROM {schema}.node WHERE id=%s".format(schema=self.SCHEMA), (id_, ))

    def _unlink_bytea(self, id_):
        self.L.info("Unlinking bytea file: '{}'".format(id_))
        with self.db.cursor() as cr:
            cr.execute("SELECT data_id FROM {schema}.node WHERE id=%s".format(schema=self.SCHEMA), (id_, ))
            data_id = cr.fetchone()[0]
            cr.execute("DELETE FROM {schema}.nodedata WHERE id=%s".format(schema=self.SCHEMA), (data_id, ))
            cr.execute("DELETE FROM {schema}.node WHERE id=%s".format(schema=self.SCHEMA), (id_, ))

    def create_tables(self):
        self.L.info("Initialising tables...")
        cr = self.db.cursor()
        cr.execute("CREATE SCHEMA {schema}".format(
            schema=self.SCHEMA
        ))
        cr.execute("""CREATE TABLE {schema}.node (
            id serial                     NOT NULL
            , parent_id integer           NULL
            , name varchar(255)           NOT NULL
            , mime_type varchar(255)      NOT NULL
            , size integer                NOT NULL
            , attr json                   NULL
            , acl json                    NULL
            , ctime timestamp             NOT NULL
            , atime timestamp             NOT NULL
            , mtime timestamp             NOT NULL
            , data_id integer             NULL
            , lob_oid integer             NULL
            , PRIMARY KEY (id)
        )
        """.format(
            schema=self.SCHEMA
        ))
        cr.execute("CREATE INDEX node_ux "
                   "ON {schema}.node (parent_id, name)".format(
            schema=self.SCHEMA
        ))
        cr.execute("""CREATE TABLE {schema}.nodedata (
            id serial                     NOT NULL
            , data bytea                  NOT NULL
            , PRIMARY KEY (id)
        )
        """.format(
            schema=self.SCHEMA
        ))

    def drop_tables(self):
        self.clear()
        self.L.info("Dropping tables...")
        cr = self.db.cursor()
        cr.execute("DROP SCHEMA {schema} CASCADE".format(
            schema=self.SCHEMA
        ))


if __name__ == '__main__':
    import logging

    rc = {}
    dsn = "postgresql://test:test@localhost/test"

    logging.basicConfig(level=logging.DEBUG, stream=sys.stderr)
    L = logging.getLogger()

    def import_tree(start_dir):
        db = libdb.Db(L, dsn)
        try:
            sto = Storage(L, rc, db)
            parent_id = None
            id_ = sto.store(start_dir, type_='bytea', parent_id=parent_id)
            ids = {start_dir: id_}
            for root, dirs, files in os.walk(start_dir):
                try:
                    dirs.remove('.git')
                except ValueError:
                    pass
                parent_id = ids[root]
                for f in dirs:
                    fn = os.path.join(root, f)
                    print(fn)
                    ids[fn] = sto.store(fn, type_='bytea', parent_id=parent_id)
                for f in files:
                    fn = os.path.join(root, f)
                    print(fn)
                    ids[fn] = sto.store(fn, type_='bytea', parent_id=parent_id)
        except Exception as exc:
            db.dbh.rollback()
            raise
        else:
            db.dbh.commit()

    def cli():
        # Main parser
        parser = argparse.ArgumentParser(
            description="Pym command-line interface.")
        parser.add_argument('--dsn',
            default=dsn,
            help="Data Source Name"
        )
        parser.add_argument('-t', '--type',
            default="bytea",
            choices=['bytea', 'lob'],
            help="Storage type defines how binary data is stored, as bytea or"
                 " large object"
        )
        parser.add_argument('cmd',
            choices=['dump', 'store', 'unlink', 'clear', 'init', 'drop'],
            help="Command (dump, store, unlink a file; clear all files; init, drop tables)"
        )
        parser.add_argument('filename',
            help="Filename"
        )

        # Parse args and run command
        args = parser.parse_args()

        db = libdb.Db(L, args.dsn)
        sto = Storage(L, rc, db)
        try:
            sto.run(args)
        except Exception as exc:
            db.dbh.rollback()
            raise
        else:
            db.dbh.commit()


    import_tree('/home/dm/myprojects/Parenchym')
    #cli()