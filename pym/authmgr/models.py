# -*- coding: utf-8 -*-
import sqlalchemy as sa
#from sqlalchemy import event
from sqlalchemy.dialects.postgresql import INET, HSTORE
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm import relationship
import colander
from pyramid.security import Allow

from pym.models import (
    DbBase, DefaultMixin, DefaultMixinDd,
)
from pym.dd import apply_mixin
import pym.lib


__all__ = ['Principal', 'Role', 'RoleMember']


class Node(pym.lib.BaseNode):
    __name__ = 'authmgr'
    __acl__ = [
        (Allow, 'r:wheel', 'admin')
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self._title = 'AuthManager'
        self['principal'] = NodePrincipal(self)
        self['role'] = NodeRole(self)
        self['rolemember'] = NodeRoleMember(self)


class NodePrincipal(pym.lib.BaseNode):
    __name__ = 'principal'

    def __init__(self, parent):
        super().__init__(parent)
        self._title = 'Principals'


class NodeRole(pym.lib.BaseNode):
    __name__ = 'role'

    def __init__(self, parent):
        super().__init__(parent)
        self._title = 'Roles'


class NodeRoleMember(pym.lib.BaseNode):
    __name__ = 'rolemember'

    def __init__(self, parent):
        super().__init__(parent)
        self._title = 'Rolemembers'


RoleMemberDd = {
    # This must be the same as ``__tablename__`` in a SQLAlchemy declarative.
    '__tablename__': 'rolemember',
    # This must be the same as ``__schema__`` in the table args of a
    # SQLAlchemy declarative.
    '__schema__': 'pym',

    'role_id': {
        'type': colander.Int(),
        'title': 'RoleId',
        'widget': None,
        'validator': colander.Length(min=1),
        'colModel': {
            'width': 50,
            'editable': True
        }
    },
    'principal_id': {
        'type': colander.Int(),
        'title': 'PrincipalId',
        'widget': None,
        'validator': colander.Length(min=1),
        'colModel': {
            'width': 50,
            'editable': True,
        }
    }
}
apply_mixin(RoleMemberDd, DefaultMixinDd)


class RoleMember(DbBase, DefaultMixin):
    __tablename__ = "rolemember"
    __table_args__ = (
        sa.UniqueConstraint('role_id', 'principal_id'),
        {
            'schema': 'pym'
        }
    )

    principal_id = sa.Column(sa.BigInteger,
        sa.ForeignKey("pym.principal.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=False)
    role_id = sa.Column(sa.BigInteger,
        sa.ForeignKey("pym.role.id",
            onupdate="CASCADE",
            ondelete="CASCADE"
        ),
        nullable=False)

    def __str__(self):
        return "<RoleMember(id={0}, role_id='{1}', principal_id='{2}'>".format(
            self.id, self.role_id, self.principal_id)


PrincipalDd = {
    # This must be the same as ``__tablename__`` in a SQLAlchemy declarative.
    '__tablename__': 'principal',
    # This must be the same as ``__schema__`` in the table args of a
    # SQLAlchemy declarative.
    '__schema__': 'pym',

    'is_enabled': {
        'type': colander.Bool(),
        'title': 'Enabled?',
        'widget': None,
        'colModel': {
            'width': 50,
            'editable': True,
            'edittype': 'checkbox',
            'editoptions': {'value': "true:false"},
            'formoptions': {'elmprefix': None},
        }
    },
    'disable_reason': {
        'type': colander.String(),
        'missing': colander.null,
        'title': 'Disable Reason',
        'widget': None,
        'validator': colander.Length(max=255),
        'colModel': {
            'width': 200,
            'editable': True,
        }
    },
    'is_blocked': {
        'type': colander.Bool(),
        'title': 'Blocked?',
        'widget': None,
        'colModel': {
            'width': 50,
            'editable': True,
            'edittype': 'checkbox',
            'editoptions': {'value': "true:false"},
            'formoptions': {'elmprefix': None},
        }
    },
    'blocked_since': {
        'type': colander.DateTime(),
        'missing': colander.null,
        'default': colander.null,
        'title': 'Blocked Since',
        'widget': None,
        'colModel': {
            'width': 100,
            'editable': False,
        }
    },
    'blocked_until': {
        'type': colander.DateTime(),
        'missing': colander.null,
        'default': colander.null,
        'title': 'Blocked Until',
        'widget': None,
        'colModel': {
            'width': 100,
            'editable': False,
        }
    },
    'block_reason': {
        'type': colander.String(),
        'missing': colander.null,
        'title': 'Block Reason',
        'widget': None,
        'validator': colander.Length(max=255),
        'colModel': {
            'width': 200,
            'editable': False,
        }
    },
    'principal': {
        'type': colander.String(),
        'title': 'Principal',
        'widget': None,
        'validator': colander.Length(min=1, max=255),
        'colModel': {
            'width': 150,
            'editable': True,
        }
    },
    'pwd': {
        'type': colander.String(),
        'missing': colander.null,
        'title': 'Password',
        'widget': None,
        'validator': colander.Length(max=255),
        'colModel': {
            'width': 100,
            'editable': True,
            'edittype': 'password',
            'editrules': {'edithidden': True},
            'hidden': True,
            'hidedlg': True,
        }
    },
    'pwd_expires': {
        'type': colander.DateTime(default_tzinfo=None),
        'title': 'Pwd Expires',
        'widget': None,
        'colModel': {
            'width': 100,
            'editable': True,
        }
    },
    'identity_url': {
        'type': colander.String(),
        'missing': colander.null,
        'title': 'Identity URL',
        'widget': None,
        'validator': colander.Length(max=255),
        'colModel': {
            'width': 100,
            'editable': False,
        }
    },
    'email': {
        'type': colander.String(),
        'title': 'Email',
        'widget': None,
        #        XXX  cannot deepcopy with validator Email   XXX
        #        , 'validator': colander.Email()
        'colModel': {
            'width': 200,
            'editable': True,
            #, 'editrules': { 'email': True }
        }
    },
    'first_name': {
        'type': colander.String(),
        'title': 'First Name',
        'widget': None,
        'validator': colander.Length(max=64),
        'colModel': {
            'width': 100,
            'editable': True,
        }
    },
    'last_name': {
        'type': colander.String(),
        'title': 'Last Name',
        'widget': None,
        'validator': colander.Length(max=64),
        'colModel': {
            'width': 100,
            'editable': True,
        }
    },
    'display_name': {
        'type': colander.String(),
        'title': 'Display Name',
        'widget': None,
        'validator': colander.Length(max=255),
        'colModel': {
            'width': 150,
            'editable': True,
        }
    },
    'notes': {
        'type': colander.String(),
        'missing': colander.null,
        'title': 'Notes',
        'widget': None,
        'validator': colander.Length(max=1024),
        'colModel': {
            'width': 150,
            'editable': True,
            'edittype': 'textarea',
        }
    },
    'login_time': {
        'type': colander.DateTime(),
        'missing': colander.null,
        'default': colander.null,
        'title': 'Login Time',
        'widget': None,
        'colModel': {
            'width': 100,
            'editable': False,
        }
    },
    'login_ip': {
        'type': colander.String(),
        'missing': colander.null,
        'title': 'Login IP',
        'widget': None,
        'validator': colander.Length(max=255),
        'colModel': {
            'width': 100,
            'editable': False,
        }
    },
    'access_time': {
        'type': colander.DateTime(),
        'missing': colander.null,
        'default': colander.null,
        'title': 'Access Time',
        'widget': None,
        'colModel': {
            'width': 100,
            'editable': False,
        }
    },
    'kick_session': {
        'type': colander.Bool(),
        'title': 'Kick?',
        'widget': None,
        'colModel': {
            'width': 50,
            'editable': True,
            'edittype': 'checkbox',
            'editoptions': {'value': "true:false"},
            'formoptions': {'elmprefix': None},
        }
    },
    'kick_reason': {
        'type': colander.String(),
        'missing': colander.null,
        'title': 'Kick Reason',
        'widget': None,
        'validator': colander.Length(max=255),
        'colModel': {
            'width': 200,
            'editable': True,
        }
    },
    'logout_time': {
        'type': colander.DateTime(),
        'missing': colander.null,
        'default': colander.null,
        'title': 'Logout Time',
        'widget': None,
        'colModel': {
            'width': 100,
            'editable': False,
        }
    },
    'gui_token': {
        'type': colander.String(),
        'missing': colander.null,
        'title': 'GUI Token',
        'widget': None,
        'validator': colander.Length(max=36),
        'colModel': {
            'width': 100,
            'editable': False,
        }
    }
}
apply_mixin(PrincipalDd, DefaultMixinDd)


class Principal(DbBase, DefaultMixin):
    """Principals (users).

    Principal must be unique. We store the string as-is, but treat it as
    lowercase: 'FOO' == 'foo' --> True.
    Since SQLAlchemy does not support PostgreSQL's functional indexes, we
    create such an index manually when the principal table is created.

    Emails are automatically lowercased. Emails must be unique.
    """
    __tablename__ = "principal"
    __table_args__ = (
        {
            'schema': 'pym'
        }
    )

    FIND_ONE_FIELD = 'principal'

    is_enabled = sa.Column(sa.Boolean, nullable=False, default=False)
    """Tells whether or not a (human) admin has en/disabled this account."""
    disable_reason = sa.Column(sa.Unicode(255))
    """Reason why admin disabled this account"""
    is_blocked = sa.Column(sa.Boolean, nullable=False, default=False)
    """Tells whether or not some automated process has en/disabled this
    account."""
    blocked_since = sa.Column(sa.DateTime)
    """Timestamp when block was established"""
    blocked_until = sa.Column(sa.DateTime)
    """Timestamp when block will automatically be released. NULL=never"""
    block_reason = sa.Column(sa.Unicode(255))
    """Reason why block was established"""

    principal = sa.Column(sa.Unicode(255), nullable=False, unique=True)
    """Principal or user name"""
    pwd = sa.Column(sa.Unicode(255))
    """Password"""
    pwd_expires = sa.Column(sa.DateTime)
    """Timestamp when current pwd expires. NULL==never"""
    identity_url = sa.Column(sa.Unicode(255), index=True, unique=True)
    """Used for login by OpenID"""
    email = sa.Column(sa.Unicode(128), nullable=False, unique=True)
    """Email address. Always lowecased."""
    first_name = sa.Column(sa.Unicode(64))
    """User's first name"""
    last_name = sa.Column(sa.Unicode(64))
    """User's last name"""
    display_name = sa.Column(sa.Unicode(255), nullable=False, unique=True)
    """User is displayed like this. Usually 'first_name last_name' or
    'principal'"""

    login_time = sa.Column(sa.DateTime)
    """Timestamp of current login"""
    login_ip = sa.Column(sa.String(255))
    """IP address of logged in client"""
    access_time = sa.Column(sa.DateTime)
    """Timestamp when site was last accessed. Used to expire session."""
    kick_session = sa.Column(sa.Boolean, nullable=False, default=False)
    """Tells whether user's session is automatically terminated on next
    access"""
    kick_reason = sa.Column(sa.Unicode(255))
    """Display kicked user this message"""
    logout_time = sa.Column(sa.DateTime)
    """Timestamp of logout"""
    gui_token = sa.Column(sa.String(36), index=True, unique=True)
    """Hmmm...?"""
    notes = sa.Column(sa.UnicodeText)
    """Well, some notes."""

    # XXX Too bad: we cannot simply do roles.append(new_role), because
    #     when SA saves the modified principal, it just sets values for
    #     principal_id and role_id, not owner which is required:
    #     IntegrityError: (IntegrityError) null value in column "owner"
    #         violates not-null constraint
    #             'INSERT INTO pym.rolemember (principal_id, role_id) VALUES
    #             (%(principal_id)s, %(role_id)s) RETURNING id'
    #             {'principal_id': 2L, 'role_id': 101L}
    roles = relationship('Role', secondary=RoleMember.__table__,
        primaryjoin='Principal.id==RoleMember.principal_id',
        backref="principals"
    )
    role_names = association_proxy('roles', 'name')

    def __str__(self):
        return "<Principal(id={0}, principal='{1}', email='{2}'>".format(
            self.id, self.principal, self.email)


RoleDd = {
    # This must be the same as ``__tablename__`` in a SQLAlchemy declarative.
    '__tablename__': 'role',
    # This must be the same as ``__schema__`` in the table args of a
    # SQLAlchemy declarative.
    '__schema__': 'pym',

    'name': {
        'type': colander.String(),
        'title': 'Rolename',
        'widget': None,
        'validator': colander.Length(min=1, max=255),
        'colModel': {
            'width': 150,
            'editable': True,
        }
    },
    'notes': {
        'type': colander.String(),
        'missing': colander.null,
        'title': 'Notes',
        'widget': None,
        'validator': colander.Length(max=255),
        'colModel': {
            'width': 150,
            'editable': True,
            'edittype': 'text',
        }
    }
}
apply_mixin(RoleDd, DefaultMixinDd)


class Role(DbBase, DefaultMixin):
    __tablename__ = "role"
    __table_args__ = (
        {
            'schema': 'pym'
        }
    )

    FIND_ONE_FIELD = 'id'

    name = sa.Column(sa.Unicode(255), nullable=False)
    notes = sa.Column(sa.Unicode(255))

    def __str__(self):
        return "<Role(id={0}, name='{1}'>".format(
            self.id, self.name)


def get_vw_principal_browse():
    return sa.Table('vw_principal_browse', Principal.metadata, autoload=True,
        schema='pym')


def get_vw_role_browse():
    return sa.Table('vw_role_browse', Role.metadata, autoload=True,
        schema='pym')


def get_vw_rolemember_browse():
    return sa.Table('vw_rolemember_browse', RoleMember.metadata, autoload=True,
        schema='pym')


class ActivityLog(DbBase):
    __tablename__ = "activity_log"
    __table_args__ = (
        {
            'schema': 'pym'
        }
    )

    FIND_ONE_FIELD = id

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
