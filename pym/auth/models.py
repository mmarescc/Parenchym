import babel
import pyramid.security
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import INET, HSTORE
from sqlalchemy.orm import relationship
from sqlalchemy.ext.associationproxy import association_proxy
from pyramid.security import Allow
import pyramid.i18n

from pym.models import (
    DbBase, DefaultMixin
)
import pym.lib
import pym.exc

from .events import UserAuthError
from .const import (NOBODY_UID, NOBODY_PRINCIPAL, NOBODY_EMAIL,
    NOBODY_DISPLAY_NAME, WHEEL_RID)


_ = pyramid.i18n.TranslationStringFactory(pym.i18n.DOMAIN)


class Node(pym.lib.BaseNode):
    __name__ = 'auth'
    __acl__ = [
        (Allow, 'r:wheel', 'admin')
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self._title = 'AuthManager'
        self['user'] = NodeUser(self)
        self['tenant'] = NodeTenant(self)
        self['group'] = NodeGroup(self)
        self['group_member'] = NodeGroupMember(self)
        self['permission'] = NodePermission(self)


class NodeUser(pym.lib.BaseNode):
    __name__ = 'user'

    def __init__(self, parent):
        super().__init__(parent)
        self._title = 'Users'


class NodeTenant(pym.lib.BaseNode):
    __name__ = 'tenant'

    def __init__(self, parent):
        super().__init__(parent)
        self._title = 'Tenants'


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


class NodePermission(pym.lib.BaseNode):
    __name__ = 'permission'

    def __init__(self, parent):
        super().__init__(parent)
        self._title = 'Permissions'


class GroupMember(DbBase, DefaultMixin):
    """
    Group member.

    A group member is either a user or another group.
    """
    __tablename__ = "group_member"
    __table_args__ = (
        sa.UniqueConstraint('group_id', 'member_user_id',
            name='group_member_user_ux'),
        sa.UniqueConstraint('group_id', 'member_group_id',
            name='group_member_group_ux'),
        {'schema': 'pym'}
    )

    group_id = sa.Column(sa.Integer(),
        sa.ForeignKey("pym.group.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=False)
    """This group is the container."""
    member_user_id = sa.Column(sa.Integer(),
        sa.ForeignKey("pym.user.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=True)
    """This user is the member."""
    member_group_id = sa.Column(sa.Integer(),
        sa.ForeignKey("pym.group.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=True)
    """This group is the member."""
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True))
    """Optional description."""

    group = relationship('Group', foreign_keys=[group_id])
    member_user = relationship('User', foreign_keys=[member_user_id])
    member_group = relationship('Group', foreign_keys=[member_group_id])


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

    is_enabled = sa.Column(sa.Boolean, nullable=False, default=False,
        info={'colanderalchemy': {'title': _("Enabled?")}})
    """Tells whether or not a (human) admin has en/disabled this account."""
    disable_reason = sa.Column(sa.Unicode(255),
        info={'colanderalchemy': {'title': _("Disable Reason")}})
    """Reason why admin disabled this account."""
    is_blocked = sa.Column(sa.Boolean, nullable=False, default=False,
        info={'colanderalchemy': {'title': _("Blocked?")}})
    """Tells whether or not some automated process has en/disabled this
    account."""
    blocked_since = sa.Column(sa.DateTime,
        info={'colanderalchemy': {'title': _("Blocked Since")}})
    """Timestamp when block was established."""
    blocked_until = sa.Column(sa.DateTime,
        info={'colanderalchemy': {'title': _("Blocked Until")}})
    """Timestamp when block will automatically be released. NULL=never."""
    block_reason = sa.Column(sa.Unicode(255),
        info={'colanderalchemy': {'title': _("Block Reason")}})
    """Reason why block was established."""

    principal = sa.Column(sa.Unicode(255), nullable=False,
        info={'colanderalchemy': {'title': _("Principal")}})
    """Principal or user name."""
    pwd = sa.Column(sa.Unicode(255),
        info={'colanderalchemy': {'title': _("Password")}})
    """Password. NULL means blocked for login, e.g. for system accounts."""
    pwd_expires = sa.Column(sa.DateTime,
        info={'colanderalchemy': {'title': _("Pwd expires")}})
    """Timestamp when current pwd expires. NULL==never."""
    identity_url = sa.Column(sa.Unicode(255), index=True, unique=True,
        info={'colanderalchemy': {'title': _("Identity URL")}})
    """Used for login by OpenID."""
    email = sa.Column(sa.Unicode(128), nullable=False,
        info={'colanderalchemy': {'title': _("Email")}})
    """Email address. Always lower cased."""
    first_name = sa.Column(sa.Unicode(64),
        info={'colanderalchemy': {'title': _("First Name")}})
    """User's first name."""
    last_name = sa.Column(sa.Unicode(64),
        info={'colanderalchemy': {'title': _("Last Name")}})
    """User's last name."""
    display_name = sa.Column(sa.Unicode(255), nullable=False,
        info={'colanderalchemy': {'title': _("Display Name")}})
    """User is displayed like this. Usually 'first_name last_name' or
    'principal'."""

    login_time = sa.Column(sa.DateTime,
        info={'colanderalchemy': {'title': _("Login Time")}})
    """Timestamp of current login."""
    login_ip = sa.Column(sa.String(255),
        info={'colanderalchemy': {'title': _("Login IP")}})
    """IP address of logged in client."""
    access_time = sa.Column(sa.DateTime,
        info={'colanderalchemy': {'title': _("Access Time")}})
    """Timestamp when site was last accessed. Used to expire session."""
    kick_session = sa.Column(sa.Boolean, nullable=False, default=False,
        info={'colanderalchemy': {'title': _("Kick?")}})
    """Tells whether user's session is automatically terminated on next
    access."""
    kick_reason = sa.Column(sa.Unicode(255),
        info={'colanderalchemy': {'title': _("Kick Reason")}})
    """Display this message to kicked user."""
    logout_time = sa.Column(sa.DateTime,
        info={'colanderalchemy': {'title': _("Logout Time")}})
    """Timestamp of logout."""
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True,
        info={'colanderalchemy': {'title': _("Description")}})
    )
    """Optional description."""

    group_memberships = relationship('GroupMember',
        foreign_keys='GroupMember.member_user_id')
    """List of our direct group memberships. Call :meth:`all_group_memberships`
    to get all."""
    groups = association_proxy('group_memberships', 'group')
        #info={'colanderalchemy': {'title': _("Groups")}})
    """List of groups we are directly member of. Call :meth:`all_groups` to
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

    group_memberships = relationship('GroupMember',
        foreign_keys='GroupMember.group_id')
    """List of memberships in which we are the container."""
    member_groups = association_proxy('group_memberships', 'member_group')
    """List of groups that are our members."""
    member_users = association_proxy('group_memberships', 'member_user')
    """List of users that are our members."""

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


class CurrentUser(object):

    SESS_KEY = 'AuthMgr/CurrentUser'

    def __init__(self, request):
        self._request = request
        self._metadata = None
        self._groups = []
        self._group_names = []
        self.uid = None
        self.principal = None
        self.init_nobody()
        self.auth_provider = AuthProviderFactory.factory(
            request.registry.settings['auth.provider'])

    def load_by_principal(self, principal):
        u = self.auth_provider.load_by_principal(principal)
        self.init_from_user(u)

    def init_nobody(self):
        self.uid = NOBODY_UID
        self.principal = NOBODY_PRINCIPAL
        self._metadata = dict(
            email=NOBODY_EMAIL,
            display_name=NOBODY_DISPLAY_NAME
        )
        self.set_groups([])

    def init_from_user(self, u):
        """
        Initialises authenticated user.
        """
        self.uid = u.id
        self.principal = u.principal
        self.set_groups(u.groups)
        self._metadata['email'] = u.email
        self._metadata['first_name'] = u.first_name
        self._metadata['last_name'] = u.last_name
        self._metadata['display_name'] = u.display_name

    def is_auth(self):
        """Tells whether user is authenticated, i.e. is not nobody
        """
        return self.uid != NOBODY_UID

    def is_wheel(self):
        if not self._groups:
            return False
        for g in self._groups:
            if g.id == WHEEL_RID:
                return True
        return False

    def login(self, login, pwd, remote_addr):
        """
        Login by principal/email and password.

        Returns True on success, else False.
        """
        # Login methods throw AuthError exception. Caller should handle them.
        try:
            if '@' in login:
                p = self.auth_provider.login_by_email(request=self._request,
                    email=login, pwd=pwd, remote_addr=remote_addr)
            else:
                p = self.auth_provider.login_by_principal(request=self._request,
                    principal=login, pwd=pwd, remote_addr=remote_addr)
        except pym.exc.AuthError as exc:
            self._request.registry.notify(
                UserAuthError(self._request, login, pwd,
                    remote_addr, exc)
            )
            raise
        self.init_from_user(p)
        self._request.session.new_csrf_token()
        return True

    def impersonate(self, principal):
        """
        Loads a different user into current session.

        Keep in mind that all session data apart from the user data will not
        change.

        :param principal: Principal or instance of new user
        :return: Instance of new user
        """
        if isinstance(principal, str):
            u = self.auth_provider.load_by_principal(principal)
        else:
            u = principal
        self._request.session[self.__class__.SESS_KEY + '/prev_user'] = \
            self.principal
        self.init_from_user(u)
        self._request.session.new_csrf_token()
        return u

    def repersonate(self):
        """
        Loads previous user back into session.

        :return: Instance of new user (which is the previous one) or None if
            no previous user was set
        """
        try:
            principal = self._request.session[
                self.__class__.SESS_KEY + '/prev_user']
        except KeyError:
            return False
        u = self.auth_provider.load_by_principal(principal)
        self.init_from_user(u)
        self._request.session.new_csrf_token()
        return u

    def logout(self):
        """
        Logout, resets metadata back to nobody.
        """
        self.auth_provider.logout(self._request, self.uid)
        # Remove all session data
        self._request.session.invalidate()
        self.init_nobody()
        self._request.session.new_csrf_token()

    def __getattr__(self, name):
        try:
            return self._metadata[name]
        except KeyError:
            raise AttributeError("Attribute '{0}' not found".format(name))

    @property
    def groups(self):
        return self._groups

    def set_groups(self, groups):
        # mlgg.debug("Setting groups: {}".format([str(x) for x in groups]))
        # for x in traceback.extract_stack(limit=7):
        #     mlgg.debug("{}".format(x))
        self._groups = groups
        self._group_names = [g.name for g in groups]

    @property
    def group_names(self):
        return self._group_names

    @property
    def preferred_locale(self):
        loc = self._metadata.get('preferred_locale', None)
        if loc:
            return babel.Locale(loc)
        else:
            return None


class AuthProviderFactory(object):
    @staticmethod
    def factory(type_):
        if type_ == 'sqlalchemy':
            from . import manager
            return manager
        raise Exception("Unknown auth provider: '{0}'".format(type_))


def get_current_user(request):
    """
    This method is used as a request method to reify a user object
    to the request object as property ``user``.
    """
    #mlgg.debug("get user: {}".format(request.path))
    principal = pyramid.security.unauthenticated_userid(request)
    cusr = CurrentUser(request)
    if principal is not None:
        cusr.load_by_principal(principal)
    return cusr