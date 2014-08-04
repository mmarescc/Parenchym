# Interesting reads:
# http://stackoverflow.com/questions/270879/efficiently-updating-database-using-sqlalchemy-orm/278606#278606
# http://stackoverflow.com/questions/9593610/creating-a-temporary-table-from-a-query-using-sqlalchemy-orm
# http://stackoverflow.com/questions/9766940/how-to-create-an-sql-view-with-sqlalchemy
# Materialized view:
# http://stackoverflow.com/questions/11114903/oracle-functional-index-creation
#
# http://stackoverflow.com/questions/4617291/how-do-i-get-a-raw-compiled-sql-query-from-a-sqlalchemy-expression

import datetime

import sqlalchemy as sa
from sqlalchemy import (
    engine_from_config,
    Column,
    Integer,
    Unicode,
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

from psycopg2.extensions import adapt as sqlescape
# or use the appropiate escape function from your db driver

from zope.sqlalchemy import ZopeTransactionExtension

import colander
import deform
import deform.widget
import pyramid.i18n
import pym.exc
import pym.lib
import pym.i18n
import pym.cache


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

cache_regions = {}

DbSession = scoped_session(
    sessionmaker(
        query_cls=pym.cache.query_callable(cache_regions),
        extension=ZopeTransactionExtension()
    )
)
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

    IDENTITY_COL = 'name'
    """
    Name of a column that can be used to identify a record uniquely, besides ID.
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

    dtime = Column(DateTime, nullable=True,
            info={'colanderalchemy': {'title': _("Deletion Time")}})
    """Timestamp, deletion time."""

    # noinspection PyMethodParameters
    @declared_attr
    def deleter_id(cls):
        """ID of user who tagged this this record as deleted."""
        return Column(
            Integer(),
            ForeignKey(
                "pym.user.id",
                onupdate="CASCADE",
                ondelete="RESTRICT"
            ),
            nullable=True,
            info={'colanderalchemy': {'title': _("DeleterID")}}
        )

    # noinspection PyMethodParameters
    @declared_attr
    def deletion_reason(cls):
        """Optional reason for deletion."""
        return Column(Unicode(255), nullable=True,
            info={'colanderalchemy': {'title': _("Deletion Reason")}}
        )

    def dump(self):
        from pym.models import todict
        from pprint import pprint
        pprint(todict(self))

    @classmethod
    def find(cls, sess, obj):
        """
        Finds given object and returns its instance.

        Input object may be the integer ID of a DB record, or a value that is
        checked in IDENTITY_COL. If object is already the requested instance,
        it is returned unchanged.

        Raises NoResultFound if object is unknown.
        """
        if isinstance(obj, int):
            o = sess.query(cls).get(obj)
            if not o:
                raise sa.orm.exc.NoResultFound()
            return o
        elif isinstance(obj, cls):
            return obj
        else:
            if not cls.IDENTITY_COL:
                raise TypeError('{} has no IDENTITY_COL'.format(cls.__name__))
            fil = {cls.IDENTITY_COL: obj}
            return sess.query(cls).filter_by(**fil).one()

    def is_deleted(self):
        return self.deleter_id is not None


@sa.event.listens_for(DefaultMixin, 'before_update', propagate=True)
def receive_before_update(mapper, connection, target):
    will_result_in_update_sql = sa.orm.object_session(target).is_modified(
        target, include_collections=False)
    if will_result_in_update_sql:
        # Now check editor_id
        if target.editor_id is None:
            raise ValueError('Editor must be set on update for ' + str(target))


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
#     sql = cursor.mogrify(statement, parameters).decode('UTF-8')
#     print("\n", 'v' * 79)
#     print(sqlparse.format(sql, reindent=True, keyword_case='upper'))
#     # print('-' * 79, "\n")
#     # from traceback import print_stack
#     # print_stack()
#     print('^' * 79, "\n")
#     return statement, parameters


# ===[ IMPORTABLE SETUP FUNCS ]=======

def init(settings, prefix, invalidate_caches=False):
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

    add_cache_region('default', pym.cache.region_default)
    add_cache_region('auth_short_term', pym.cache.region_auth_short_term)
    add_cache_region('auth_long_term', pym.cache.region_auth_long_term)
    if invalidate_caches:
        pym.cache.region_default.invalidate()
        pym.cache.region_auth_short_term.invalidate()
        pym.cache.region_auth_long_term.invalidate()


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


def add_cache_region(name, region):
    cache_regions[name] = region


def exists(sess, name, schema='public'):
    """
    Checks if given relation exists.

    Relation may be:

    r = ordinary table
    i = index
    S = sequence
    v = view
    f = foreign table
    m = materialized view

    :param sess: Instance of a DB session.
    :param name: Name of the relation.
    :param schema: Optional name of schema. Defaults to 'public'.
    :return: One of above mentioned letters if relation exists, None if not.
    """
    q = sa.text("""
        SELECT c.relkind
        FROM   pg_class     c
        JOIN   pg_namespace n ON n.oid = c.relnamespace
        WHERE  c.relname = :name     -- sequence name here
        AND    n.nspname = :schema  -- schema name here
        AND    c.relkind = ANY('{r,i,S,v,f,m}');
    """)
    k = sess.execute(q, {'name': name, 'schema': schema}).scalar()
    return k if k else None

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

def todict(o, fully_qualified=False, fmap=None, excludes=None):
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
    :param excludes: Optional list of column names to exclude
    :rtype: Dict
    """
    def convert_datetime(v):
        try:
            return v.strftime("%Y-%m-%d %H:%M:%S")
        except AttributeError:
            # 'NoneType' object has no attribute 'strftime'
            return None

    d = {}
    if excludes is None:
        excludes = []
    if isinstance(o, sa.util.KeyedTuple):
        d = o._asdict()
    else:
        for c in o.__table__.columns:
            if c.name in excludes:
                continue
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
from sqlalchemy.sql import compiler


def compile_query(query):
    dialect = query.session.bind.dialect
    statement = query.statement
    comp = compiler.SQLCompiler(dialect, statement)
    comp.compile()
    enc = dialect.encoding
    params = {}
    for k, v in comp.params.items():
        params[k] = sqlescape(v)
    return comp.string % params

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
