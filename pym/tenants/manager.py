import datetime
import sqlalchemy as sa
from pym.auth.models import User, Group, GroupMember
from pym.auth.manager import create_group, create_group_member
from pym.auth.const import SYSTEM_UID, GROUP_KIND_TENANT
from pym.res.models import ResourceNode
from pym.res.const import NODE_NAME_ROOT
from .models import Tenant


def create_tenant(sess, owner, name, cascade, **kwargs):
    """
    Creates a new tenant record.

    :param sess: A DB session instance.
    :param owner: ID, ``principal``, or instance of a user.
    :param name: Name.
    :param cascade: True to also create a group and resource for this tenant.
    :param kwargs: See :class:`~pym.auth.models.Tenant`.
    :return: Instance of created tenant.
    """
    ten = Tenant()
    ten.owner_id = User.find(sess, owner).id
    ten.name = name
    for k, v in kwargs.items():
        setattr(ten, k, v)
    sess.add(ten)
    sess.flush()  # need ID

    if cascade:
        # Create tenant's group
        create_group(sess, owner, name, kind=GROUP_KIND_TENANT,
            descr="All members of tenant " + name)
        n_root = ResourceNode.load_root(sess, name=NODE_NAME_ROOT)

        try:
            title = kwargs['title']
        except KeyError:
            title = name.title()
        n_root.add_child(sess=sess, owner=SYSTEM_UID, kind="res",
            name=name, title=title,
            iface='pym.tenants.models.ITenantNode')

    sess.flush()
    return ten


def update_tenant(sess, tenant, editor, **kwargs):
    """
    Updates a tenant.

    For details about ``**kwargs``, see :class:`~pym.auth.models.Tenant`.

    :param sess: A DB session instance.
    :param tenant: ID, ``name``, or instance of a tenant.
    :param editor: ID, ``principal``, or instance of a user.
    :return: Instance of updated tenant.
    """

    # TODO Rename tenant's resource
    # TODO Rename tenant's group

    ten = Tenant.find(sess, tenant)
    ten.editor_id = User.find(sess, editor).id
    ten.mtime = datetime.datetime.now()
    for k, v in kwargs.items():
        setattr(ten, k, v)
    sess.flush()
    return ten


def delete_tenant(sess, tenant, deleter, delete_from_db=False):
    """
    Deletes a tenant.

    :param sess: A DB session instance.
    :param tenant: ID, ``name``, or instance of a tenant.
    :param deleter: ID, ``principal``, or instance of a user.
    :param delete_from_db: Optional. Defaults to just tag as deleted (False),
        set True to physically delete record from DB.
    :return: None if really deleted, else instance of tagged tenant.
    """

    # TODO Delete tenant's resource
    # TODO Delete tenant's group

    ten = Tenant.find(sess, tenant)
    if delete_from_db:
        sess.delete(ten)
        ten = None
    else:
        ten.deleter_id = User.find(sess, deleter).id
        ten.dtime = datetime.datetime.now()
        # TODO Replace content of unique fields
    sess.flush()
    return ten


def collect_my_tenants(sess, user_id):
    """
    Returns list of tenants to which given user belongs.

    Each tenant has a global group with the same name. Membership in those
    groups determines whether a tenant is listed here or not.

    :param sess: Instance of a DB session.
    :param user_id: ID of user.
    :return: List of tenants.
    """
    tt = sess.query(
        Tenant
    ).join(
        Group, Group.name == Tenant.name
    ).join(
        GroupMember, GroupMember.group_id == Group.id
    ).filter(sa.and_(
        GroupMember.member_user_id == user_id,
        Group.kind == GROUP_KIND_TENANT,
        Group.tenant_id == None
    )).all()
    return tt


def add_user(sess, tenant, user, owner, **kwargs):
    """
    Adds a user to tenant's group.

    :param sess: A DB session instance.
    :param tenant: ID, ``name``, or instance of a tenant.
    :param user: ID, ``principal``, or instance of a user.
    :param owner: ID, ``principal``, or instance of a user.
    """
    ten = Tenant.find(sess, tenant)
    g_ten = sess.query(Group).filter(
        Group.name == ten.name,
        Group.kind == GROUP_KIND_TENANT
    ).one()
    create_group_member(sess, owner, g_ten, member_user=user, **kwargs)
    sess.flush()
