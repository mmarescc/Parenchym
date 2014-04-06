from .models import ResourceNode
from ..auth.const import SYSTEM_UID, WHEEL_RID


# noinspection PyUnusedLocal
def create_views(sess):
    pass


def setup_resources(sess):
    n_root = ResourceNode.create_root(sess=sess, owner=SYSTEM_UID, kind="res",
        name='root', title='Root',
        iface='pym.res.models:IRootNode')

    n_help = n_root.add_child(sess=sess, owner=SYSTEM_UID, kind="res",
        name='help', title='Help',
        iface='pym.res.models:IHelpNode')

    n_sys = n_root.add_child(sess=sess, owner=SYSTEM_UID, kind="res",
        name='__sys__', title='System',
        iface='pym.res.models:ISystemNode')

    n_sys_auth = n_sys.add_child(sess=sess, owner=SYSTEM_UID, kind="res",
        name='auth', title='AuthManager',
        iface='pym.auth.models:IAuthNode')

    n_sys_auth_users = n_sys_auth.add_child(sess=sess, owner=SYSTEM_UID,
        kind="res", name='users', title='Users',
        iface='pym.auth.models:IUsersNode')

    n_sys_auth_tenants = n_sys_auth.add_child(sess=sess, owner=SYSTEM_UID,
        kind="res", name='tenants', title='Tenants',
        iface='pym.auth.models:ITenantsNode')

    n_sys_auth_groups = n_sys_auth.add_child(sess=sess, owner=SYSTEM_UID,
        kind="res", name='groups', title='Groups',
        iface='pym.auth.models:IGroupsNode')

    n_sys_auth_group_members = n_sys_auth.add_child(sess=sess, owner=SYSTEM_UID,
        kind="res", name='group_members', title='Group Members',
        iface='pym.auth.models:IGroupMembersNode')

    n_sys_auth_permissions = n_sys_auth.add_child(sess=sess, owner=SYSTEM_UID,
        kind="res", name='permissions', title='Permissions',
        iface='pym.auth.models:IPermissionsNode')

    return n_root


def setup_acl(sess, n_root):
    # Grant group 'wheel' all permissions on resource 'root'.
    n_root.allow(sess, SYSTEM_UID, '*', group=WHEEL_RID)


def setup(sess, schema_only=False):
    create_views(sess)
    if not schema_only:
        n_root = setup_resources(sess)
        setup_acl(sess, n_root)
