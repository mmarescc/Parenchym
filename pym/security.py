import os
import logging

import passlib.context
import pyramid.security
import pyramid.session
import pyramid.i18n
from pyramid.httpexceptions import HTTPForbidden, HTTPNotFound
from pyramid.view import forbidden_view_config, notfound_view_config
from pyramid.events import subscriber, NewRequest
import pym.i18n
import Crypto


_ = pyramid.i18n.TranslationStringFactory(pym.i18n.DOMAIN)


mlgg = logging.getLogger(__name__)


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
    request.response.status = 404
    return dict()


# ====================================================
#   Event Handler
# ====================================================


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
