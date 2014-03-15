import logging
import os
import sqlalchemy as sa
import sqlalchemy.orm.exc
import pyramid.paster
import pyramid.config
from pym.authmgr.const import UNIT_TESTER_UID, SYSTEM_UID
import pym.authmgr.models as pam
from pym.rc import Rc
import pym
import pym.models


mlgg = logging.getLogger(__name__)


class TestingArgs(object):
    config = 'testing.ini'
    root_dir = '.'
    etc_dir = None


def init_app(args, setup_logging=True):
    """
    Inits Pyramid app for testing environment

    :param args: Class with args
    :return: Dict with ``DbEngine``, ``DbSession`` and ``DbBase``.
    """
    if setup_logging:
        pyramid.paster.setup_logging(args.config)
        settings = pyramid.paster.get_appsettings(args.config)
        if 'environment' not in settings:
            raise KeyError('Missing key "environment" in config. Specify '
                'environment in INI file "{}".'.format(args.config))
        if not args.etc_dir:
            args.etc_dir = os.path.join(args.root_dir, 'etc')
        rc = Rc(
            environment=settings['environment'],
            root_dir=args.root_dir,
            etc_dir=args.etc_dir
        )
        rc.load()
        settings.update(rc.data)
        settings['rc'] = rc
        result = {'settings': settings}
        pym.init_auth(rc)

        pym.models.init_unscoped(settings, 'db.pym.sa.')

        return result


def create_unit_tester(lgg, sess):
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
        p = sess.query(pam.User).filter(
            pam.User.id == UNIT_TESTER_UID
        ).one()
        lgg.debug('Principal ' + p.principal + ' loaded')
    except sa.orm.exc.NoResultFound:
        # noinspection PyArgumentList
        p = pam.User(owner=SYSTEM_UID, **pf)
        sess.add(p)
        lgg.debug('Principal ' + p.principal + ' added')
    sess.flush()
    return p


# noinspection PyUnusedLocal
class BaseMock(object):

    def __init__(self, *args, **kw):
        try:
            self.lgg = kw['lgg']
        except KeyError:
            self.lgg = None

    def __getattr__(self, item):
        def _method(*args, **kw):
            self.lgg.debug("Mock: {}.{}()".format(
                self.__class__.__name__,
                item
            ))
        return _method


class MockFileUploadStore(BaseMock):
    pass


class MockContext(BaseMock):
    pass
