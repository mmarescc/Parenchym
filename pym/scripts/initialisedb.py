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
import pym.authmgr.manager as usrmgr
from pym.authmgr.const import *

import pym.cli
import pym.lib
import pym.models


SQL_VW_USER_BROWSE = """
CREATE OR REPLACE VIEW pym.vw_user_browse AS
(
    SELECT "user".id                      AS id,
           "user".is_enabled              AS is_enabled,
           "user".disable_reason          AS disable_reason,
           "user".is_blocked              AS is_blocked,
           "user".blocked_since           AS blocked_since,
           "user".blocked_until           AS blocked_until,
           "user".block_reason            AS block_reason,
           "user".principal               AS principal,
           "user".pwd                     AS pwd,
           "user".pwd_expires             AS pwd_expires,
           "user".identity_url            AS identity_url,
           "user".email                   AS email,
           "user".first_name              AS first_name,
           "user".last_name               AS last_name,
           "user".display_name            AS display_name,
           "user".login_time              AS login_time,
           "user".login_ip                AS login_ip,
           "user".access_time             AS access_time,
           "user".kick_session            AS kick_session,
           "user".kick_reason             AS kick_reason,
           "user".logout_time             AS logout_time,
           "user".descr                   AS descr,
           "user".mtime                   AS mtime,
           "user".editor_id                  AS editor_id,
           e.display_name               AS editor_display_name,
           "user".ctime                   AS ctime,
           "user".owner_id                   AS owner_id,
           o.display_name               AS owner_display_name
    FROM      pym."user"
    JOIN      pym."user" AS o ON pym."user".owner_id = o.id
    LEFT JOIN pym."user" AS e ON pym."user".editor_id = e.id
);"""

SQL_VW_TENANT_BROWSE = """
CREATE OR REPLACE VIEW pym.vw_tenant_browse AS
(
    SELECT tenant.id                     AS id,
           tenant.name                   AS name,
           tenant.descr                  AS descr,
           tenant.mtime                  AS mtime,
           tenant.editor_id              AS editor_id,
           e.display_name                AS editor_display_name,
           tenant.ctime                  AS ctime,
           tenant.owner_id                  AS owner_id,
           o.display_name                AS owner_display_name
    FROM      pym.tenant
    JOIN      pym."user" AS o ON pym.tenant.owner_id = o.id
    LEFT JOIN pym."user" AS e ON pym.tenant.editor_id = e.id
);"""

SQL_VW_GROUP_BROWSE = """
CREATE OR REPLACE VIEW pym.vw_group_browse AS
(
    SELECT "group".id                      AS id,
           "group".tenant_id               AS tenant_id,
           t.name                        AS tenant_name,
           "group".name                    AS name,
           "group".descr                   AS descr,
           "group".mtime                   AS mtime,
           "group".editor_id                  AS editor_id,
           e.display_name                AS editor_display_name,
           "group".ctime                   AS ctime,
           "group".owner_id                   AS owner_id,
           o.display_name                AS owner_display_name
    FROM      pym."group"
    JOIN      pym."user" AS o ON pym."group".owner_id = o.id
    LEFT JOIN pym."user" AS e ON pym."group".editor_id = e.id
    LEFT JOIN pym.tenant AS t ON pym."group".tenant_id = t.id
);"""

SQL_VW_GROUP_MEMBER_BROWSE = """
CREATE OR REPLACE VIEW pym.vw_group_member_browse AS
(
    SELECT gm.id                        AS id,
           "group".id                     AS group_id,
           tenant.id                    AS tenant_id,
           tenant.name                  AS tenant_name,
           "group".name                   AS group_name,
           "user".id                      AS user_id,
           "user".principal               AS user_principal,
           "user".email                   AS user_email,
           "user".display_name            AS user_display_name,
           gro.id                       AS other_group_id,
           gro.name                     AS other_group_name,
           gm.ctime                     AS ctime,
           gm.owner_id                     AS owner_id,
           o.display_name               AS owner_display_name
    FROM      pym.group_member gm
    JOIN      pym."user"  AS o      ON gm.owner_id    = o.id
    JOIN      pym."group"           ON gm.group_id       = "group".id
    LEFT JOIN pym."user"            ON gm.user_id        = "user".id
    LEFT JOIN pym."group" AS gro    ON gm.other_group_id = gro.id
    LEFT JOIN pym.tenant            ON "group".tenant_id      = tenant.id
);"""


class InitialiseDbCli(pym.cli.Cli):
    def __init__(self):
        super().__init__()

    def run(self):

        sess = self._sess
        with transaction.manager:
            self._create_schema(sess)
            pym.models.create_all()
            self._create_views(sess)
            if not self.args.schema_only:
                self._setup_users(sess)
            if self.args.alembic_config:
                alembic_cfg = Config(self.args.alembic_config)
                command.stamp(alembic_cfg, "head")
            mark_changed(sess)

    @staticmethod
    def _create_schema(sess):
        sess.execute('CREATE SCHEMA IF NOT EXISTS pym')
        mark_changed(sess)
        transaction.commit()

    @staticmethod
    def _create_views(sess):
        sess.execute(SQL_VW_USER_BROWSE)
        sess.execute(SQL_VW_TENANT_BROWSE)
        sess.execute(SQL_VW_GROUP_BROWSE)
        sess.execute(SQL_VW_GROUP_MEMBER_BROWSE)

    def _setup_users(self, sess):
        # 1// Create user system
        p_system = usrmgr.create_user(dict(
            id=SYSTEM_UID,
            principal='system',
            email='system@localhost',
            first_name='system',
            display_name='System',
            owner_id=SYSTEM_UID,
            # Groups do not exist yet. Do not auto-create them
            groups=False
        ))

        # 2// Create groups
        # This group should not have members.
        # Not-authenticated users are automatically member of 'everyone'
        usrmgr.create_group(dict(
            id=EVERYONE_RID,
            name='everyone',
            descr='Everyone (incl. unauthenticated users)',
            location_name='System',
            location_type='System',
            owner_id=SYSTEM_UID,
        ))
        usrmgr.create_group(dict(
            id=SYSTEM_RID,
            name='system',
            location_name='System',
            location_type='System',
            owner_id=SYSTEM_UID
        ))
        r_wheel = usrmgr.create_group(dict(
            id=WHEEL_RID,
            name='wheel',
            descr='Site Admins',
            location_name='System',
            location_type='System',
            owner_id=SYSTEM_UID
        ))
        r_users = usrmgr.create_group(dict(
            id=USERS_RID,
            name='users',
            descr='Authenticated Users',
            location_name='System',
            location_type='System',
            owner_id=SYSTEM_UID
        ))
        r_unit_testers = usrmgr.create_group(dict(
            id=UNIT_TESTERS_RID,
            name='unit testers',
            descr='Unit Testers',
            location_name='System',
            location_type='System',
            owner_id=SYSTEM_UID
        ))

        # 3// Put 'system' into its groups
        usrmgr.create_group_member(dict(
            group_id=r_users.id,
            user_id=p_system.id,
            owner_id=SYSTEM_UID
        ))
        usrmgr.create_group_member(dict(
            group_id=r_wheel.id,
            user_id=p_system.id,
            owner_id=SYSTEM_UID
        ))

        # 4// Create users
        usrmgr.create_user(dict(
            id=ROOT_UID,
            principal='root',
            email='root@localhost',
            first_name='root',
            display_name='Root',
            pwd=self.rc.g('auth.user_root.pwd'),
            is_enabled=True,
            user_type='System',
            owner_id=SYSTEM_UID,
            groups=[r_wheel.name, r_users.name]
        ))
        usrmgr.create_user(dict(
            id=NOBODY_UID,
            principal='nobody',
            email='nobody@localhost',
            first_name='Nobody',
            display_name='Nobody',
            is_enabled=False,
            user_type='System',
            owner_id=SYSTEM_UID,
            # This user is not member of any group
            # Not-authenticated users are automatically 'nobody'
            groups=False
        ))
        usrmgr.create_user(dict(
            id=SAMPLE_DATA_UID,
            principal='sample_data',
            email='sample_data@localhost',
            first_name='Sample Data',
            display_name='Sample Data',
            is_enabled=False,
            user_type='System',
            owner_id=SYSTEM_UID,
            # This user is not member of any group
            groups=False
        ))
        usrmgr.create_user(dict(
            id=UNIT_TESTER_UID,
            principal='unit_tester',
            email='unit_tester@localhost',
            first_name='Unit-Tester',
            display_name='Unit-Tester',
            is_enabled=False,
            user_type='System',
            owner_id=SYSTEM_UID,
            groups=[r_unit_testers.name]
        ))

        # 5// Set sequence counter for user-created things
        # XXX PostgreSQL only
        # Regular users have ID > 100
        sess.execute('ALTER SEQUENCE pym.user_id_seq RESTART WITH 101')
        # Regular groups have ID > 100
        sess.execute('ALTER SEQUENCE pym.group_id_seq RESTART WITH 101')
        sess.flush()


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
