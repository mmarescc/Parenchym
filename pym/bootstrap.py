import os
import sqlalchemy as sa
import sqlalchemy.orm.exc
#from zope.sqlalchemy import mark_changed
from pyramid.paster import (
    get_appsettings,
    setup_logging,
    bootstrap
)
from pyramid import testing
from pyramid.config import Configurator

from pym.authmgr.const import UNIT_TESTER_UID, SYSTEM_UID
from pym.rc import Rc
import pym.exc
import pym.models
import pym.authmgr.models as aam


class User(pym.security.User):

    def __init__(self, request):
        super().__init__(request)
        self._is_monitor = False

    def set_is_monitor(self, v):
        self._is_monitor = v

    @property
    def is_monitor(self):
        return self._is_monitor


class AppBaseClass(object):

    def __init__(self, L, with_db=False):
        self.L = L
        self.with_db = with_db
        self.DUMP_OPTS_JSON = dict(
            sort_keys=False,
            indent=4,
            ensure_ascii=False
        )
        self.DUMP_OPTS_YAML = dict(
            allow_unicode=True,
            default_flow_style=False
        )

        class Args(object):
            config = 'testing.ini'

        self._init_app(Args)

        self.REQUEST = testing.DummyRequest()
        self.REQUEST.registry = self.CONFIG.registry
        user = User(self.REQUEST)
        self.REQUEST.user = user

        if with_db:
            self.sess = pym.models.DbSession()
            self.create_unit_tester()

### mark_changed(sess)

    def _init_app(self, args):
        """
        Initialises Pyramid application.

        Loads config settings. Initialises SQLAlchemy.
        """
        self.ARGS = args
        setup_logging(self.ARGS.config)
        settings = get_appsettings(self.ARGS.config)

        if 'environment' not in settings:
            raise KeyError(
                'Missing key "environment" in config. Specify '
                'environment in paster INI file.'
            )
        # The directory of the config file is our root_dir
        rc = Rc(
            environment=settings['environment'],
            root_dir=os.path.normpath(
                os.path.join(os.getcwd(), os.path.dirname(
                    self.ARGS.config))
            )
        )
        rc.load()
        settings.update(rc.data)
        settings['rc'] = rc

        pym.models.init(settings, 'db.pym.sa.')

        self.RC = rc
        self.SETTINGS = settings

        self.CONFIG = Configurator(
            settings=settings
        )
        self.CONFIG.include(pym)

    def create_unit_tester(self):
        L = self.L
        sess = self.sess
        pf = {
            'id': UNIT_TESTER_UID,
            'principal': 'UNIT_TESTER',
            'is_enabled': False,
            'pwd': None,
            'pwd_expires': '1111-11-11',
            'email': 'unit_tester@localhost.localdomain',
            'notify_by': 'onscreen',
            'display_name': 'UNIT TESTER'
        }
        try:
            p = sess.query(aam.User).filter(
                aam.User.id == UNIT_TESTER_UID
            ).one()
            L.debug('Principal ' + p.principal + ' loaded')
        except sa.orm.exc.NoResultFound:
            p = aam.User(owner=SYSTEM_UID, **pf)
            sess.add(p)
            L.debug('Principal ' + p.principal + ' added')
        sess.flush()
        self.unit_tester = p
        self.REQUEST.user = pym.security.User(self.REQUEST)
        self.REQUEST.user.impersonate(self.unit_tester)
