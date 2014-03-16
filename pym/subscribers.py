import logging
import babel.support
import babel
import icu
import pyramid

from pyramid.events import (subscriber, BeforeRender, NewRequest, ContextFound)
import pyramid.location
import pyramid.session
from pyramid.i18n import get_localizer

import pym.models
import pym.authmgr.models
import pym.events


_ = pyramid.i18n.TranslationStringFactory('Parenchym')
mlgg = logging.getLogger(__name__)

DEBUG = False


if DEBUG:
    @subscriber(ContextFound)
    def debug_context_found(event):
        rq = event.request
        # if rq.path.startswith('/static-'):
        #     return
        ctx = rq.context
        mlgg.debug('---[ CONTEXT: {}, {}'.format(rq.path, str(ctx)))

    @subscriber(NewRequest)
    def debug_new_request(event):
        rq = event.request
        # if rq.path.startswith('/static-'):
        #     return
        mlgg.debug('===[ REQUEST: {}'.format(rq.path))
        #mlgg.debug(str(rq))


@subscriber(BeforeRender)
def add_renderer_globals(event):
    """
    Make globals available in all renderers.

    - ``h`` contains module :mod:`pym.renderer_globals`
    - REMOVED ``_`` is the shortcut for translate method
    - ``bfmt`` is an instance of :mod:`babel.support.Format`, initialised
      with current locale. It contains convenience functions like
      ``format_number()`` etc.
    - ``babel`` contains complete module :mod:`babel`
    """
    import pym.renderer_globals
    event['h'] = pym.renderer_globals
    request = event['request']
    event['bfmt'] = babel.support.Format(request.locale_name)
    event['babel'] = babel
    event['icu'] = icu


# @subscriber(NewRequest)
# def log_activity(event):
#     r = event.request
#     if not 'static-' in r.url:
#         a = pym.authmgr.models.ActivityLog()
#         a.principal = r.user.principal
#         a.method = r.method
#         a.url = r.url
#         a.client_addr = r.client_addr
#         a.remote_addr = r.remote_addr
#         a.remote_user = r.remote_user
#         a.header_authorization = r.authorization
#         a.headers = dict(r.headers)
#         sess = pym.models.DbSession()
#         sess.add(a)
#         sess.flush()
