import pyramid.testing

import pym.testing
import pym.models


def before_all(context):
    args = pym.testing.TestingArgs
    app = pym.testing.init_app(args, setup_logging=True)
    # This essentially sets properties:
    # settings, DbEngine, DbSession, DbBase
    for k, v in app.items():
        setattr(context, k, v)


# noinspection PyUnusedLocal
def before_scenario(context, scenario):
    context.configurator = pyramid.testing.setUp(
        request=pyramid.testing.DummyRequest(),
        settings=context.settings
    )
    context.sess = pym.models.DbSession()


# noinspection PyUnusedLocal
def after_scenario(context, scenario):
    pyramid.testing.tearDown()
    #context.sess.remove()