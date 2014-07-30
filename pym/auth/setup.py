from pym.res.models import ResourceNode
from pym.res.const import NODE_NAME_ROOT, NODE_NAME_SYS
from . import manager as authmgr
from .const import *
from .models import Permission, Permissions


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
           gr.id                        AS group_id,
           tenant.id                    AS tenant_id,
           tenant.name                  AS tenant_name,
           gr.name                      AS group_name,
           mu.id                        AS member_user_id,
           mu.principal                 AS member_user_principal,
           mu.email                     AS member_user_email,
           mu.display_name              AS member_user_display_name,
           mgr.id                       AS member_group_id,
           mgr.name                     AS member_group_name,
           gm.ctime                     AS ctime,
           gm.owner_id                  AS owner_id,
           o.display_name               AS owner_display_name
    FROM      pym.group_member gm
    JOIN      pym."user"  AS o      ON gm.owner_id        = o.id
    JOIN      pym."group" AS gr     ON gm.group_id        = gr.id
    LEFT JOIN pym."user"  AS mu     ON gm.member_user_id  = mu.id
    LEFT JOIN pym."group" AS mgr    ON gm.member_group_id = mgr.id
    LEFT JOIN pym.tenant            ON gr.tenant_id       = tenant.id
);"""

# -- List all permissions with their respective parent path.
# -- Root permissions (i.e. without parent) are also listed.
# id    name       parents
# 1      *         NULL
# 2    visit       NULL
# 3    read        {{2,visit}}
# 4    admin       {{2,visit}}
# 5    delete      {{2,visit}}
# 6    write       {{2,visit},{3,read}}
# 7    admin_auth  {{2,visit},{4,admin}}
# 8    admin_res   {{2,visit},{4,admin}}
SQL_VW_PERMISSIONS_WITH_PARENTS = """
CREATE OR REPLACE VIEW pym.vw_permissions_with_parents AS
(
    WITH RECURSIVE other AS
    (
      -- non-recursive term
      SELECT
        ARRAY [ARRAY [p.id :: TEXT, p.name :: TEXT]] AS path,
        NULL :: TEXT []                              AS parents,
        p.id,
        p.parent_id,
        p.name
      FROM pym.permission_tree p
      WHERE p.parent_id IS NULL

      UNION ALL

      -- recursive term
      SELECT
        other.path || ARRAY [p.id :: TEXT, p.name :: TEXT] AS path,
        path [0 : array_upper(path, 1) + 1]                 AS parents,
        p.id,
        p.parent_id,
        p.name
      FROM
        pym.permission_tree AS p
        JOIN other AS other
          ON (p.parent_id = other.id)
    )
    SELECT
      id,
      name,
      parents
    FROM other
    ORDER BY parents NULLS FIRST
)
"""

# -- List all permissions with their children.
# -- CAVEAT: Permissions without children do not appear in result!
# id    name    children
# 4    admin    {{7,admin_auth}}
# 4    admin    {{8,admin_res}}
# 3    read     {{6,write}}
# 2    visit    {{3,read}}
# 2    visit    {{3,read},{6,write}}
# 2    visit    {{4,admin}}
# 2    visit    {{4,admin},{7,admin_auth}}
# 2    visit    {{4,admin},{8,admin_res}}
# 2    visit    {{5,delete}}
SQL_VW_PERMISSIONS_WITH_CHILDREN = """
CREATE OR REPLACE VIEW pym.vw_permissions_with_children AS
(
    WITH RECURSIVE other AS
    (
      -- non-recursive term
      SELECT
        ARRAY [ARRAY [p.id :: TEXT, p.name :: TEXT]] AS path,
        NULL :: TEXT []                              AS children,
        p.id,
        p.parent_id,
        name
      FROM pym.permission_tree p
      WHERE p.parent_id IS NOT NULL

      UNION ALL

      -- recursive term
      SELECT
        ARRAY [p.id :: TEXT, p.name :: TEXT] || other.path AS path,
        path [1 : array_upper(path, 1)]                     AS children,
        p.id,
        p.parent_id,
        p.name
      FROM
        pym.permission_tree AS p
        JOIN other AS other
          ON (p.id = other.parent_id)
    )
    SELECT
      id,
      name,
      children
    FROM other
    WHERE array_length(children, 1) > 0
    ORDER BY name, children
)
"""


def create_views(sess):
    sess.execute(SQL_VW_USER_BROWSE)
    sess.execute(SQL_VW_TENANT_BROWSE)
    sess.execute(SQL_VW_GROUP_BROWSE)
    sess.execute(SQL_VW_GROUP_MEMBER_BROWSE)
    sess.execute(SQL_VW_PERMISSIONS_WITH_PARENTS)
    sess.execute(SQL_VW_PERMISSIONS_WITH_CHILDREN)


def setup_users(sess, root_pwd):
    # 1// Create user system
    u_system = authmgr.create_user(
        sess,
        owner=SYSTEM_UID,
        id=SYSTEM_UID,
        is_enabled=False,
        principal='system',
        pwd=None,
        email='system@localhost',
        first_name='system',
        display_name='System',
        # Groups do not exist yet. Do not auto-create them
        groups=False
    )

    # 2// Create groups
    # This group should not have members.
    # Not-authenticated users are automatically member of 'everyone'
    authmgr.create_group(
        sess,
        owner=SYSTEM_UID,
        id=EVERYONE_RID,
        name='everyone',
        descr='Everyone (incl. unauthenticated users)',
        kind=GROUP_KIND_SYSTEM
    )
    authmgr.create_group(
        sess,
        owner=SYSTEM_UID,
        id=SYSTEM_RID,
        name='system',
    )
    g_wheel = authmgr.create_group(
        sess,
        owner=SYSTEM_UID,
        id=WHEEL_RID,
        name='wheel',
        descr='Site Admins',
        kind=GROUP_KIND_SYSTEM
    )
    g_users = authmgr.create_group(
        sess,
        owner=SYSTEM_UID,
        id=USERS_RID,
        name='users',
        descr='Authenticated Users',
        kind=GROUP_KIND_SYSTEM
    )
    g_unit_testers = authmgr.create_group(
        sess,
        owner=SYSTEM_UID,
        id=UNIT_TESTERS_RID,
        name='unit testers',
        descr='Unit Testers',
        kind=GROUP_KIND_SYSTEM
    )

    # 3// Put 'system' into its groups
    authmgr.create_group_member(
        sess,
        owner=SYSTEM_UID,
        group=g_users,
        member_user=u_system,
    )
    authmgr.create_group_member(
        sess,
        owner=SYSTEM_UID,
        group=g_wheel,
        member_user=u_system
    )

    # 4// Create users
    authmgr.create_user(
        sess,
        owner=SYSTEM_UID,
        id=ROOT_UID,
        principal='root',
        email='root@localhost',
        first_name='root',
        display_name='Root',
        pwd=root_pwd,
        is_enabled=True,
        groups=[g_wheel.name, g_users.name]
    )
    authmgr.create_user(
        sess,
        owner=SYSTEM_UID,
        id=NOBODY_UID,
        principal='nobody',
        pwd=None,
        email='nobody@localhost',
        first_name='Nobody',
        display_name='Nobody',
        is_enabled=False,
        # This user is not member of any group
        # Not-authenticated users are automatically 'nobody'
        groups=False
    )
    authmgr.create_user(
        sess,
        owner=SYSTEM_UID,
        id=SAMPLE_DATA_UID,
        principal='sample_data',
        pwd=None,
        email='sample_data@localhost',
        first_name='Sample Data',
        display_name='Sample Data',
        is_enabled=False,
        # This user is not member of any group
        groups=False
    )
    authmgr.create_user(
        sess,
        owner=SYSTEM_UID,
        id=UNIT_TESTER_UID,
        principal='unit_tester',
        pwd=None,
        email='unit_tester@localhost',
        first_name='Unit-Tester',
        display_name='Unit-Tester',
        is_enabled=False,
        user_type='System',
        groups=[g_unit_testers.name]
    )

    # 5// Set sequence counter for user-created things
    # XXX PostgreSQL only
    # Regular users have ID > 100
    sess.execute('ALTER SEQUENCE pym.user_id_seq RESTART WITH 101')
    # Regular groups have ID > 100
    sess.execute('ALTER SEQUENCE pym.group_id_seq RESTART WITH 101')
    sess.flush()


def setup_permissions(sess):
    """
    Sets up permission tree as follows:

        visit:                  visit a node
         |
         +-- read:              read an object
         |    +-- write:        write an object
         +-- delete:            delete an object
         |
         +-- admin
              +-- admin_auth:   admin users, groups, permissions, ACL
              +-- admin_res:    admin resources
    """
    p_all = Permission()
    p_all.owner_id = SYSTEM_UID
    p_all.name = Permissions.all.value
    p_all.descr = "All permissions."

    p_visit = Permission()
    p_visit.owner_id = SYSTEM_UID
    p_visit.name = Permissions.visit.value
    p_visit.descr = "Permission to visit this node. This is weaker than 'read'."

    p_read = Permission()
    p_read.owner_id = SYSTEM_UID
    p_read.name = Permissions.read.value
    p_read.descr = "Permission to read this resource."

    p_write = Permission()
    p_write.owner_id = SYSTEM_UID
    p_write.name = Permissions.write.value
    p_write.descr = "Permission to write this resource."

    p_delete = Permission()
    p_delete.owner_id = SYSTEM_UID
    p_delete.name = Permissions.delete.value
    p_delete.descr = "Permission to delete this resource."

    p_admin = Permission()
    p_admin.owner_id = SYSTEM_UID
    p_admin.name = Permissions.admin.value
    p_admin.descr = "Permission to administer in general."

    p_admin_auth = Permission()
    p_admin_auth.owner_id = SYSTEM_UID
    p_admin_auth.name = Permissions.admin_auth.value
    p_admin_auth.descr = "Permission to administer authentication and "\
        "authorization, like users, groups, permissions and ACL on resources."

    p_admin_res = Permission()
    p_admin_res.owner_id = SYSTEM_UID
    p_admin_res.name = Permissions.admin_res.value
    p_admin_res.descr = "Permission to administer resources."

    p_visit.add_child(p_read)
    p_visit.add_child(p_delete)
    p_visit.add_child(p_admin)

    p_read.add_child(p_write)

    p_admin.add_child(p_admin_auth)
    p_admin.add_child(p_admin_res)

    sess.add(p_all)
    sess.add(p_visit)


def setup_resources(sess):
    n_root = ResourceNode.load_root(sess, name=NODE_NAME_ROOT, use_cache=False)
    n_sys = n_root[NODE_NAME_SYS]

    n_sys_auth = n_sys.add_child(sess=sess, owner=SYSTEM_UID, kind="res",
        name=NODE_NAME_SYS_AUTH_MGR, title='AuthManager',
        iface='pym.auth.models.IAuthMgrNode')

    n_sys_auth.add_child(sess=sess, owner=SYSTEM_UID,
        kind="res", name=NODE_NAME_SYS_AUTH_USER_MGR, title='User Manager',
        iface='pym.auth.models.IUserMgrNode')

    n_sys_auth.add_child(sess=sess, owner=SYSTEM_UID,
        kind="res", name=NODE_NAME_SYS_AUTH_GROUP_MGR, title='Group Manager',
        iface='pym.auth.models.IGroupMgrNode')

    n_sys_auth.add_child(sess=sess, owner=SYSTEM_UID,
        kind="res", name=NODE_NAME_SYS_AUTH_GROUP_MEMBER_MGR,
        title='Group Member Manager',
        iface='pym.auth.models.IGroupMemberMgrNode')

    n_sys_auth.add_child(sess=sess, owner=SYSTEM_UID,
        kind="res", name=NODE_NAME_SYS_AUTH_PERMISSION_MGR, title='Permission Manager',
        iface='pym.auth.models.IPermissionMgrNode')


def setup_basics(sess, root_pwd, schema_only=False):
    create_views(sess)
    if not schema_only:
        setup_users(sess, root_pwd)
        setup_permissions(sess)


def setup(sess, schema_only=False):
    if not schema_only:
        setup_resources(sess)
