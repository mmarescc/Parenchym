import sqlalchemy as sa
from pym.auth.models import User, Group, GroupMember
from pym.auth.manager import create_group_member
from pym.res.models import ResourceNode
from pym.res.const import NODE_ROOT, NODE_SYS
from pym.auth.const import SYSTEM_UID, NODE_SYS_AUTH_MGR, GROUP_KIND_TENANT
from .const import NODE_TENANT_MGR, DEFAULT_TENANT_NAME, DEFAULT_TENANT_TITLE
from . import manager as tmgr


def setup_resources(sess):
    n_root = ResourceNode.load_root(sess, name=NODE_ROOT, use_cache=False)
    n_sys_auth = n_root[NODE_SYS][NODE_SYS_AUTH_MGR]

    n_sys_auth.add_child(
        sess=sess, owner=SYSTEM_UID,
        kind="res", name=NODE_TENANT_MGR, title='Tenant Manager',
        iface='pym.auth.models.ITenantMgrNode')


def setup_tenants(sess):
    # Create tenant. Cascade also creates a resource and a group
    tmgr.create_tenant(sess, SYSTEM_UID, name=DEFAULT_TENANT_NAME,
        title=DEFAULT_TENANT_TITLE, cascade=True)
    # Put all so far existing users into our group
    g = sess.query(Group).filter(sa.and_(
        Group.tenant_id == None,
        Group.name == DEFAULT_TENANT_NAME,
        Group.kind == GROUP_KIND_TENANT
    )).one()
    uu = sess.query(User)
    for u in uu:
        create_group_member(sess, owner=SYSTEM_UID, group=g, member_user=u)


def setup(sess, schema_only=False):
    if not schema_only:
        setup_resources(sess)
        setup_tenants(sess)