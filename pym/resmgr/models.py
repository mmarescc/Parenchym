import pyramid.util
import sqlalchemy as sa
import sqlalchemy.event
from sqlalchemy.orm import (relationship, backref)
from sqlalchemy.orm.collections import attribute_mapped_collection

from pyramid.security import (
    Allow, ALL_PERMISSIONS
)
#from pyramid.decorator import reify
import zope.interface

import pym.lib
import pym.exc
import pym.authmgr.models
from pym.models import (
    DbBase, DefaultMixin
)


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


# =========================


class ResourceNode(DbBase, DefaultMixin):
    __tablename__ = "resource_tree"
    sa.UniqueConstraint('parent_id', 'name'),
    __table_args__ = (
        {'schema': 'pym'}
    )
    # __mapper_args__ = {
    #     'polymorphic_on': 'kind',
    #     'polymorphic_identity': 'resnode'
    # }

    # Root resource has parent_id NULL
    parent_id = sa.Column(
        sa.Integer(),
        sa.ForeignKey(
            'pym.resource_tree.id',
            onupdate='CASCADE',
            ondelete='CASCADE',
            name='resource_tree_parent_id_fk'
        ),
        nullable=True
    )
    name = sa.Column(sa.Unicode(255), nullable=False)
    """
    Name of the resource.
    Will be used in traversal as ``__name__``. May be set even for root
    resources, roots will be recognized when ``parent_id`` is None.
    """
    f_title = sa.Column(sa.Unicode(255), nullable=True)
    """
    Title of the resource.

    Will be the title of a page.
    """
    f_short_title = sa.Column(sa.Unicode(255), nullable=True)
    """
    Short title of the resource.

    Will be used in breadcrumbs and menus.
    """
    kind = sa.Column(sa.Unicode(255), nullable=False)
    """
    Kind of resource. Default is 'res'. Discriminates resources in polymorphic
    tables.
    """
    sortix = sa.Column(sa.Integer(), nullable=True, default=500)
    """
    Sort index; if equal, sort by name.
    """
    iface = sa.Column(sa.Unicode(255), nullable=True)
    """
    Dotted Python name of the interface this node implements.

    Specifying the interface here is useful when you do not have a separate
    class for your resource. You may use the default class :class:`Res` and
    still be able to attach your views to an interface (view config
    ``context``).

    E.g. 'pym.resmgr:IRes'
    """

    children = relationship("ResourceNode",
        order_by=lambda: [ResourceNode.sortix, ResourceNode.name],
        # cascade deletions
        cascade="all, delete-orphan",
        # Let the DB cascade deletions to children
        passive_deletes=True,
        # Typically, a resource is loaded during traversal. Maybe traversal
        # needs a specific child, but never the whole set. So load the children
        # individually.
        lazy='select',
        ##lazy='joined',
        ##join_depth=1,

        # many to one + adjacency list - remote_side
        # is required to reference the 'remote'
        # column in the join condition.
        backref=backref("parent", remote_side="ResourceNode.id"),

        # children will be represented as a dictionary
        # on the "name" attribute.
        collection_class=attribute_mapped_collection('name'),
    )
    """
    Children of this node.

    The parent node is inserted as well as a backref, and used in traversal
    as ``__parent__``.

    .. warning::

        Accessing this attribute will pull **all children** from the database
        **at once**, across all polymorphic tables. The result may be
        overwhelming!

        Use this attribute only if you *really* need a *complete* sorted list
        of all children.

        Don't even try ``len(res.children)`` to count them!
    """

    # TODO relationship to ACL

    def __init__(self, owner, name, kind, **kwargs):
        self.owner = owner,
        self.name = name
        self.kind = kind
        for k, v in kwargs.items():
            setattr(self, k, v)

    @classmethod
    def create_root(cls, sess, owner, name, kind, **kwargs):
        r = cls.load_root(sess, name)
        if r:
            if r.kind == kind:
                return r
            else:
                raise ValueError("Root node '{}' already exists, but kind"
                    " differs: is='{}' wanted='{}'".format(
                    name, r.kind, kind))
        r = cls(owner, name, kind, **kwargs)
        sess.add(r)
        return r

    @classmethod
    def load_root(cls, sess, name='root'):
        """
        Loads root resource of resource tree.

        Since we allow several trees in the same table, argument ``name`` tells
        which one we want.

        :param sess: A DB session
        :param name: Name of the wanted root node
        :return: Instance of the root node or, None if not found
        """
        try:
            r = sess.query(cls).filter(
                sa.and_(cls.parent_id == None, cls.name == name)
            ).one()
        except sa.orm.exc.NoResultFound:
            return None
        return r

    def dumps(self, _indent=0):
        return "   " * _indent \
            + repr(self) + "\n" \
            + "".join([c.dumps(_indent + 1) for c in self.children.values()])

    def __repr__(self):
        return "<{cls}(id={0}, parent_id='{1}', name='{2}', kind='{3}')>".format(
            self.id, self.parent_id, self.name, self.kind, cls=self.__class__.__name__)

    @property
    def __name__(self):
        """
        Used for traversal.
        """
        if self.parent_id is None:
            return None
        return self.name

    @property
    def __parent__(self):
        """
        Used for traversal.
        """
        return self.parent

    @property
    def __acl__(self):
        """
        Used for Pyramid's authorization policy.
        """
        acl = []
        # TODO Load ACL
        return acl

    @property
    def title(self):
        """
        Title of this node.

        Uses ``name`` if not set.
        """
        return self.f_title if self.f_title else self.name

    @property
    def short_title(self):
        """
        Short title of this node.

        Uses ``title`` if not set.
        """
        return self.f_short_title if self.f_short_title else self.title


# noinspection PyUnusedLocal
def resource_node_load_listener(target, context):
    if target.iface:
        iface = pyramid.util.DottedNameResolver(None).resolve(target.iface)
        zope.interface.alsoProvides(target, iface)

sa.event.listen(ResourceNode, 'load', resource_node_load_listener)
