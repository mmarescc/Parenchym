from pyramid.security import (
    NO_PERMISSION_REQUIRED,
    has_permission
)
from pyramid.httpexceptions import HTTPFound

from pyramid.view import view_config
import logging
import pym.models

import pym.resmgr.models


L = logging.getLogger('Pym')
_ = lambda s: s


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


@view_config(
    name='imprint',
    context=pym.resmgr.models.Root,
    renderer='pym:templates/imprint.mako',
    permission=NO_PERMISSION_REQUIRED
)
def imprint(context, request):
    return dict()


@view_config(
    name='js',
    context=pym.resmgr.models.Root,
    renderer='string',
    permission=NO_PERMISSION_REQUIRED
)
def js(context, request):
    # Just sit here and do nothing.
    # If we get called, it will be logged in subscribers on new request.
    return ''


@view_config(
    name='main',
    context=pym.resmgr.models.Root,
    renderer='pym:templates/main.mako',
    permission='view'
)
def main(context, request):
    return dict()
