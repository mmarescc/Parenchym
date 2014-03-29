import logging
from zope.interface import (
    Attribute,
    Interface,
    implementer
)
from pyramid.events import subscriber
import pyramid.i18n
import pym.i18n


_ = pyramid.i18n.TranslationStringFactory(pym.i18n.DOMAIN)


mlgg = logging.getLogger(__name__)

# ====================================================
#   Events
# ====================================================


class IUserAuthError(Interface):
    """
    Event emitted when an AuthError is raised.
    """
    request = Attribute('The request object')
    login = Attribute('The login which we tried to authenticate, e.g. principal or email')
    pwd = Attribute('The password')
    remote_addr = Attribute('The remote address')
    exc = Attribute('The exception object')


@implementer(IUserAuthError)
class UserAuthError(object):
    """
    An instance of this class is emitted as an :term:`event` when an AuthError
    is raised.

    The event instance has attributes ``request``, which is the current request
    object and, ``login``, which is the login we tried to authenticate, e.g.
    principal or email, ``pwd`` the password, ``remote_addr`` the remote
    address, and ``exc`` the exception object.

    This event class implements the :class:`IUserAuthError` interface.
    """
    def __init__(self, request, login, pwd, remote_addr, exc):
        self.request = request
        self.login = login
        self.pwd = pwd
        self.remote_addr = remote_addr
        self.exc = exc


class IBeforeUserLoggedIn(Interface):
    """
    Event emitted when we have found the user account, but before we actually
    log him in.
    """
    request = Attribute('The request object')
    user = Attribute('The user object')


@implementer(IBeforeUserLoggedIn)
class BeforeUserLoggedIn(object):
    """
    An instance of this class is emitted as an :term:`event` when we have
    found the user account, but before we actually log him in.

    The event instance has attributes ``request``, which is the current request
    object and, ``user``, which is a :class:`pym.authmgr.models.User` object.

    This event class implements the :class:`IUserLoggedIn` interface.
    """
    def __init__(self, request, user):
        self.request = request
        self.user = user


class IUserLoggedIn(Interface):
    """
    Event emitted whenever a user successfully logged in.
    """
    request = Attribute('The request object')
    user = Attribute('The user object')


@implementer(IUserLoggedIn)
class UserLoggedIn(object):
    """
    An instance of this class is emitted as an :term:`event` whenever a user
    successfully logged in.

    The event instance has attributes ``request``, which is the current request
    object and, ``user``, which is a :class:`pym.authmgr.models.User` object.

    This event class implements the :class:`IUserLoggedIn` interface.
    """
    def __init__(self, request, user):
        self.request = request
        self.user = user


class IUserLoggedOut(Interface):
    """
    Event emitted whenever a user logged out.
    """
    request = Attribute('The request object')
    user = Attribute('The user object')


@implementer(IUserLoggedOut)
class UserLoggedOut(object):
    """
    An instance of this class is emitted as an :term:`event` whenever a user
    logged out.

    The event instance has attributes ``request``, which is the current request
    object and, ``user``, which is a :class:`pym.authmgr.models.User` object.

    This event class implements the :class:`IUserLoggedIn` interface.
    """
    def __init__(self, request, user):
        self.request = request
        self.user = user


# ====================================================
#   Event Handler
# ====================================================


@subscriber(IUserAuthError)
def handle_user_auth_error(event):
    mlgg.warn("User Auth Error: {msg}: login='{l}' pwd='{p}' remote_addr='{a}'".format(
        msg=event.exc,
        l=event.login.replace("'", r"\'"), p=event.pwd.replace("'", r"\'"),
        a=event.remote_addr
    ))


# noinspection PyUnusedLocal
@subscriber(IBeforeUserLoggedIn)
def handle_before_user_logged_in(event):
    # TODO Log login action
    # TODO Check for active session from same IP
    #      --> Complain about not having logged out
    # TODO Check for active session from different IP
    #      --> Automatically kick other session
    pass


# noinspection PyUnusedLocal
@subscriber(IUserLoggedIn)
def handle_user_logged_in(event):
    pass


# noinspection PyUnusedLocal
@subscriber(IUserLoggedOut)
def handle_user_logged_out(event):
    pass
