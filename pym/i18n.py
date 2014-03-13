# -*- coding: utf-8 -*-
import functools
import babel
import icu

import pyramid.i18n


DOMAIN = None
"""Our Translation Domain.

MUST be set during application's initialisation, e.g. in ``includeme()``.
"""

_ = pyramid.i18n.TranslationStringFactory(DOMAIN) if DOMAIN else lambda s: s


def translate_choices(translate_func, choices):
    """
    Translates the text element of a choices list.

    A choices list is a list of 2-tuples, appropriate to be used for a
    select list in HTML; 1st element of the tuple is the value, 2nd element
    is the displayed text.

    And this 2nd element, i.e. the displayed text, we translate here.

    `translate_func` can be a partial (see `functools.partial`) initialised
    with domain and mapping. A translation function can be
    `pyramid.i18n.Localizer.translate()`, which can be obtained with
    `pyramid.i18n.get_localizer(request)`.

    :param translate_func: A function to translate the strings.
    :param choices: Typically list of 2-tuples with choices. May also be a dict.
        Then if the values are translation strings, they are translated.
    :return: List of translated 2-tuples.
    """
    if isinstance(choices[0], dict):
        ret = []
        for c in choices:
            c2 = c.copy()
            for k, v in c.items():
                if isinstance(v, pyramid.i18n.TranslationString):
                    c2[k] = translate_func(v)
            ret.append(c2)
        return ret
    else:
        return [(x[0], translate_func(x[1])) for x in choices]


def locale_negotiator(request):
    """Negotiates the locale setting.

    In config settings we have a list of available languages, key
    ``i18n.avail_languages``.
    First, we look if the current user has a preferred locale. If not, we use
    Pyramid's default locale negotiator,
    If the obtained locale is in our available language, we use this.
    The reason is that explicitly setting the locale takes precedence.
    Set '*' as ``avail_languages`` to allow all.

    If no locale was explicitly set, we let ``request.accept_language``,
    which is a WebOb object, find the best match from our available
    languages.
    """
    avail_languages = request.registry.settings['i18n.avail_languages']
    loc = request.user.preferred_locale
    if not loc:
        loc = pyramid.i18n.default_locale_negotiator(request)
    if loc:
        if '*' in avail_languages or loc in avail_languages:
            return loc
    # Some bots seem to transmit just '*' and WebOB then throws
    # an exception:
    #     Traceback (most recent call last):
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/gunicorn/workers/sync.py", line 126, in handle_request
    #     respiter = self.wsgi(environ, resp.start_response)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/paste/deploy/config.py", line 291, in __call__
    #     return self.app(environ, start_response)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/pyramid/router.py", line 251, in __call__
    #     response = self.invoke_subrequest(request, use_tweens=True)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/pyramid/router.py", line 227, in invoke_subrequest
    #     response = handle_request(request)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/pyramid/tweens.py", line 21, in excview_tween
    #     response = handler(request)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/pyramid_tm/__init__.py", line 82, in tm_tween
    #     reraise(*exc_info)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/pyramid_tm/compat.py", line 13, in reraise
    #     raise value
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/pyramid_tm/__init__.py", line 63, in tm_tween
    #     response = handler(request)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/pyramid/router.py", line 78, in handle_request
    #     has_listeners and notify(NewRequest(request))
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/pyramid/registry.py", line 74, in notify
    #     [ _ for _ in self.subscribers(events, None) ]
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/zope/interface/registry.py", line 323, in subscribers
    #     return self.adapters.subscribers(objects, provided)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/zope/interface/adapter.py", line 601, in subscribers
    #     subscription(*objects)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/pyramid/config/adapters.py", line 102, in derived_subscriber
    #     return subscriber(arg[0])
    #   File "/home/ceres/Pym/pym/subscribers.py", line 55, in add_localizer
    #     localizer = get_localizer(request)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/pyramid/i18n.py", line 209, in get_localizer
    #     current_locale_name = get_locale_name(request)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/pyramid/i18n.py", line 150, in get_locale_name
    #     locale_name = negotiate_locale_name(request)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/pyramid/i18n.py", line 137, in negotiate_locale_name
    #     locale_name = negotiator(request)
    #   File "/home/ceres/Pym/pym/i18n.py", line 40, in locale_negotiator
    #     return request.accept_language.best_match(avail_languages)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/webob/acceptparse.py", line 230, in best_match
    #     _check_offer(offer)
    #   File "/home/ceres/.virtualenvs/pym-py32-env/lib/python3.2/site-packages/webob/acceptparse.py", line 316, in _check_offer
    #     raise ValueError("The application should offer specific types, got %r" % offer)
    # ValueError: The application should offer specific types, got '*'
    try:
        return request.accept_language.best_match(avail_languages)
    except ValueError:
        return 'en'


def get_locale(request):
    loc = babel.Locale(pyramid.i18n.negotiate_locale_name(request))
    return loc


def get_lang_choices(request, with_default=False):
    choices = [(k, v) for k, v in request.locale.languages.items()]
    collator = icu.Collator.createInstance(
        icu.Locale(pyramid.i18n.negotiate_locale_name(request)))
    f = functools.cmp_to_key(collator.compare)
    choices.sort(key=lambda it: f(it[1]))
    if with_default:
        choices = [('*', _("DEFAULT"))] + choices
    return choices


def default_locale(request):
    if request.user.preferred_locale:
        return request.user.preferred_locale
    return request.locale


def fetch_translated(request, data):
    """
    Returns translation in requested language.

    :arg:`data` is a dict where each key is a language designator
    and its value is the translated string.

    The requested language is determined from user's preferred locale
    setting and the current request's language setting.

    :param request: Current request
    :param data: Dict with translated strings
    :return: Translated string
    """
    if not data:
        return ''
    wanted = [str(request.locale)]
    if request.user.preferred_locale:
        wanted.insert(0, str(request.user.preferred_locale))
    avail = list(data.keys())
    loc = babel.Locale.negotiate(wanted, avail)
    if loc:
        return data[str(loc)]
    else:
        try:
            return data['*']
        except KeyError:
            return None