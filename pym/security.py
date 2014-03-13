# coding: utf-8
import os

import babel
import passlib.context
import pyramid.security
from pyramid.httpexceptions import HTTPForbidden, HTTPNotFound
from pyramid.view import forbidden_view_config, notfound_view_config
import Crypto

from pym.authmgr.const import (NOBODY_UID, NOBODY_PRINCIPAL, NOBODY_EMAIL,
    NOBODY_DISPLAY_NAME)
import pym.authmgr.models
import pym.exc


_ = lambda s: s

DEBUG = False


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
        self._roles = None
        self._role_names = None
        self.uid = None
        self.principal = None
        self.init_nobody()
        self.auth_provider = AuthProviderFactory.factory(
            request.registry.settings['auth.provider'])

    def load_by_principal(self, principal):
        p = self.auth_provider.load_by_principal(principal)
        self.init_from_principal(p)

    def init_nobody(self):
        self.uid = NOBODY_UID
        self.principal = NOBODY_PRINCIPAL
        self._metadata = dict(
            email=NOBODY_EMAIL,
            display_name=NOBODY_DISPLAY_NAME
        )
        self.set_roles([])

    def init_from_principal(self, p):
        """
        Initialises authenticated user.
        """
        self.uid = p.id
        self.principal = p.principal
        self.set_roles(p.roles)
        self._metadata['email'] = p.email
        self._metadata['first_name'] = p.first_name
        self._metadata['last_name'] = p.last_name
        self._metadata['display_name'] = p.display_name

    def is_auth(self):
        """Tells whether user is authenticated, i.e. is not nobody
        """
        return self.uid != NOBODY_UID

    def is_wheel(self):
        for r in self.roles:
            if r.id == pym.authmgr.const.WHEEL_RID:
                return True
        return False

    def login(self, login, pwd):
        """
        Login by principal/email and password.

        Returns True on success, else False.
        """
        # Login methods throw AuthError exception. Caller should handle them.
        if '@' in login:
            p = self.auth_provider.login_by_email(email=login, pwd=pwd)
        else:
            p = self.auth_provider.login_by_principal(
                principal=login, pwd=pwd)
        self.init_from_principal(p)
        self._request.session.new_csrf_token()
        return True

    def impersonate(self, principal):
        if isinstance(principal, str):
            p = self.auth_provider.load_by_principal(principal)
        else:
            p = principal
        self.init_from_principal(p)
        roles = []  # TODO fetch roles of impersonated principal
        self.set_roles(roles)
        self._request.session.new_csrf_token()
        return p

    def logout(self):
        """
        Logout, resets metadata back to nobody.
        """
        self.auth_provider.logout(self.uid)
        self.init_nobody()
        self._request.session.new_csrf_token()

    def __getattr__(self, name):
        try:
            return self._metadata[name]
        except KeyError:
            raise AttributeError("Attribute '{0}' not found".format(name))

    @property
    def roles(self):
        return self._roles

    def set_roles(self, roles):
        roles.sort(key=lambda x: x.name)
        if DEBUG:
            print("Setting roles:", [str(x) for x in roles])
        self._roles = roles
        self._role_names = [r.name for r in roles]

    @property
    def role_names(self):
        return self._role_names

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
    # Not authenticated users have no roles
    if usr.uid == NOBODY_UID:
        return []
    # If we have no roles, we cannot have a location either
    if not usr.role_names:
        return []
    role_names = ['r:' + r for r in usr.role_names]
    return role_names


def get_user(request):
    principal = pyramid.security.unauthenticated_userid(request)
    usr = User(request)
    if principal is not None:
        usr.load_by_principal(principal)
    return usr


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


@forbidden_view_config(
    renderer='pym:templates/forbidden.mako',
)
def forbidden_view(request):
    return dict()


@notfound_view_config(xhr=True)
def xhr_notfound_view(request):
    """
    NotFound view for AJAX requests.
    """
    return HTTPNotFound()


@notfound_view_config(
    renderer='pym:templates/notfound.mako',
)
def notfound_view(request):
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
