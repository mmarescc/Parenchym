
from pym.auth.const import SYSTEM_UID, WHEEL_RID
from .models import ResourceNode
from .const import *


def setup_resources(sess):
    n_root = ResourceNode.create_root(sess=sess, owner=SYSTEM_UID, kind="res",
        name=NODE_NAME_ROOT, title='Root',
        iface='pym.res.models.IRootNode')

    n_root.add_child(sess=sess, owner=SYSTEM_UID, kind="res",
        name=NODE_NAME_HELP, title='Help',
        iface='pym.res.models.IHelpNode')

    n_root.add_child(sess=sess, owner=SYSTEM_UID, kind="res",
        name=NODE_NAME_SYS, title='System',
        iface='pym.res.models.ISystemNode')

    return n_root


def setup_acl(sess, n_root):
    # Grant group 'wheel' all permissions on resource 'root'.
    n_root.allow(sess, SYSTEM_UID, '*', group=WHEEL_RID)


def setup(sess, schema_only=False):
    #create_views(sess)
    if not schema_only:
        n_root = setup_resources(sess)
        setup_acl(sess, n_root)
