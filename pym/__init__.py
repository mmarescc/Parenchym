import os.path
from pkg_resources import resource_filename
import json

from pyramid.config import Configurator
from pyramid_beaker import session_factory_from_settings
from pyramid.authentication import SessionAuthenticationPolicy
from pyramid.authorization import ACLAuthorizationPolicy
from pyramid.threadlocal import get_current_request
from pyramid.i18n import get_localizer, TranslationStringFactory
import deform
from pyramid_mailer import Mailer

from pym.rc import Rc
from pym.authmgr import manager as authmgr_manager
from . import security
from . import models
from . import i18n
from . import lib
from .resmgr.models import root_factory


def main(global_config, **settings):
    """ This function returns a Pyramid WSGI application.
    """
    # Init Rc
    # Get Rc instance like this, then use its methods e.g. g() or s():
    #     request.registry.settings['rc']
    # Rc data is merged directly into settings, so you can retrieve it like
    # this:
    #     request.registry.settings['project']
    # Set Rc's root_dir, which by default is the project dir (not the package
    # dir)
    #     ProjectDir
    #     +-- pym
    #     |   `-- rc.py
    #     `-- PackageDir
    if 'environment' not in settings:
        raise KeyError('Missing key "environment" in config. Specify '
            'environment in paster INI file.')
    rc = Rc(environment=settings['environment'],
        root_dir=os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..')
        )
    )
    rc.load()
    settings.update(rc.data)
    rc.s('environment', settings['environment'])
    # Put rc into config settings
    settings['rc'] = rc

    # Create config
    config = Configurator(
        settings=settings
    )
    config.include(includeme)

    return config.make_wsgi_app()


def includeme(config):

    # Override deform templates
    # Initialisation must take place from within dom-ready! Else
    # deform.js and/or jquery is not loaded, because we use requirejs
    def translator(term):
        return get_localizer(get_current_request()).translate(term)

    deform_templates = resource_filename('deform', 'templates')
    search_path = (resource_filename('pym', 'deform_templates'),
        deform_templates)
    deform.Form.set_zpt_renderer(search_path, translator=translator)

    # Init resource root
    config.set_root_factory(root_factory)

    # Init session
    session_factory = session_factory_from_settings(config.registry.settings)
    config.set_session_factory(session_factory)

    # Init Auth and Authz
    auth_pol = SessionAuthenticationPolicy(
        callback=security.group_finder
    )
    authz_pol = ACLAuthorizationPolicy()
    config.add_request_method(security.get_user, 'user', reify=True)
    config.set_authentication_policy(auth_pol)
    config.set_authorization_policy(authz_pol)
    config.set_default_permission('view')

    # i18n
    config.add_translation_dirs('pym:locale/')
    config.add_translation_dirs('deform:locale/')
    config.set_locale_negotiator(i18n.locale_negotiator)
    config.add_request_method(i18n.get_locale, 'locale', reify=True)
    # This sets the translation string factory and domain
    # for use in templates. See pym.subscribers.add_localizer().
    i18n.tsf = TranslationStringFactory('pym')

    # Mailer
    config.registry['mailer'] = Mailer.from_settings(config.registry.settings)

    # Init DB
    models.init(config.registry.settings, 'db.pym.sa.')

    # Run scan() which also imports db models
    config.scan('pym')

    # Static assets for this project
    config.add_static_view('static-pym', 'pym:static')
    config.add_static_view('static-deform', 'deform:static')

    init_auth(config.registry.settings['rc'])


def init_auth(rc):
    authmgr_manager.PASSWORD_SCHEME = rc.g('auth.password_scheme',
        authmgr_manager.PASSWORD_SCHEME).lower()
