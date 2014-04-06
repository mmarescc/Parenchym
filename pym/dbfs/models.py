import sqlalchemy as sa
import sqlalchemy.orm
from sqlalchemy.dialects.postgresql import JSON, UUID
from zope.interface import implementer
from zope.interface import Interface
import pyramid.i18n
import pym.res.models


_ = pyramid.i18n.TranslationStringFactory(pym.i18n.DOMAIN)


class IFsNode(Interface):
    pass


@implementer(IFsNode)
class FsNode(pym.res.models.ResourceNode):
    __tablename__ = "fs_tree"
    sa.UniqueConstraint('parent_id', 'name', 'rev'),
    __table_args__ = (
        {'schema': 'pym'}
    )
    __mapper_args__ = {
        'polymorphic_identity': 'file'
    }

    MIME_TYPE_DIRECTORY = 'inode/directory'
    MIME_TYPE_JSON = 'application/json'

    id = sa.Column(sa.Integer(),
        sa.ForeignKey('pym.resource_tree.id'),
        primary_key=True, nullable=False)
    """Primary key of table."""
    tenant_id = sa.Column(sa.Integer(),
        sa.ForeignKey('pym.tenant.id'),
        nullable=False)
    """ID of owning tenant."""
    fs_root_id = sa.Column(sa.Integer(),
        sa.ForeignKey('pym.fs_tree.id'),
        nullable=False)
    """ID of root node for this FS."""
    uuid = sa.Column(UUID, nullable=False,
        server_default=sa.func.uuid_generate_v4())
    """
    UUID of this file. Used e.g. to identify file in cache. Each revision of the
    same file has its own UUID.
    """
    rev = sa.Column(sa.Integer(), nullable=False, default=1)
    """Revision."""
    mime_type = sa.Column(sa.Unicode(255), nullable=False)
    """
    Mime type.

    If it's a directory, use 'inode/directory', ``size``=0 and all content
    fields are empty.
    """

    # noinspection PyUnusedLocal
    @sa.orm.validates('mime_type')
    def validate_mime_type(self, key, mime_type):
        mime_type = mime_type.lower()
        assert '/' in mime_type
        return mime_type

    size = sa.Column(sa.Integer(),
        sa.CheckConstraint('size>=0'),
        nullable=False
    )
    """Size in bytes."""
    meta = sa.orm.deferred(
        sa.Column(JSON, nullable=True)
    )
    """Optional meta data."""
    content_json = sa.orm.deferred(
        sa.Column(JSON, nullable=True)
    )
    """Content as JSON."""
    content_text = sa.orm.deferred(
        sa.Column(sa.UnicodeText(), nullable=True)
    )
    """Content as CLOB."""
    content_bin = sa.orm.deferred(
        sa.Column(sa.LargeBinary(), nullable=True)
    )
    """Content as binary."""
    notes = sa.orm.deferred(
        sa.Column(sa.UnicodeText(), nullable=True)
    )
    """Notes."""

    def is_root(self):
        return self.id == self.fs_root_id

    def is_dir(self):
        return self.mime_type == self.MIME_TYPE_DIRECTORY

    def __repr__(self):
        return "<{cls}(id={0}, parent_id='{1}', name='{2}', kind='{3}')>".format(
            self.id, self.parent_id, self.name, self.kind, cls=self.__class__.__name__)
