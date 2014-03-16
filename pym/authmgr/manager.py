import datetime
import logging
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import and_

from pym.models import DbSession
from pym.authmgr.models import (User, Group, GroupMember)
from .const import SYSTEM_UID
import pym.security
from pym.exc import AuthError


PASSWORD_SCHEME = 'pbkdf2_sha512'


def load_by_principal(principal):
    """
    Loads a user instance by principal.
    """
    sess = DbSession()
    try:
        p = sess.query(User).filter(
            User.principal == principal).one()
    except NoResultFound:
        raise AuthError("User not found by principal '{}'".format(principal))
    return p


def _login(request, filter_, pwd, remote_addr):
    """
    Performs login.

    Called by the ``login_by...`` functions which initialise the filter.
    """
    filter_.append(User.is_enabled == True)
    filter_.append(User.is_blocked == False)
    sess = DbSession()
    try:
        u = sess.query(User).filter(and_(*filter_)).one()
    except NoResultFound:
        raise AuthError('User not found')
    # We have found the requested user, now broadcast this info so that
    # preparations can take place before we actually log him in.
    request.registry.notify(
        pym.security.BeforeUserLoggedIn(request, u)
    )
    # Now log user in
    if not pym.security.pwd_context.verify(pwd, u.pwd):
        raise AuthError('Wrong credentials')
    # And save some stats
    u.login_time = datetime.datetime.now()
    u.login_ip = remote_addr
    u.logout_time = None
    u.editor_id = SYSTEM_UID
    request.registry.notify(
        pym.security.UserLoggedIn(request, u)
    )
    return u


def logout(request, uid):
    """
    Performs logout.
    """
    sess = DbSession()
    u = sess.query(User).filter(User.id == uid).one()
    u.login_ip = None
    u.login_time = None
    u.access_time = None
    u.logout_time = datetime.datetime.now()
    u.editor_id = SYSTEM_UID
    request.registry.notify(
        pym.security.UserLoggedOut(request, u)
    )
    return u


def _check_credentials(*args):
    """
    Ensures that given credentials are not empty.

    This ensures that login fails with empty password or empty
    identity URL.
    """
    for a in args:
        if not a:
            raise AuthError('Missing credentials')


def login_by_principal(request, principal, pwd, remote_addr):
    """
    Logs user in by principal and password, returns principal instance.

    Raises exception :class:`pym.exc.AuthError` if user is not found.
    """
    _check_credentials(principal, pwd)
    filter_ = [User.principal == principal]
    return _login(request, filter_, pwd, remote_addr)


def login_by_email(request, email, pwd, remote_addr):
    """
    Logs user in by email and password, returns principal instance.

    Raises exception :class:`pym.exc.AuthError` if user is not found.
    """
    _check_credentials(email, pwd)
    filter_ = [User.email == email]
    return _login(request, filter_, pwd, remote_addr)


def login_by_identity_url(request, identity_url, remote_addr):
    """
    Logs user in by identity URL (OpenID), returns principal instance.

    Raises exception :class:`pym.exc.AuthError` if user is not found.
    """
    raise NotImplementedError()


def create_user(data):
    """
    Creates a new user record.

    Data fields:
    - ``owner_id``: Required
    - ``groups``:   Optional list of group names. group 'users' is always
                    automatically set.
                    If we provide a value for groups that evaluates to False,
                    this account is not member of any group.

    :param data: Dict with data fields
    :returns: Instance of created user
    """
    # Determine groups this user will be member of.
    # Always at least 'users'.
    if 'groups' in data:
        if data['groups']:
            groups = set(data['groups'] + ['users'])
        else:
            groups = set()
        del data['groups']
    else:
        groups = ['users']
    # Make sure the password is encrypted
    if 'pwd' in data:
        if not data['pwd'].startswith(('{', '$')):
            data['pwd'] = pym.security.pwd_context.encrypt(data['pwd'],
                PASSWORD_SCHEME)
    # If display_name is not explicitly set, use principal, thus
    # preserving its case (real principal will be stored lower case).
    if not 'display_name' in data:
        data['display_name'] = data['principal']
    # Allow only lowercase principals
    data['principal'] = data['principal'].lower()
    # Ditto email
    data['email'] = data['email'].lower()

    sess = DbSession()
    # Create user
    u = User()
    for k, v in data.items():
        setattr(u, k, v)
    sess.add(u)
    sess.flush()  # to get ID of user
    # Load/create the groups and memberships
    for name in groups:
        try:
            g = sess.query(Group).filter(
                and_(
                    Group.tenant_id == None,  # must be system group
                    Group.name == name
                )
            ).one()
        except NoResultFound:
            g = Group()
            g.name = name
            g.owner_id = data['owner_id']
            sess.add(g)
            sess.flush()
        gm = GroupMember()
        gm.user_id = u.id
        gm.group_id = g.id
        gm.owner_id = u.owner_id
        sess.add(gm)
    sess.flush()
    return u


def update_user(data):
    """
    Updates a user.

    Data fields:
    ``id``:     Required. ID of user to update
    ``editor_id``: Required
    ``mtime``:  Required

    :param data: Dict with data fields
    :returns: Instance of updated user
    """
    # Make sure the password is encrypted
    if 'pwd' in data:
        if not data['pwd'].startswith(('{', '$')):
            data['pwd'] = pym.security.pwd_context.encrypt(data['pwd'],
                PASSWORD_SCHEME)
    # Allow only lowercase principals
    if 'principal' in data:
        data['principal'] = data['principal'].lower()
    # Ditto email
    if 'email' in data:
        data['email'] = data['email'].lower()
    sess = DbSession()
    u = sess.query(User).filter(User.id == data['id']).one()
    for k, v in data.items():
        setattr(u, k, v)
    # If display_name is emptied, use principal
    if not u.display_name:
        u.display_name = u.principal
    sess.flush()
    return u


def delete_user(id_):
    """
    Deletes a user.

    :param id_: ID of user to delete
    """
    sess = DbSession()
    u = sess.query(User).filter(User.id == id_).one()
    sess.delete(u)
    sess.flush()


def create_group(data):
    """
    Creates a new group record.

    Data fields:
    - ``owner_id``: Required
    :param data: Dict with data fields
    :returns: Instance of created group
    """
    sess = DbSession()
    g = Group()
    for k, v in data.items():
        setattr(g, k, v)
    sess.add(g)
    sess.flush()
    return g


def update_group(data):
    """
    Updates a group.

    Data fields:
    ``id``:     Required. ID of group to update
    ``editor_id``: Required
    ``mtime``:  Required

    :param data: Dict with data fields
    :returns: Instance of updated group
    """
    sess = DbSession()
    g = sess.query(Group).filter(Group.id == data['id']).one()
    for k, v in data.items():
        setattr(g, k, v)
    sess.flush()
    return g


def delete_group(id_):
    """
    Deletes a group.

    :param id_: ID of group to delete
    """
    sess = DbSession()
    g = sess.query(Group).filter(Group.id == id_).one()
    sess.delete(g)
    sess.flush()


def create_group_member(data):
    """
    Creates a new group_member record.

    Data fields:
    - ``owner_id``:        Required
    - ``group_id``:      Required
    - ``user_id``: Required if ``other_group_id`` is not given
    - ``other_group_id``: Required if ``user_id`` is not given
    :param data: Dict with data fields
    :returns: Instance of created group_member
    """
    sess = DbSession()
    gm = GroupMember()
    for k, v in data.items():
        setattr(gm, k, v)
    sess.add(gm)
    sess.flush()
    return gm


def delete_group_member(id_):
    """
    Deletes a group_member.

    :param id_: ID of group_member to delete
    """
    sess = DbSession()
    gm = sess.query(GroupMember).filter(GroupMember.id == id_).one()
    sess.delete(gm)
    sess.flush()
