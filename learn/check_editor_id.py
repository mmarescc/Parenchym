#!/usr/bin/env python
import logging

import sqlalchemy as sa
import sqlalchemy.orm
import sqlalchemy.exc
import transaction
import zope.sqlalchemy
from sqlalchemy.ext.declarative import (
    declared_attr,
    declarative_base
)

logging.basicConfig(level=logging.INFO)
lgg = logging.getLogger(__name__)

#salgg = logging.getLogger('sqlalchemy.engine')
#salgg.setLevel(logging.INFO)

DbEngine = sa.create_engine("postgresql+psycopg2://test:test@localhost/test")
DbSession = sa.orm.scoped_session(
    sa.orm.sessionmaker(
        extension=zope.sqlalchemy.ZopeTransactionExtension()
    )
)
DbSession.configure(bind=DbEngine)
DbBase = declarative_base(bind=DbEngine)


# Rhoobarb
#
# def _validate_editor(context):
#     if not context.current_parameters['editor_id']:
#     #    raise ValueError('Editor must be set on update.')
#         lgg.error('**************** Editor must be set on update.')
#     # 'editor_id' is present in current_parameters, only having a value of None.
#     # If a field is omitted by SA, say because the value did not change, I
#     # would expect to not find that key in current_parameters. If that would be
#     # case for editor_id, I'd expect above code to raise a KeyError.
#     # Is that correct?


class DefaultMixin(object):
    """Mixin to add Parenchym's standard fields to a model class.

    These are: id, ctime, owner, mtime, editor.
    """

    id = sa.Column(sa.Integer(), primary_key=True, nullable=False)
    """Primary key of table."""

    ctime = sa.Column(sa.DateTime(), server_default=sa.func.current_timestamp(),
        nullable=False)
    """Timestamp, creation time."""

    # noinspection PyMethodParameters
    @declared_attr
    def owner_id(cls):
        """ID of user who created this record."""
        return sa.Column(
            sa.Integer(),
            sa.ForeignKey(
                "pym.user.id",
                onupdate="CASCADE",
                ondelete="RESTRICT"
            ),
            nullable=False
        )

    mtime = sa.Column(sa.DateTime(), onupdate=sa.func.current_timestamp(), nullable=True)
    """Timestamp, last edit time."""

    # noinspection PyMethodParameters
    @declared_attr
    def editor_id(cls):
        """ID of user who was last editor."""
        return sa.Column(
            sa.Integer(),
            sa.ForeignKey(
                "pym.user.id",
                onupdate="CASCADE",
                ondelete="RESTRICT"
            ),
            nullable=True,
            # Learned 20140317: Don't do this if you do not want to actively
            # set a value
            #onupdate=_validate_editor
        )


class User(DbBase, DefaultMixin):
    __tablename__ = "user"
    __table_args__ = (
        {'schema': 'pym'}
    )

    principal = sa.Column(sa.Unicode(255), nullable=False)


class Tenant(DbBase, DefaultMixin):
    """
    A tenant.
    """
    __tablename__ = "tenant"
    __table_args__ = (
        sa.UniqueConstraint('name', name='tenant_ux'),
        {'schema': 'pym'}
    )

    name = sa.Column(sa.Unicode(255), nullable=False)
    # Load description only if needed
    descr = sa.orm.deferred(sa.Column(sa.UnicodeText, nullable=True))
    """Optional description."""

    def __repr__(self):
        return "<{name}(id={id}, name='{n}'>".format(
            id=self.id, n=self.name, name=self.__class__.__name__)


@sa.event.listens_for(Tenant, 'before_update')
def receive_before_update(mapper, connection, target):
    lgg.info('Received a before_update for the mixin')
    lgg.info('Class name: {}'.format(target.__class__.__name__))
    will_result_in_update_sql = sa.orm.object_session(target).is_modified(
        target, include_collections=False)
    if will_result_in_update_sql:
        lgg.info('+++ SQL UPDATE')
    else:
        lgg.info('--- no update necessary')


def setup(sess):
    try:
        sess.execute("drop schema pym cascade")
        zope.sqlalchemy.mark_changed(sess)
        transaction.commit()
    except sa.exc.ProgrammingError:
        pass

    with transaction.manager:
        sess.execute("create schema pym")
        zope.sqlalchemy.mark_changed(sess)

    with transaction.manager:
        DbBase.metadata.create_all(DbEngine)
        u1 = User()
        u1.owner_id = 1
        u1.principal = 'salomon'
        u2 = User()
        u2.owner_id = 1
        u2.principal = 'sibylle'
        sess.add(u1)
        sess.add(u2)


def dance(sess):
    lgg.info('=' * 78)
    with transaction.manager:
        try:
            tn = sess.query(Tenant).filter(Tenant.name == 'foo').one()
        except sa.orm.exc.NoResultFound:
            tn = Tenant()
            tn.owner_id = 2
            tn.name = 'foo'
            tn.descr = 'o'
            sess.add(tn)
            cnt = 0
            lgg.info('Loop {} (added): {} {} {}'.format(cnt, tn.editor_id,
                tn.descr, tn.descr.count('o')))
        else:
            cnt = tn.descr.count('o')
            lgg.info('Loop {} (stored before change): {} {} {}'.format(cnt, tn.editor_id,
                tn.descr, tn.descr.count('o')))
            # XXX Have activated the onupdate=_validate_editor() check above to
            # XXX log an error.
            #
            # If cnt == 1 we just added that record, so editor_id must be None.
            # Later on, editor_id must be set.
            # if cnt > 1 and tn.editor_id is None:
            #     lgg.error("***************  AAAAAAGH ******************")
            #tn.descr += 'o'
            tn.editor_id = 2
        sess.flush()
        lgg.info('-' * 78)


def main():
    sess = DbSession()
    setup(sess)

    dance(sess)
    dance(sess)
    dance(sess)
    dance(sess)
    dance(sess)
    dance(sess)
    dance(sess)

if __name__ == '__main__':
    main()