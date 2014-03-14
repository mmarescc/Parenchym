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


SQL_VW_PRINCIPAL_BROWSE = """
CREATE OR REPLACE VIEW pym.vw_principal_browse AS
(
    SELECT principal.id                      AS id,
           principal.is_enabled              AS is_enabled,
           principal.disable_reason          AS disable_reason,
           principal.is_blocked              AS is_blocked,
           principal.blocked_since           AS blocked_since,
           principal.blocked_until           AS blocked_until,
           principal.block_reason            AS block_reason,
           principal.principal               AS principal,
           principal.pwd                     AS pwd,
           principal.pwd_expires             AS pwd_expires,
           principal.identity_url            AS identity_url,
           principal.email                   AS email,
           principal.first_name              AS first_name,
           principal.last_name               AS last_name,
           principal.display_name            AS display_name,
           principal.login_time              AS login_time,
           principal.login_ip                AS login_ip,
           principal.access_time             AS access_time,
           principal.kick_session            AS kick_session,
           principal.kick_reason             AS kick_reason,
           principal.logout_time             AS logout_time,
           principal.gui_token               AS gui_token,
           principal.notes                   AS notes,
           principal.mtime                   AS mtime,
           principal.editor                  AS editor,
           e.display_name                    AS editor_display_name,
           principal.ctime                   AS ctime,
           principal.owner                   AS owner,
           o.display_name                    AS owner_display_name
    FROM pym.principal
    LEFT OUTER JOIN pym.principal AS o ON pym.principal.owner = o.id
    LEFT OUTER JOIN pym.principal AS e ON pym.principal.editor = e.id
);"""

SQL_VW_ROLE_BROWSE = """
CREATE OR REPLACE VIEW pym.vw_role_browse AS
(
    SELECT role.id                      AS id,
           role.name                    AS name,
           role.notes                   AS notes,
           role.mtime                   AS mtime,
           role.editor                  AS editor,
           e.display_name               AS editor_display_name,
           role.ctime                   AS ctime,
           role.owner                   AS owner,
           o.display_name               AS owner_display_name
    FROM pym.role
    LEFT OUTER JOIN pym.principal AS o ON pym.role.owner = o.id
    LEFT OUTER JOIN pym.principal AS e ON pym.role.editor = e.id
);"""

SQL_VW_ROLEMEMBER_BROWSE = """
CREATE OR REPLACE VIEW pym.vw_rolemember_browse AS
(
    SELECT rm.id                             AS id,
           principal.id                      AS principal_id,
           principal.principal               AS principal_principal,
           principal.is_enabled              AS principal_is_enabled,
           principal.is_blocked              AS principal_is_blocked,
           principal.email                   AS principal_email,
           principal.first_name              AS principal_first_name,
           principal.last_name               AS principal_last_name,
           principal.display_name            AS principal_display_name,
           principal.notes                   AS principal_notes,
           role.id                           AS role_id,
           role.name                         AS role_name,
           role.notes                        AS role_notes,
           rm.ctime                          AS ctime,
           rm.owner                          AS owner,
           o.display_name                    AS owner_display_name
    FROM pym.rolemember rm
    -- Use outer joins to principal and role to see if we have
    -- member records for non-existing principals or roles.
    LEFT OUTER JOIN pym.principal      ON rm.principal_id = principal.id
    LEFT OUTER JOIN pym.role           ON rm.role_id      = role.id
    LEFT OUTER JOIN pym.principal AS o ON pym.principal.owner = o.id
);"""


class InitialiseDbCli(pym.cli.Cli):
    def __init__(self):
        super().__init__()

    def run(self):

        sess = pym.models.DbSession()
        with transaction.manager:
            pym.models.create_all()
            self._create_views(sess)
            if not self.args.schema_only:
                self._setup_users(sess)
            if self.args.alembic_config:
                alembic_cfg = Config(self.args.alembic_config)
                command.stamp(alembic_cfg, "head")
            mark_changed(sess)

    @staticmethod
    def _create_views(sess):
        sess.execute(SQL_VW_PRINCIPAL_BROWSE)
        sess.execute(SQL_VW_ROLE_BROWSE)
        sess.execute(SQL_VW_ROLEMEMBER_BROWSE)

    def _setup_users(self, sess):
        # 1// Create principal system
        p_system = usrmgr.create_principal(dict(
            id=SYSTEM_UID,
            principal='system',
            email='system@localhost',
            first_name='system',
            display_name='System',
            owner=SYSTEM_UID,
            # Roles do not exist yet. Do not auto-create them
            roles=False
        ))

        # 2// Create roles
        # This role should not have members.
        # Not-authenticated users are automatically member of 'everyone'
        usrmgr.create_role(dict(
            id=EVERYONE_RID,
            name='everyone',
            notes='Everyone (incl. unauthenticated users)',
            location_name='System',
            location_type='System',
            owner=SYSTEM_UID,
        ))
        usrmgr.create_role(dict(
            id=SYSTEM_RID,
            name='system',
            location_name='System',
            location_type='System',
            owner=SYSTEM_UID
        ))
        r_wheel = usrmgr.create_role(dict(
            id=WHEEL_RID,
            name='wheel',
            notes='Site Admins',
            location_name='System',
            location_type='System',
            owner=SYSTEM_UID
        ))
        r_users = usrmgr.create_role(dict(
            id=USERS_RID,
            name='users',
            notes='Authenticated Users',
            location_name='System',
            location_type='System',
            owner=SYSTEM_UID
        ))
        r_unit_testers = usrmgr.create_role(dict(
            id=UNIT_TESTERS_RID,
            name='unit testers',
            notes='Unit Testers',
            location_name='System',
            location_type='System',
            owner=SYSTEM_UID
        ))

        # 3// Put 'system' into its roles
        usrmgr.create_rolemember(dict(
            role_id=r_users.id,
            principal_id=p_system.id,
            owner=SYSTEM_UID
        ))
        usrmgr.create_rolemember(dict(
            role_id=r_wheel.id,
            principal_id=p_system.id,
            owner=SYSTEM_UID
        ))

        # 4// Create principals
        usrmgr.create_principal(dict(
            id=ROOT_UID,
            principal='root',
            email='root@localhost',
            first_name='root',
            display_name='Root',
            pwd=self.rc.g('auth.user_root.pwd'),
            is_enabled=True,
            user_type='System',
            owner=SYSTEM_UID,
            roles=[r_wheel.name, r_users.name]
        ))
        usrmgr.create_principal(dict(
            id=NOBODY_UID,
            principal='nobody',
            email='nobody@localhost',
            first_name='Nobody',
            display_name='Nobody',
            is_enabled=False,
            user_type='System',
            owner=SYSTEM_UID,
            # This principal is not member of any role
            # Not-authenticated users are automatically 'nobody'
            roles=False
        ))
        usrmgr.create_principal(dict(
            id=SAMPLE_DATA_UID,
            principal='sample_data',
            email='sample_data@localhost',
            first_name='Sample Data',
            display_name='Sample Data',
            is_enabled=False,
            user_type='System',
            owner=SYSTEM_UID,
            # This principal is not member of any role
            roles=False
        ))
        usrmgr.create_principal(dict(
            id=UNIT_TESTER_UID,
            principal='unit_tester',
            email='unit_tester@localhost',
            first_name='Unit-Tester',
            display_name='Unit-Tester',
            is_enabled=False,
            user_type='System',
            owner=SYSTEM_UID,
            roles=[r_unit_testers.name]
        ))

        # 5// Set sequence counter for user-created things
        # XXX PostgreSQL only
        # Regular users have ID > 100
        sess.execute('ALTER SEQUENCE pym.principal_id_seq RESTART WITH 101')
        # Regular roles have ID > 100
        sess.execute('ALTER SEQUENCE pym.role_id_seq RESTART WITH 101')
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
