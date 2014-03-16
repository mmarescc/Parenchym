import os
import logging
import babel
import passlib.context
import pyramid.security
import pyramid.session
import pyramid.i18n
from pyramid.events import subscriber, NewRequest
from pyramid.httpexceptions import HTTPForbidden, HTTPNotFound
from pyramid.view import forbidden_view_config, notfound_view_config
import Crypto
from zope.interface import (
    Attribute,
    Interface,
    implementer
)

from pym.authmgr.const import (NOBODY_UID, NOBODY_PRINCIPAL, NOBODY_EMAIL,
    NOBODY_DISPLAY_NAME)
import pym.authmgr.models
import pym.exc
import pym.events


_ = pyramid.i18n.TranslationStringFactory('Parenchym')


mlgg = logging.getLogger(__name__)


class AuthProviderFactory(object):
    @staticmethod
    def factory(type_):
        if type_ == 'sqlalchemy':
            import pym.authmgr.manager
            return pym.authmgr.manager
        raise Exception("Unknown auth provider: '{0}'".format(type_))


class User(object):

    SESS_KEY = 'AuthMgr/User'

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
            if g.id == pym.authmgr.const.WHEEL_RID:
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


def group_finder(userid, request):
    """
    Returns role_names of the currently logged in user.

    Role names are prefixed with 'r:'.
    Nobody has no role_names.
    Param 'userid' must match principal of current user, else throws error
    """
    usr = request.user
    # unauthenticated_userid becomes authenticated_userid if groupfinder
    # returns not None.
    if userid != usr.principal:
        # This should not happen (tm)
        raise Exception("Userid '{0}' does not match current "
            "user.principal '{1}'".format(
                userid, usr.principal))
    # Not authenticated users have no groups
    if usr.uid == NOBODY_UID:
        return []
    if not usr.group_names:
        return []
    group_names = ['g:' + g for g in usr.group_names]
    return group_names


def get_user(request):
    """
    This method is used as a request method to reify a user object
    to the request object as property ``user``.
    """
    #mlgg.debug("get user: {}".format(request.path))
    principal = pyramid.security.unauthenticated_userid(request)
    usr = User(request)
    if principal is not None:
        usr.load_by_principal(principal)
    return usr


class Encryptor(object):

    def __init__(self, secret):
        self._secret = secret.encode('utf-8')
        if not len(self._secret) in (16, 24, 32):
            self._secret += (32 - len(self._secret)) * b'}'

    def encrypt(self, plaintext):
        if plaintext is None or plaintext == '':
            return plaintext
        iv = os.urandom(16)
        encobj = self.create_enc_object(iv, self._secret)
        ciphertext = iv
        ciphertext += encobj.encrypt(plaintext)
        return ciphertext

    def decrypt(self, ciphertext):
        if ciphertext is None or ciphertext == '':
            return ciphertext
        iv = ciphertext[:16]
        encobj = self.create_enc_object(iv, self._secret)
        plaintext = encobj.decrypt(ciphertext[16:])
        return plaintext.decode('utf-8')

    @classmethod
    def create_enc_object(cls, iv, secret):
        return Crypto.Cipher.AES.new(
            secret,
            Crypto.Cipher.AES.MODE_CFB,
            iv
        )


# ====================================================
#   Views
# ====================================================


# noinspection PyUnusedLocal
@forbidden_view_config(xhr=True)
def xhr_forbidden_view(request):
    """
    Forbidden view for AJAX requests.

    To properly signal clients the forbidden status, we must not redirect to
    a login view. (1) AJAX clients cannot login by such a view, (2) AJAX client
    may expect a JSON response, and the client JavaScript will crash if it
    gets some HTML.
    """
    return HTTPForbidden()


# noinspection PyUnusedLocal
@forbidden_view_config(
    renderer='pym:templates/forbidden.mako',
)
def forbidden_view(request):
    return dict()


# noinspection PyUnusedLocal
@notfound_view_config(xhr=True)
def xhr_not_found_view(request):
    """
    NotFound view for AJAX requests.
    """
    return HTTPNotFound()


# noinspection PyUnusedLocal
@notfound_view_config(
    renderer='pym:templates/not_found.mako',
)
def not_found_view(request):
    return dict()


pwd_context = passlib.context.CryptContext(
    schemes=[
        'pbkdf2_sha512',
        'sha512_crypt',
        # LDAP schemes are for Dovecot
        'ldap_salted_sha1',
        # Set plaintext last, otherwise passlib does not identify a hash
        # correctly
        'ldap_plaintext'
    ],
    default='pbkdf2_sha512'
)


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


@subscriber(NewRequest)
def validate_csrf_token(event):
    """Validates CSRF token for XHR (AJAX) and POST requests.

    POST requests must send the token in (hidden) field ``csrf_token``.

    XHR requests must send the token as HTML header ``X-CSRF-Token``.
    On the client side, application PYM initialises jQuery ajax calls to
    automatically send this header.

    The benefit is that a CSRF token is sent also from 3rd-party widgets
    that do not allow to modify the sent data.
    """
    request = event.request
    if request.is_xhr or request.method.upper() in ('POST', 'PUT', 'DELETE'):
        pyramid.session.check_csrf_token(request)
