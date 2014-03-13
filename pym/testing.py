import logging

import sqlalchemy as sa
import sqlalchemy.orm.exc

from pym.authmgr.const import UNIT_TESTER_UID, SYSTEM_UID
import pym.authmgr.models as pam


mlgg = logging.getLogger(__name__)


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
        p = sess.query(pam.Principal).filter(
            pam.Principal.id == UNIT_TESTER_UID
        ).one()
        lgg.debug('Principal ' + p.principal + ' loaded')
    except sa.orm.exc.NoResultFound:
        # noinspection PyArgumentList
        p = pam.Principal(owner=SYSTEM_UID, **pf)
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
