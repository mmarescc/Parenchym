# -*- coding: utf-8 -*-

import datetime
from sqlalchemy.orm import object_session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql import and_

from pym.models import DbSession
from pym.authmgr.models import (Principal, Role, RoleMember)
import pym.security
from pym.exc import AuthError


PASSWORD_SCHEME = 'sha512_crypt'


_LOADED_PRINCIPALS = {}


def load_by_principal(principal):
    """
    Loads a principal instance by principal.
    """
    p = _LOADED_PRINCIPALS.get(principal, None)
    if p:
        if not object_session(p):
            p = None
    if not p:
        sess = DbSession()
        try:
            p = sess.query(Principal).filter(
                Principal.principal == principal).one()
        except NoResultFound:
            raise AuthError('Principal not found')
        _LOADED_PRINCIPALS[principal] = p
    return p


def _login(filter_, pwd):
    """
    Performs login.

    Called by the ``login_by...`` functions which initialise the filter.
    """
    # TODO Log login action
    # TODO Check for active session from same IP
    #      --> Complain about not having logged out
    # TODO Check for active session from different IP
    #      --> Automatically kick other session
    filter_.append(Principal.is_enabled == True)
    filter_.append(Principal.is_blocked == False)
    sess = DbSession()
    try:
        p = sess.query(Principal).filter(and_(*filter_)).one()
    except NoResultFound:
        raise AuthError('Principal not found')
    if not pym.security.pwd_context.verify(pwd, p.pwd):
        raise AuthError('Wrong credentials')
    p.login_time = datetime.datetime.now()
    p.login_ip = None
    p.logout_time = None
    sess.flush()
    return p


def _can_login(filter_, pwd):
    """
    Checks if a login would be successful.

    The checks are the same as for an actual login.

    Called by the ``can_login_by...`` functions which initialise the filter.
    """
    # TODO Log login action
    # TODO Check for active session from same IP
    #      --> Complain about not having logged out
    # TODO Check for active session from different IP
    #      --> Automatically kick other session
    filter_.append(Principal.is_enabled == True)
    filter_.append(Principal.is_blocked == False)
    sess = DbSession()
    try:
        p = sess.query(Principal).filter(and_(*filter_)).one()
    except NoResultFound:
        raise AuthError('Principal not found')
    if not pym.security.pwd_context.verify(pwd, p.pwd):
        raise AuthError('Wrong credentials')
    return p


def _check_credentials(*args):
    """
    Ensures that given credentials are not empty.

    This ensures that login fails with empty password or empty
    identity URL.
    """
    for a in args:
        if not a:
            raise AuthError('Wrong credentials')


def login_by_principal(principal, pwd):
    """
    Logs user in by principal and password, returns principal instance.

    Raises exception :class:`pym.exc.AuthError` if user is not found.
    """
    _check_credentials(principal, pwd)
    filter_ = [Principal.principal == principal]
    return _login(filter_, pwd)


def can_login_by_principal(principal, pwd):
    """
    Checks whether logging in by principal and password would be successful.
    """
    _check_credentials(principal, pwd)
    filter_ = [Principal.principal == principal]
    return _can_login(filter_, pwd)


def login_by_email(email, pwd):
    """
    Logs user in by email and password, returns principal instance.

    Raises exception :class:`pym.exc.AuthError` if user is not found.
    """
    _check_credentials(email, pwd)
    filter_ = [Principal.email == email]
    return _login(filter_, pwd)


def can_login_by_email(email, pwd):
    """
    Checks whether logging in by email and password would be successful.
    """
    _check_credentials(email, pwd)
    filter_ = [Principal.email == email]
    return _can_login(filter_, pwd)


def can_login(login, pwd):
    if '@' in login:
        return can_login_by_email(login, pwd)
    else:
        return can_login_by_principal(login, pwd)


def login_by_identity_url(identity_url):
    """
    Logs user in by identity URL (OpenID), returns principal instance.

    Raises exception :class:`pym.exc.AuthError` if user is not found.
    """
    raise NotImplementedError()


def logout(uid):
    """
    Performs logout.
    """
    # TODO Log logout action
    sess = DbSession()
    p = sess.query(Principal).filter(Principal.id == uid).one()
    p.login_ip = None
    p.login_time = None
    p.access_time = None
    p.logout_time = datetime.datetime.now()
    sess.flush()
    return p


def create_principal(data):
    """
    Creates a new principal record.

    Data fields:
    - ``owner``: Required
    - ``roles``: Optional list of role names. Role 'users' is always
                 automatically set.
                 If we provide a value for roles that evaluates to False,
                 this account is not member of any role.

    :param data: Dict with data fields
    :returns: Instance of created principal
    """
    # Determine roles this principal will be member of.
    # Always at least 'users'.
    if 'roles' in data:
        if data['roles']:
            roles = set(data['roles'] + ['users'])
        else:
            roles = set()
        del data['roles']
    else:
        roles = ['users']
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
    # Create principal
    p = Principal()
    for k, v in data.items():
        setattr(p, k, v)
    sess.add(p)
    sess.flush()  # to get ID of principal
    # Load/create the roles and memberships
    for name in roles:
        try:
            r = sess.query(Role).filter(Role.name == name).one()
        except NoResultFound:
            r = Role()
            r.name = name
            r.owner = data['owner']
            sess.add(r)
            sess.flush()
        rm = RoleMember()
        rm.principal_id = p.id
        rm.role_id = r.id
        rm.owner = p.owner
        sess.add(rm)
    sess.flush()
    return p


def update_principal(data):
    """
    Updates a principal.

    Data fields:
    ``id``:     Required. ID of principal to update
    ``editor``: Required
    ``mtime``:  Required

    :param data: Dict with data fields
    :returns: Instance of updated principal
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
    p = sess.query(Principal).filter(Principal.id == data['id']).one()
    for k, v in data.items():
        setattr(p, k, v)
    # If display_name is emptied, use principal
    if not p.display_name:
        p.display_name = p.principal
    sess.flush()
    return p


def delete_principal(id_):
    """
    Deletes a principal.

    :param id_: ID of principal to delete
    """
    sess = DbSession()
    p = sess.query(Principal).filter(Principal.id == id_).one()
    sess.delete(p)
    sess.flush()


def create_role(data):
    """
    Creates a new role record.

    Data fields:
    - ``owner``: Required
    :param data: Dict with data fields
    :returns: Instance of created role
    """
    sess = DbSession()
    r = Role()
    for k, v in data.items():
        setattr(r, k, v)
    sess.add(r)
    sess.flush()
    return r


def update_role(data):
    """
    Updates a role.

    Data fields:
    ``id``:     Required. ID of role to update
    ``editor``: Required
    ``mtime``:  Required

    :param data: Dict with data fields
    :returns: Instance of updated role
    """
    sess = DbSession()
    r = sess.query(Role).filter(Role.id == data['id']).one()
    for k, v in data.items():
        setattr(r, k, v)
    sess.flush()
    return r


def delete_role(id_):
    """
    Deletes a role.

    :param id_: ID of role to delete
    """
    sess = DbSession()
    r = sess.query(Role).filter(Role.id == id_).one()
    sess.delete(r)
    sess.flush()


def create_rolemember(data):
    """
    Creates a new rolemember record.

    Data fields:
    - ``owner``:        Required
    - ``principal_id``: Required
    - ``role_id``:      Required
    :param data: Dict with data fields
    :returns: Instance of created rolemember
    """
    sess = DbSession()
    rm = RoleMember()
    for k, v in data.items():
        setattr(rm, k, v)
    sess.add(rm)
    sess.flush()
    return rm


def delete_rolemember(id_):
    """
    Deletes a rolemember.

    :param id_: ID of rolemember to delete
    """
    sess = DbSession()
    rm = sess.query(RoleMember).filter(RoleMember.id == id_).one()
    sess.delete(rm)
    sess.flush()
