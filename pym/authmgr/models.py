# -*- coding: utf-8 -*-
import sqlalchemy as sa
#from sqlalchemy import event
from sqlalchemy.dialects.postgresql import INET, HSTORE
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship
import colander
from pyramid.security import Allow

from pym.models import (
    DbBase, DefaultMixin
)
import pym.lib


__all__ = ['User', 'Group', 'GroupMember']


class Node(pym.lib.BaseNode):
    __name__ = 'authmgr'
    __acl__ = [
        (Allow, 'r:wheel', 'admin')
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self._title = 'AuthManager'
        self['principal'] = NodeUser(self)
        self['role'] = NodeGroup(self)
        self['rolemember'] = NodeGroupMember(self)


class NodeUser(pym.lib.BaseNode):
    __name__ = 'user'

    def __init__(self, parent):
        super().__init__(parent)
        self._title = 'Users'


class NodeGroup(pym.lib.BaseNode):
    __name__ = 'group'

    def __init__(self, parent):
        super().__init__(parent)
        self._title = 'Groups'


class NodeGroupMember(pym.lib.BaseNode):
    __name__ = 'group_member'

    def __init__(self, parent):
        super().__init__(parent)
        self._title = 'Group Members'

    def __repr__(self):
        return "<{name}(id={id}, group_id='{g}', user_id={u}, " \
               "other_group_id={o}>".format(
                   id=self.id, g=self.group_id, u=self.user_id,
                   o=self.other_group_id, name=self.__class__.__name__
               )


class GroupMember(DbBase, DefaultMixin):
    """
    Group member.

    A group member is either a user or another group.
    """
    __tablename__ = "group_member"
    __table_args__ = (
        sa.UniqueConstraint('group_id', 'user_id', 'other_group_id',
            name='group_member_ux'),
        {'schema': 'pym'}
    )

    group_id = sa.Column(sa.Integer(),
        sa.ForeignKey("pym.group.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=False)
    """We define a member of this group."""
    user_id = sa.Column(sa.Integer(),
        sa.ForeignKey("pym.user.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=True)
    """Member is this user."""
    other_group_id = sa.Column(sa.Integer(),
        sa.ForeignKey("pym.group.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=True)
    """Member is this group."""
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True))
    """Optional description."""


class User(DbBase, DefaultMixin):
    """
    A user account.

    Attribute ``principal`` is the login name which must be unique. We store the
    string as-is, but treat it as lowercase: 'FOO' == 'foo' --> True.

    We treat ``email`` and ``display_name`` the same.

    Each user has a ``display_name`` by which she is identified in the UI.
    Therefore this also must be unique. Be creative, if the default,
    ``first_name`` and ``last_name`` is not sufficient.

    Users are global to the system, i.e. a person has only one user account,
    regardless how many tenants he belongs to.
    """
    __tablename__ = "user"
    # The unique indexes are created below.
    __table_args__ = (
        {'schema': 'pym'}
    )

    is_enabled = sa.Column(sa.Boolean, nullable=False, default=False)
    """Tells whether or not a (human) admin has en/disabled this account."""
    disable_reason = sa.Column(sa.Unicode(255))
    """Reason why admin disabled this account."""
    is_blocked = sa.Column(sa.Boolean, nullable=False, default=False)
    """Tells whether or not some automated process has en/disabled this
    account."""
    blocked_since = sa.Column(sa.DateTime)
    """Timestamp when block was established."""
    blocked_until = sa.Column(sa.DateTime)
    """Timestamp when block will automatically be released. NULL=never."""
    block_reason = sa.Column(sa.Unicode(255))
    """Reason why block was established."""

    principal = sa.Column(sa.Unicode(255), nullable=False)
    """Principal or user name."""
    pwd = sa.Column(sa.Unicode(255))
    """Password. NULL means blocked for login, e.g. for system accounts."""
    pwd_expires = sa.Column(sa.DateTime)
    """Timestamp when current pwd expires. NULL==never."""
    identity_url = sa.Column(sa.Unicode(255), index=True, unique=True)
    """Used for login by OpenID."""
    email = sa.Column(sa.Unicode(128), nullable=False)
    """Email address. Always lower cased."""
    first_name = sa.Column(sa.Unicode(64))
    """User's first name."""
    last_name = sa.Column(sa.Unicode(64))
    """User's last name."""
    display_name = sa.Column(sa.Unicode(255), nullable=False)
    """User is displayed like this. Usually 'first_name last_name' or
    'principal'."""

    login_time = sa.Column(sa.DateTime)
    """Timestamp of current login."""
    login_ip = sa.Column(sa.String(255))
    """IP address of logged in client."""
    access_time = sa.Column(sa.DateTime)
    """Timestamp when site was last accessed. Used to expire session."""
    kick_session = sa.Column(sa.Boolean, nullable=False, default=False)
    """Tells whether user's session is automatically terminated on next
    access."""
    kick_reason = sa.Column(sa.Unicode(255))
    """Display this message to kicked user."""
    logout_time = sa.Column(sa.DateTime)
    """Timestamp of logout."""
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True))
    """Optional description."""

    groups = relationship('Group', secondary='pym.group_member',
        foreign_keys=[GroupMember.user_id, GroupMember.group_id])
    """List of groups we are directly member of. Call :meth:`group_tree` to
    get all."""

    def __repr__(self):
        return "<{name}(id={id}, principal='{p}', email='{e}'>".format(
            id=self.id, p=self.principal, e=self.email, name=self.__class__.__name__)


sa.Index("user_principal_ux", sa.func.lower(User.__table__.c.principal),
    unique=True)
sa.Index("user_email_ux", sa.func.lower(User.__table__.c.email),
    unique=True)
sa.Index("user_display_name_ux", sa.func.lower(User.__table__.c.display_name),
    unique=True)


class Tenant(DbBase, DefaultMixin):
    """
    A tenant.
    """
    __tablename__ = "tenant"
    __table_args__ = (
        sa.UniqueConstraint('name', name='tenant_ux'),
        {'schema': 'pym'}
    )

    name = sa.Column(sa.Unicode(255), nullable=False)
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True))
    """Optional description."""

    def __repr__(self):
        return "<{name}(id={id}, name='{n}'>".format(
            id=self.id, n=self.name, name=self.__class__.__name__)


class Group(DbBase, DefaultMixin):
    """
    A group.

    A group groups users or other groups. Groups may be global to the system,
    or belong to a specific tenant. In the former case, group's ``name`` must
    be globally unique, in the latter case only within that tenant.

    A group may only belong to one tenant.
    """
    __tablename__ = "group"
    __table_args__ = (
        sa.UniqueConstraint('tenant_id', 'name', name='group_ux'),
        {'schema': 'pym'}
    )

    tenant_id = sa.Column(sa.Integer(),
        sa.ForeignKey("pym.tenant.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=True
    )
    """Optional reference to the tenant to which this group belongs."""
    name = sa.Column(sa.Unicode(255), nullable=False)
    """Name of the group. Must be unique within a tenant."""
    kind = sa.Column(sa.Unicode(255), nullable=True)
    """An optional classifier to bundle groups together."""
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True))
    """Optional description."""

    def __repr__(self):
        return "<{name}(id={id}, tenant_id={t}, name='{n}'>".format(
            id=self.id, t=self.tenant_id, n=self.name,
            name=self.__class__.__name__)


class Permission(DbBase, DefaultMixin):
    """
    Permission.

    A permission has a ``code_name``, a string that is used in code e.g. as::

        @view_defaults(permission='manage_auth')

    Permissions may be hierarchical.

    If you grant a permission, automatically all of its parents are also
    granted. E.g. if ``read`` is a parent of ``write`` and you grant ``write``,
    ``read`` is also granted.

    If you deny a permission, automatically all of its children are also denied.
    E.g. if with above settings you deny ``read``, ``write`` is also denied.
    """
    __tablename__ = "permission_tree"
    __table_args__ = (
        sa.UniqueConstraint('code_name', name='permission_tree_ux'),
        {'schema': 'pym'}
    )
    # Topmost permission has parent_id NULL
    parent_id = sa.Column(sa.Integer(),
        sa.ForeignKey(
            'pym.permission_tree.id',
            onupdate='CASCADE',
            ondelete='CASCADE',
            name='permission_parent_fk'
        ),
        nullable=True
    )
    code_name = sa.Column(sa.Unicode(64), nullable=False)
    """The name of the permission as used in code."""
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True))
    """Optional description."""

    def __repr__(self):
        return "<{name}(id={id}, code_name='{cn}', parent_id='{p}'>".format(
            id=self.id, cn=self.code_name, p=self.parent_id, name=self.__class__.__name__)


class Ace(DbBase, DefaultMixin):
    """
    Access Control Entry.

    We define access control by granting or denying a group or a user a
    named permission on a resource.
    """
    __tablename__ = "resource_acl"
    __table_args__ = (
        sa.UniqueConstraint('resource_id', 'group_id', 'user_id',
            'permission_id', 'allow', name='resource_acl_ux'),
        {'schema': 'pym'}
    )

    resource_id = sa.Column(sa.Integer(),
        sa.ForeignKey("pym.resource_tree.id",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name='resource_acl_resource_fk'
        ),
        nullable=False
    )
    """Reference to a resource node."""
    group_id = sa.Column(sa.Integer(),
        sa.ForeignKey("pym.group.id",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name='resource_acl_group_fk'
        ),
        nullable=True
    )
    """Reference to a group. Mandatory if user is not set."""
    user_id = sa.Column(sa.Integer(),
        sa.ForeignKey("pym.user.id",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name='resource_acl_user_fk'
        ),
        nullable=True
    )
    """Reference to a user. Mandatory if group is not set."""
    sortix = sa.Column(sa.Integer(), nullable=True, default=500)
    """Sort index; if equal, sort by ID.

    .. note::

        Pyramid's authorization policy lets the first match win, so it is
        important to setup ``sortix`` properly!
    """
    permission_id = sa.Column(sa.Integer(),
        sa.ForeignKey("pym.permission_tree.id",
            onupdate="CASCADE",
            ondelete="CASCADE",
            name='resource_acl_permission_fk'
        ),
        nullable=False
    )
    """Reference to a permission."""
    allow = sa.Column(sa.Boolean(),
        nullable=False
    )
    """Allow if TRUE, deny if FALSE."""
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True))
    """Optional description."""

    def __repr__(self):
        return "<{name}(id={id}, resource_node_id={r}, group_id={g}," \
               " user_id={u}, sortix={ix}, permission_id={p}, allow={allow}>".format(
                   id=self.id, r=self.resource_node_id, p=self.permission_id,
                   g=self.group_id, u=self.user_id, allow=self.allow,
                   ix=self.sortix, name=self.__class__.__name__
               )


class ActivityLog(DbBase):
    __tablename__ = "activity_log"
    __table_args__ = (
        {'schema': 'pym'}
    )

    id = sa.Column(sa.Integer, primary_key=True)
    """Primary key of table."""
    ctime = sa.Column(sa.DateTime,
        server_default=sa.func.current_timestamp())
    """Timestamp, creation time."""
    principal = sa.Column(sa.Unicode(255))
    method = sa.Column(sa.Unicode(255))
    url = sa.Column(sa.Unicode(2048))
    client_addr = sa.Column(INET)
    remote_addr = sa.Column(INET)
    remote_user = sa.Column(sa.Unicode(255))
    header_authorization = sa.Column(sa.Unicode(255))
    headers = sa.Column(HSTORE)


def get_vw_user_browse():
    return sa.Table('vw_user_browse', User.metadata, autoload=True,
        schema='pym')


def get_vw_group_browse():
    return sa.Table('vw_group_browse', Group.metadata, autoload=True,
        schema='pym')


def get_vw_group_member_browse():
    return sa.Table('vw_group_member_browse', GroupMember.metadata, autoload=True,
        schema='pym')
