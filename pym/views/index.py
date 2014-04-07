from pyramid.security import (
    NO_PERMISSION_REQUIRED
)
from pyramid.httpexceptions import HTTPFound
from pyramid.view import view_config

import pym.models

import pym.res.models
import pym.auth.models
import pym.tenants.manager


# noinspection PyUnusedLocal
@view_config(
    name='',
    context=pym.res.models.IRootNode,
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
    context=pym.res.models.IRootNode,
    renderer='pym:templates/imprint.mako',
    permission=NO_PERMISSION_REQUIRED
)
def imprint(context, request):
    return dict()


# noinspection PyUnusedLocal
@view_config(
    name='main',
    context=pym.res.models.IRootNode,
    renderer='pym:templates/main.mako',
    permission='visit'
)
def main(context, request):
    # Enum tenants to which current user belongs.
    # If only one, redirect to tenant home page,
    # if several, let him choose.
    sess = pym.models.DbSession()
    tt = pym.tenants.manager.collect_my_tenants(sess, request.user.uid)
    if len(tt) == 1:
        url = request.resource_url(context[tt[0].name])
        return HTTPFound(location=url)
    else:
        return dict(tenants=tt)
