from pyramid.security import (
    Allow, ALL_PERMISSIONS
)
#from pyramid.decorator import reify
import pym.lib
import pym.exc
import pym.authmgr.models


class Root(pym.lib.BaseNode):
    __acl__ = [
        (Allow, 'r:wheel', ALL_PERMISSIONS),
        (Allow, 'r:users', 'view'),
    ]

    def __init__(self, parent):
        super().__init__(parent)
        self._title = "Root"
        self['help'] = HelpNode(self)
        self['__sys__'] = SystemNode(self)


# ===[ HELP ]=======


class HelpNode(pym.lib.BaseNode):
    __name__ = 'help'

    def __init__(self, parent):
        super().__init__(parent)
        self._title = "Help"

    def __getitem__(self, item):
        return KeyError()


# ===[ SYSTEM ]======


class SystemNode(pym.lib.BaseNode):
    __name__ = '__sys__'

    def __init__(self, parent):
        super().__init__(parent)
        self._title = "System"
        self['authmgr'] = pym.authmgr.models.Node(self)


root = Root(None)


# noinspection PyUnusedLocal
def root_factory(request):
    return root
