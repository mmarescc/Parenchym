# Interesting reads:
# http://stackoverflow.com/questions/270879/efficiently-updating-database-using-sqlalchemy-orm/278606#278606
# http://stackoverflow.com/questions/9593610/creating-a-temporary-table-from-a-query-using-sqlalchemy-orm
# http://stackoverflow.com/questions/9766940/how-to-create-an-sql-view-with-sqlalchemy
# Materialized view:
# http://stackoverflow.com/questions/11114903/oracle-functional-index-creation

import sqlalchemy as sa
from sqlalchemy import (
    engine_from_config,
    Column,
    Integer,
    DateTime,
    ForeignKey,
    event,
    util
)
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    ColumnProperty,
    class_mapper
)
import sqlalchemy.orm.query
from sqlalchemy.orm.collections import InstrumentedList
from sqlalchemy.ext.declarative import (
    declared_attr,
    declarative_base
)
from sqlalchemy.sql.expression import (func)
import sqlalchemy.engine

from zope.sqlalchemy import ZopeTransactionExtension

import colander
import deform
import deform.widget
import pyramid.i18n
import pym.exc
import pym.lib
import pym.i18n


_ = pyramid.i18n.TranslationStringFactory(pym.i18n.DOMAIN)


# ===[ SCHEMA HELPERS ]=======

# noinspection PyUnusedLocal
@colander.deferred
def deferred_csrf_token_default(node, kw):
    request = kw.get('request')
    csrf_token = request.session.get_csrf_token()
    return csrf_token


CSRF_SCHEMA_NODE = colander.SchemaNode(
    colander.String(),
    default=deferred_csrf_token_default,
    # Don't need a validator. We have a subscriber checking this token.
    widget=deform.widget.HiddenWidget(),
)
"""
Colander schema node for a hidden field containing a CSRF token.

Usage::

    class LoginSchema(colander.MappingSchema):
        login = colander.SchemaNode(colander.String())
        pwd   = colander.SchemaNode(colander.String(),
                    widget=deform.widget.PasswordWidget()
                )
        csrf_token = CSRF_SCHEMA_NODE

When you create a schema instance, do not forget to bind the current
request like so::

    sch = LoginSchema().bind(request=self.request)
"""


class LoginSchema(colander.MappingSchema):
    """
    Schema for basic login form with CSRF token.
    """
    login = colander.SchemaNode(colander.String())
    pwd = colander.SchemaNode(colander.String(),
        widget=deform.widget.PasswordWidget()
    )
    csrf_token = CSRF_SCHEMA_NODE


# ===[ DB HELPERS ]=======

DbSession = scoped_session(sessionmaker(extension=ZopeTransactionExtension()))
"""
Factory for DB session.
"""
DbBase = declarative_base()
"""
Our base class for declarative models.
"""
DbEngine = None
"""
Default DB engine.
"""


class DefaultMixin(object):
    """Mixin to add Parenchym's standard fields to a model class.

    These are: id, ctime, owner, mtime, editor.
    """

    id = Column(Integer, primary_key=True, nullable=False,
        info={'colanderalchemy': {'title': _("ID")}})
    """Primary key of table."""

    ctime = Column(DateTime, server_default=func.current_timestamp(),
        nullable=False,
            info={'colanderalchemy': {'title': _("Creation Time")}})
    """Timestamp, creation time."""

    # noinspection PyMethodParameters
    @declared_attr
    def owner_id(cls):
        """ID of user who created this record."""
        return Column(
            Integer(),
            ForeignKey(
                "pym.user.id",
                onupdate="CASCADE",
                ondelete="RESTRICT"
            ),
            nullable=False,
            info={'colanderalchemy': {'title': _("OwnerID")}}
        )

    mtime = Column(DateTime, onupdate=func.current_timestamp(), nullable=True,
            info={'colanderalchemy': {'title': _("Mod Time")}})
    """Timestamp, last edit time."""

    # noinspection PyMethodParameters
    @declared_attr
    def editor_id(cls):
        """ID of user who was last editor."""
        return Column(
            Integer(),
            ForeignKey(
                "pym.user.id",
                onupdate="CASCADE",
                ondelete="RESTRICT"
            ),
            nullable=True,
            info={'colanderalchemy': {'title': _("EditorID")}}
        )

    def dump(self):
        from pym.models import todict
        from pprint import pprint
        pprint(todict(self))


@sa.event.listens_for(DefaultMixin, 'before_update', propagate=True)
def receive_before_update(mapper, connection, target):
    will_result_in_update_sql = sa.orm.object_session(target).is_modified(
        target, include_collections=False)
    if will_result_in_update_sql:
        # Now check editor_id
        if target.editor_id is None:
            raise ValueError('Editor must be set on update')


# ================================

# import sqlparse
# from pprint import pprint
# @event.listens_for(sqlalchemy.engine.Engine, "before_cursor_execute",
#     retval=True)
# def before_cursor_execute(conn, cursor, statement,
#                 parameters, context, executemany):
#     print("\n", 'v' * 79)
#     print(sqlparse.format(statement, reindent=True, keyword_case='upper'))
#     print('-' * 79, "\n")
#     pprint(parameters)
#     print('^' * 79, "\n")
#     return statement, parameters

# import sqlparse
# from pprint import pprint
# @event.listens_for(sqlalchemy.engine.Engine, "before_cursor_execute",
#     retval=True)
# def before_cursor_execute(conn, cursor, statement,
#                 parameters, context, executemany):
#     sql = cursor.mogrify(statement, parameters)
#     print("\n", 'v' * 79)
#     print(sqlparse.format(sql, reindent=True, keyword_case='upper'))
#     print('^' * 79, "\n")
#     return statement, parameters


# ===[ IMPORTABLE SETUP FUNCS ]=======

def init(settings, prefix):
    """
    Initializes scoped SQLAlchemy by rc settings.

    Creates engine, binds a scoped session and declarative base.
    Call this function for global initialization of the WebApp.

    Initialises the module globals ``DbEngine``, ``DbSession`` and ``DbBase``.
    The session is joined into the Zope Transaction Manager.

    :param settings: Dict with settings
    :param prefix: Prefix for SQLAlchemy settings
    """
    global DbEngine
    DbEngine = engine_from_config(settings, prefix,
        json_serializer=pym.lib.json_serializer,
        json_deserializer=pym.lib.json_deserializer
    )
    DbSession.configure(bind=DbEngine)
    DbBase.metadata.bind = DbEngine


def init_unscoped(settings, prefix):
    """
    Initializes unscoped SQLAlchemy by rc settings.

    Creates engine, binds a scoped session and declarative base.
    Call this function for global initialization of the WebApp.

    Initialises the module globals ``DbEngine``, ``DbSession`` and ``DbBase``.
    This session has no external transaction manager.

    :param settings: Dict with settings
    :param prefix: Prefix for SQLAlchemy settings
    :return: Dict with ``DbEngine``, ``DbSession`` and ``DbBase``.
    """
    global DbEngine, DbSession, DbBase
    DbEngine = engine_from_config(settings, prefix,
        json_serializer=pym.lib.json_serializer,
        json_deserializer=pym.lib.json_deserializer
    ),
    DbSession = sessionmaker(bind=DbEngine)
    DbBase = declarative_base(bind=DbEngine)


def create_all():
    """Creates bound data model."""
    DbBase.metadata.create_all(DbEngine)

# ================================

### # ===[ FOR SQLITE ]=======
### @event.listens_for(DbEngine, "connect")
### def set_sqlite_pragma(dbapi_connection, connection_record):
###     """
###     This is supposed to turn foreign key constraints on for SQLite, so that
###     we can use SA's ``passive_delete=True``.
###
###     XXX Alas, (at least from CLI scripts) we get an error:
###     ``sqlalchemy.exc.InvalidRequestError: No such event 'connect' for
###     target 'None'``
###     """
###     cursor = dbapi_connection.cursor()
###     cursor.execute("PRAGMA foreign_keys=ON")
###     cursor.close()
### # ================================


# ===[ HELPER ]===================

def todict(o, fully_qualified=False, fmap=None):
    """Transmogrifies data of record object into dict.

    Inspired by
    http://blog.mitechie.com/2010/04/01/hacking-the-sqlalchemy-base-class/
    Converts only physical table columns. Columns created by e.g.
    relationship() must be handled otherwise.

    :param o: Data to transmogrify
    :param fully_qualified: Whether dict keys should be fully qualified (schema
        + '.' + table + '.' + column) or not (just column name). *CAVEAT* Full
        qualification is only possible if ``o`` has attribute ``__table__``.
        E.g. a KeyedTuple does not.
    :param fmap: Mapping of field names to functions. Each function is called to
        build the value for this field.

    :rtype: Dict
    """
    def convert_datetime(v):
        try:
            return v.strftime("%Y-%m-%d %H:%M:%S")
        except AttributeError:
            # 'NoneType' object has no attribute 'strftime'
            return None

    d = {}
    if isinstance(o, sa.util.KeyedTuple):
        d = o._asdict()
    else:
        for c in o.__table__.columns:
            if isinstance(c.type, DateTime):
                value = convert_datetime(getattr(o, c.name))
            elif isinstance(c, InstrumentedList):
                value = list(c)
            else:
                value = getattr(o, c.name)
            if fully_qualified:
                k = o.__table__.schema + '.' + o.__table__.name + '.' + c.name
            else:
                k = c.name
            d[k] = value

    if fmap:
        for k, func in fmap.items():
            d[k] = func(o)
    return d


def todata(rs, fully_qualified=False, fmap=None):
    """Transmogrifies a result set into a list of dicts.

    If ``rs`` is a single instance, only a dict is returned. If ``rs`` is a
    list, a list of dicts is returned.

    :param rs: Data to transmogrify
    :param fully_qualified: Whether dict keys should be fully qualified (schema
        + '.' + table + '.' + column) or not (just column name)

    :rtype: Dict or list of dicts
    """
    if isinstance(rs, (list, sqlalchemy.orm.query.Query)):
        data = []
        for row in rs:
            data.append(todict(row, fully_qualified=fully_qualified, fmap=fmap))
        return data
    else:
        return todict(rs, fully_qualified=fully_qualified, fmap=fmap)


def attribute_names(cls, kind="all"):
    if kind == 'columnproperty':
        return [prop.key for prop in class_mapper(cls).iterate_properties
            if isinstance(prop, ColumnProperty)]
    else:
        return [prop.key for prop in class_mapper(cls).iterate_properties]


# ===[ COMPILER CREATEVIEW ]=======

# http://stackoverflow.com/questions/9766940/how-to-create-an-sql-view-with-sqlalchemy

# class CreateView(Executable, ClauseElement):
#     def __init__(self, name, select):
#         self.name = name
#         self.select = select
#
#
# @compiles(CreateView)
# def visit_create_view(element, compiler, **kw):
#     return "CREATE VIEW %s AS %s" % (
#          element.name,
#          compiler.process(element.select, literal_binds=True)
#          )

# # test data
# from sqlalchemy import MetaData, Column, Integer
# from sqlalchemy.engine import create_engine
# engine = create_engine('sqlite://')
# metadata = MetaData(engine)
# t = Table('t',
#           metadata,
#           Column('id', Integer, primary_key=True),
#           Column('number', Integer))
# t.create()
# engine.execute(t.insert().values(id=1, number=3))
# engine.execute(t.insert().values(id=9, number=-3))
#
# # create view
# createview = CreateView('viewname', t.select().where(t.c.id>5))
# engine.execute(createview)
#
# # reflect view and print result
# v = Table('viewname', metadata, autoload=True)
# for r in engine.execute(v.select()):
#     print r
#
# @compiles(CreateView, 'sqlite')
# def visit_create_view(element, compiler, **kw):
#     return "CREATE VIEW IF NOT EXISTS %s AS %s" % (
#          element.name,
#          compiler.process(element.select, literal_binds=True)
#          )
