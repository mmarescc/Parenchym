# -*- coding: utf-8 -*-

from pyramid.view import view_config, view_defaults
from pyramid.httpexceptions import HTTPFound
from pyramid.security import (
    remember
    , forget
    , NO_PERMISSION_REQUIRED
)

import pym.authmgr.models
import pym.resmgr.models
import pym.lib
import pym.exc


_ = lambda s: s


@view_defaults(
    context=pym.authmgr.models.Node,
    permission='manage_auth'
)
class UsrMgrView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    @view_config(
        name='',
        renderer='pym:authmgr/templates/index.mako',
    )
    def index(self):
        return dict()


@view_defaults(
    context=pym.resmgr.models.Root,
    permission=NO_PERMISSION_REQUIRED
)
class LogInOutView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.login_url = request.resource_url(context, '@@login')
        referrer = request.params.get('referrer', None)
        if not referrer:
            referrer = request.session.get('login.referrer', None)
        if not referrer:
            referrer = request.url
            if referrer == self.login_url:
                # never use the login form itself as came_from
                referrer = request.resource_url(request.root)
        self.referrer = referrer
        request.session['login.referrer'] = referrer
        self.index_url = request.resource_url(request.root)

    @view_config(
        name='login',
        renderer='pym:authmgr/templates/login.mako',
        request_method='GET'
    )
    def login(self):
        return dict(
            referrer=self.referrer,
            url=self.login_url
        )

    @view_config(
        name='login',
        request_method='POST'
    )
    def login_post(self):
        try:
            login = self.request.POST['login']
            pwd = self.request.POST['pwd']
            self.request.user.login(login=login, pwd=pwd)
        except pym.exc.AuthError:
            msg = "Wrong credentials!"
            self.request.session.flash(dict(kind="error", text=msg))
            return HTTPFound(location=self.login_url)
        else:
            headers = remember(self.request, self.request.user.principal)
            self.request.session.flash(dict(
                kind="info",
                text='User {0} logged in'.format(
                    self.request.user.display_name
                )))
            #url = self.request.resource_url(self.request.root, 'main')
            #return HTTPFound(location=url, headers=headers)
            return HTTPFound(location=self.referrer, headers=headers)

    @view_config(
        name='logout',
    )
    def logout(self):
        name = self.request.user.display_name
        self.request.user.logout()
        headers = forget(self.request)
        self.request.session.flash(dict(
            kind="info",
            text='User {0} logged out'.format(name)))
        return HTTPFound(location=self.index_url, headers=headers)
