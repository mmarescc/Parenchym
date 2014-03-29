# -*- coding: utf-8 -*-

from pyramid.view import view_config
import logging

import pym.res.models

L = logging.getLogger('Pym')


@view_config(
    name='',
    context=pym.res.models.SystemNode,
    renderer='pym:sys/templates/index.mako',
    permission='admin'
)
def index(context, request):
    return dict()


