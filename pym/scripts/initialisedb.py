import time
import transaction
import argparse
import logging
import sys
import os

from zope.sqlalchemy import mark_changed

from alembic.config import Config
from alembic import command

import pym.models
import pym.cli
import pym.lib
import pym.auth.setup
import pym.res.setup
import pym.tenants.setup

import pym.cli
import pym.lib
import pym.models


class InitialiseDbCli(pym.cli.Cli):
    def __init__(self):
        super().__init__()

    def run(self):
        root_pwd = self.rc.g('auth.user_root.pwd')
        self._config.scan('pym')
        sess = self._sess

        # Create schema 'pym' and all models
        with transaction.manager:
            self._create_schema(sess)
        with transaction.manager:
            pym.models.create_all()

        with transaction.manager:
            # Users and stuff we need to setup the other modules
            pym.auth.setup.setup_basics(sess, root_pwd,
                schema_only=self.args.schema_only)
            sess.flush()
            # Setup each module
            pym.res.setup.setup(sess, schema_only=self.args.schema_only)
            sess.flush()
            pym.auth.setup.setup(sess, schema_only=self.args.schema_only)
            sess.flush()
            pym.tenants.setup.setup(sess, schema_only=self.args.schema_only)
            sess.flush()

            if self.args.alembic_config:
                alembic_cfg = Config(self.args.alembic_config)
                command.stamp(alembic_cfg, "head")

            mark_changed(sess)

    @staticmethod
    def _create_schema(sess):
        sess.execute('CREATE SCHEMA IF NOT EXISTS pym')
        mark_changed(sess)


def parse_args(app_class):
    # Main parser
    parser = argparse.ArgumentParser(
        description="InitialiseDb command-line interface."
    )
    app_class.add_parser_args(parser, (('config', True),
        ('locale', False), ('alembic-config', False)))
    parser.add_argument(
        '--schema-only',
        action='store_true',
        help="""Create only schema without inserting users etc."""
    )
    return parser.parse_args()


def main(argv=None):
    if not argv:
        argv = sys.argv
    start_time = time.time()
    app_name = os.path.basename(argv[0])
    lgg = logging.getLogger('cli.' + app_name)

    args = parse_args(InitialiseDbCli)
    runner = InitialiseDbCli()
    runner.init_app(args, lgg=lgg, setup_logging=True)
    # noinspection PyBroadException
    try:
        runner.run()
    except Exception as exc:
        lgg.exception(exc)
        lgg.fatal('Program aborted!')
    else:
        lgg.info('Finished in {} secs.'.format(time.time() - start_time))
        lgg.info("Directory 'install/db' may contain SQL scripts"
              " you have to run manually.")
    finally:
        # Do some cleanup or saving etc.
        pass


if __name__ == '__main__':
    main(sys.argv)
