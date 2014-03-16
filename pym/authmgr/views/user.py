import copy
import colander
import sqlalchemy as sa
from pyramid.view import view_config, view_defaults
import datetime
from sqlalchemy.exc import StatementError
from sqlalchemy.orm.exc import NoResultFound

import pym.authmgr
from pym.authmgr.models import User, Group, GroupMember
import pym.authmgr.manager as manager
from pym.models import DbSession, todata
import pym.lib


@view_defaults(
    context=pym.authmgr.models.NodeUser,
    permission='manage_auth'
)
class UserView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(
        name='',
        renderer='pym:authmgr/templates/user/index.mako',
    )
    def index(self):
        return dict()
