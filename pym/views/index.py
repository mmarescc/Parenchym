import logging
from pyramid.security import (
    NO_PERMISSION_REQUIRED
)
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config
import sqlalchemy as sa
import sqlalchemy.orm.exc

import pym.models

import pym.resmgr.models
import pym.authmgr.models


# noinspection PyUnusedLocal
@view_config(
    name='',
    context=pym.resmgr.models.Root,
    renderer='pym:templates/index.mako',
    permission=NO_PERMISSION_REQUIRED
)
def index(context, request):
    if request.user.is_auth():
        return HTTPFound(location=request.resource_url(request.root, 'main'))
    return dict()


# noinspection PyUnusedLocal
@view_config(
    name='imprint',
    context=pym.resmgr.models.Root,
    renderer='pym:templates/imprint.mako',
    permission=NO_PERMISSION_REQUIRED
)
def imprint(context, request):
    return dict()


# noinspection PyUnusedLocal
@view_config(
    name='main',
    context=pym.resmgr.models.Root,
    renderer='pym:templates/main.mako',
    permission='view'
)
def main(context, request):
    # lgg = logging.getLogger('pym.test')
    # sess = pym.models.DbSession()
    # T = pym.authmgr.models.Tenant
    # try:
    #     tn = sess.query(T).filter(T.name == 'foo').one()
    #     request.session['cnt'] = tn.descr.count('o')
    # except sa.orm.exc.NoResultFound:
    #     tn = pym.authmgr.models.Tenant()
    #     tn.owner_id = request.user.uid
    #     tn.name = 'foo'
    #     tn.descr = 'o'
    #     sess.add(tn)
    #     lgg.debug('Added')
    #     request.session['cnt'] = 0
    # else:
    #     request.session['cnt'] += 1
    #     lgg.debug('{} {} {} {}'.format(request.session['cnt'], tn.editor_id,
    #         tn.descr, tn.descr.count('o')))
    #     tn.descr += 'o'
    #     tn.editor_id = request.user.uid
    return dict()
