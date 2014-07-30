import pyramid.util
import sqlalchemy as sa
import sqlalchemy.event
from sqlalchemy.orm import (relationship, backref)
from sqlalchemy.orm.collections import attribute_mapped_collection
from sqlalchemy.ext.hybrid import hybrid_property
import pyramid.security
#from pyramid.decorator import reify
import zope.interface

import pym.lib
import pym.exc
import pym.cache
import pym.auth.models as pam
from pym.models import (DbBase, DefaultMixin, DbSession)
from pym.models.types import CleanUnicode


class IRootNode(zope.interface.Interface):
    pass


class IHelpNode(zope.interface.Interface):
    pass


class ISystemNode(zope.interface.Interface):
    pass


# class RootNode(pym.lib.BaseNode):
#     __name__ = 'root'
#     __acl__ = [
#         (Allow, 'g:wheel', ALL_PERMISSIONS),
#     ]
#
#     def __init__(self, parent):
#         super().__init__(parent)
#         self._title = "Root"
#         self['help'] = HelpNode(self)
#         self['__sys__'] = ISystemNode(self)
#
#
# # ===[ HELP ]=======
#
#
# class HelpNode(pym.lib.BaseNode):
#     __name__ = 'help'
#
#     def __init__(self, parent):
#         super().__init__(parent)
#         self._title = "Help"
#
#     def __getitem__(self, item):
#         return KeyError()
#
#
# # ===[ SYSTEM ]======
#
#
# class SystemNode(pym.lib.BaseNode):
#     __name__ = '__sys__'
#
#     def __init__(self, parent):
#         super().__init__(parent)
#         self._title = "System"
#         self['auth'] = pam.AuthNode(self)
#
#
# root_node = RootNode(None)


def root_factory(request):
    #return root_node
    sess = DbSession()
    n = ResourceNode.load_root(sess, 'root')
    return n


# =========================


class ResourceNode(DbBase, DefaultMixin):
    __tablename__ = "resource_tree"
    # XXX Cannot use this unique constraint, because we might have child
    # XXX resources that have other unique requirements, e.g.
    # XXX dbfs.models.FileNode that discriminates by revision.
    #sa.UniqueConstraint('parent_id', 'name'),
    __table_args__ = (
        {'schema': 'pym'}
    )
    __mapper_args__ = {
        'polymorphic_on': 'kind',
        'polymorphic_identity': 'res'
    }

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
    _name = sa.Column('name', CleanUnicode(255), nullable=False)
    """
    Name of the resource.
    Will be used in traversal as ``__name__``. May be set even for root
    resources, roots are recognized by ``parent_id`` being None.
    """
    _title = sa.Column('title', CleanUnicode(255), nullable=True)
    """
    Title of the resource.

    Used as the title of a page.
    """
    _short_title = sa.Column('short_title', CleanUnicode(255), nullable=True)
    """
    Short title of the resource.

    Used in breadcrumbs and menus.
    """
    _slug = sa.Column('slug', CleanUnicode(255), nullable=True)
    """
    Slug of the resource.

    Used in URLs.
    """
    kind = sa.Column(CleanUnicode(255), nullable=False)
    """
    Kind of resource. Default is 'res'. Discriminates resources in polymorphic
    tables.
    """
    sortix = sa.Column(sa.Integer(), nullable=True, server_default='5000')
    """
    Sort index; if equal, sort by name.
    """
    iface = sa.Column(CleanUnicode(255), nullable=True)
    """
    Dotted Python name of the interface this node implements.

    Specifying the interface here is useful when you do not have a separate
    class for your resource. You may use the default class :class:`Res` and
    still be able to attach your views to an interface (view config
    ``context``).

    E.g. 'pym.res:IRes'
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
        backref=backref("parent", lazy="select", remote_side="ResourceNode.id"),

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

    acl = relationship(pam.Ace,
        order_by=[pam.Ace.allow, pam.Ace.sortix],
        # cascade deletions
        cascade="all, delete-orphan",
        # Let the DB cascade deletions to children
        passive_deletes=True,
        # Typically, a resource is loaded during traversal. We need its full ACL
        # then.
        lazy='select',
        ##lazy='joined',
        ##join_depth=1,
    )

    def __init__(self, owner_id, name, kind, **kwargs):
        self.owner_id = owner_id,
        self.name = name
        self.kind = kind
        for k, v in kwargs.items():
            setattr(self, k, v)

    def _set_ace(self, sess, owner, allow, permission, user=None, group=None,
            **kwargs):
        if not user and not group:
            raise pym.exc.PymError("Ace must reference either user or group.")
        if user and group:
            raise pym.exc.PymError("Ace cannot reference user and group "
                                   "simultaneously.")
        ace = pam.Ace()

        if isinstance(owner, int):
            ace.owner_id = owner
        elif isinstance(owner, str):
            o = sess.query(pam.User).filter(
                pam.User.principal == owner
            ).one()
            ace.owner_id = o.id
        else:
            ace.owner_id = owner.id

        if user:
            if isinstance(user, int):
                ace.user_id = user
            elif isinstance(user, str):
                u = sess.query(pam.User).filter(
                    pam.User.principal == user
                ).one()
                ace.user_id = u.id
            else:
                ace.user_id = user.id

        if group:
            if isinstance(group, int):
                ace.group_id = group
            elif isinstance(group, str):
                g = sess.query(pam.Group).filter(
                    pam.Group.name == group
                ).one()
                ace.group_id = g.id
            else:
                ace.group_id = group.id

        if permission:
            if isinstance(permission, int):
                ace.permission_id = permission
            elif isinstance(permission, str):
                p = sess.query(pam.Permission).filter(
                    pam.Permission.name == permission
                ).one()
                ace.permission_id = p.id
            elif isinstance(permission, pam.Permissions):
                p = sess.query(pam.Permission).filter(
                    pam.Permission.name == permission.value
                ).one()
                ace.permission_id = p.id
            else:
                ace.permission_id = permission.id

        ace.allow = allow

        for k, v in kwargs.items():
            setattr(ace, k, v)

        self.acl.append(ace)

    def allow(self, sess, owner, permission, user=None, group=None,
            **kwargs):
        """
        Allows a permission on this resource to user or group.

        Parameters ``owner``, ``permission``, ``user``, and ``group`` may be
        given as integer (ID), as string (principal or name), or as objects.

        Either ``user`` or ``group`` must be given, but not both.

        :param sess: A DB session.
        :param owner: Owner of this ACE.
        :param permission: Permission to set.
        :param user: Set permission for this user.
        :param group: Set permission for this group.
        :param kwargs: Other parameters suitable for :class:`pym.auth.models.Ace`.
        """
        self._set_ace(sess=sess, owner=owner, allow=True, permission=permission,
            user=user, group=group, **kwargs)

    def deny(self, sess, owner, permission, user=None, group=None,
            **kwargs):
        """
        Denies a permission on this resource from user or group.

        Parameters ``owner``, ``permission``, ``user``, and ``group`` may be
        given as integer (ID), as string (principal or name), or as objects.

        Either ``user`` or ``group`` must be given, but not both.

        :param sess: A DB session.
        :param owner: Owner of this ACE.
        :param permission: Permission to set.
        :param user: Set permission for this user.
        :param group: Set permission for this group.
        :param kwargs: Other parameters suitable for :class:`pym.auth.models.Ace`.
        """
        self._set_ace(sess=sess, owner=owner, allow=False, permission=permission,
            user=user, group=group, **kwargs)

    def add_child(self, sess, owner, kind, name, **kwargs):
        owner_id = pam.User.find(sess, owner).id
        n = ResourceNode(owner_id=owner_id, kind=kind, name=name, **kwargs)
        n.parent = self
        return n

    @classmethod
    def find(cls, sess, parent, **kwargs):
        """
        Finds a resource node with given attributes.

        :returns: Instance of node if it exists, False otherwise.
        """
        parent_id = parent if isinstance(parent, int) else parent.id
        try:
            return sess.query(cls).filter_by(parent_id=parent_id, **kwargs).one()
        except sa.orm.exc.NoResultFound:
            return False

    @classmethod
    def create_root(cls, sess, owner, name, kind, **kwargs):
        if isinstance(owner, int):
            owner_id = owner
        elif isinstance(owner, str):
            o = sess.query(pam.User).filter(
                pam.User.principal == owner
            ).one()
            owner_id = o.id
        else:
            owner_id = owner.id
        try:
            r = cls.load_root(sess, name, use_cache=False)
        except sa.orm.exc.NoResultFound:
            r = cls(owner_id, name, kind, **kwargs)
            sess.add(r)
        else:
            if r.kind == kind:
                return r
            else:
                raise ValueError("Root node '{}' already exists, but kind"
                    " differs: is='{}' wanted='{}'".format(
                    name, r.kind, kind))
        return r

    @classmethod
    def load_root(cls, sess, name='root', use_cache=True):
        """
        Loads root resource of resource tree.

        Since we allow several trees in the same table, argument ``name`` tells
        which one we want.

        :param sess: A DB session
        :param name: Name of the wanted root node
        :return: Instance of the root node or, None if not found
        """
        # CAVEAT: Setup fails if we use cache here!
        if use_cache:
            r = sess.query(
                cls
            ).options(
                pym.cache.FromCache("auth_long_term",
                cache_key='resource:{}:None'.format(name))
            ).options(
                pym.cache.RelationshipCache(cls.children, "auth_long_term",
                cache_key='resource:{}:None:children'.format(name))
            ).options(
                # CAVEAT: Program hangs if we use our own cache key here!
                pym.cache.RelationshipCache(cls.acl, "auth_long_term")  # ,
                #cache_key='resource:{}:None:acl'.format(name))
            ).filter(
                sa.and_(cls.parent_id == None, cls.name == name)
            ).one()
        else:
            r = sess.query(
                cls
            ).filter(
                sa.and_(cls.parent_id == None, cls.name == name)
            ).one()
        return r

    def is_root(self):
        return self.parent_id is None

    def dumps(self, _indent=0):
        return "   " * _indent \
            + repr(self) + "\n" \
            + "".join([c.dumps(_indent + 1) for c in self.children.values()])

    def __acl__(self):
        """
        ACL for Pyramid's authorization policy.
        """
        sess = sa.inspect(self).session
        # Bind ourselves to a new session in case we'd lost our session. This
        # may happen if the current request created an exception, which closes
        # the current session, and Pyramid redirects to an error page. That
        # error page again uses DB objects, but since the session had been
        # closed, it fails with a DetachedInstanceError, or and object's session
        # being None.
        if not sess:
            sess = DbSession()
            sess.add(self)
        acl = []
        perms = pam.Permission.load_all(sess)
        # Convert self.acl into Pyramid's ACL
        for ace in self.acl:
            pyr_ace = ace.to_pyramid_ace(perms)
            acl.append(pyr_ace)
            # If allow, allow all parents
            if ace.allow:
                if perms[ace.permission_id]['parents']:
                    for p in perms[ace.permission_id]['parents']:
                        pyr_ace2 = (pyr_ace[0], pyr_ace[1], p['name'])
                        acl.append(pyr_ace2)
            # If deny, deny all children
            else:
                for ch in perms[ace.permission_id]['children']:
                    pyr_ace2 = (pyr_ace[0], pyr_ace[1], ch['name'])
                    acl.append(pyr_ace2)
        return acl

    @classmethod
    def load_child(cls, sess, id_or_name, parent_id=None, use_cache=True):
        if isinstance(id_or_name, int):
            fil = [cls.id == id_or_name]
        else:
            fil = [
                cls.parent_id == parent_id,
                cls.name == id_or_name,
            ]
        if use_cache:
            return sess.query(
                cls
            ).options(
                pym.cache.FromCache("auth_long_term",
                    cache_key='resource:{}:{}'.format(
                        id_or_name, parent_id))
            ).options(
                pym.cache.RelationshipCache(cls.children, "auth_long_term",
                    cache_key='resource:{}:{}:children'.format(
                        id_or_name, parent_id))
            ).options(
                pym.cache.RelationshipCache(cls.acl, "auth_long_term",
                    cache_key='resource:{}:{}:acl'.format(
                        id_or_name, parent_id))
            ).options(
                pym.cache.RelationshipCache(cls.parent, "auth_long_term")#,
                    #cache_key='presource:{}:{}:parent'.format(
                    #    id_or_name, parent_id))
            ).filter(
                sa.and_(*fil)
            ).one()
        else:
            return sess.query(
                cls
            ).filter(
                sa.and_(*fil)
            ).one()

    def __getitem__(self, item):
        cls = self.__class__
        sess = sa.inspect(self).session
        try:
            child = cls.load_child(sess, item, self.id, use_cache=True)
        except sa.orm.exc.NoResultFound as exc:
            raise KeyError("Child resource not found: '{}'".format(item))
        return child

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
        if self.parent_id is None:
            return None
        return self.parent

    @hybrid_property
    def name(self):
        """
        Name of this node.
        """
        return self._name

    @name.setter
    def name(self, v):
        self._name = v

    @hybrid_property
    def title(self):
        """
        Title of this node.

        Uses ``name`` if not set.
        """
        return self._title if self._title else self.name

    @title.setter
    def title(self, v):
        self._title = v

    @hybrid_property
    def short_title(self):
        """
        Short title of this node.

        Uses ``title`` if not set.
        """
        return self._short_title if self._short_title else self.title

    @short_title.setter
    def short_title(self, v):
        self._short_title = v

    @hybrid_property
    def slug(self):
        """
        Slug of this node.

        Slugs are used in URLs.

        Uses ``name`` if not set.
        """
        return self._slug if self._slug else self.name

    @slug.setter
    def slug(self, v):
        self._slug = v

    @property
    def root(self):
        n = self
        while n.parent:
            n = n.parent
        return n

    @property
    def user(self):
        if self.parent_id is None:
            return self.__user__
        return self.root.__user__


# When we load a node from DB attach the stored interface to the instance.
# noinspection PyUnusedLocal
def resource_node_load_listener(target, context):
    if target.iface:
        iface = pyramid.util.DottedNameResolver(None).resolve(target.iface)
        zope.interface.alsoProvides(target, iface)

sa.event.listen(ResourceNode, 'load', resource_node_load_listener)
