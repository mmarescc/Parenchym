import functools
import json
import datetime
import sqlalchemy as sa
import sqlalchemy.exc
from pyramid.view import view_config, view_defaults
import colanderalchemy
import pyramid.i18n
import pyramid.httpexceptions as hexc

import pym.auth
import pym.auth.models as pam
import pym.auth.manager as pamgr
from pym.models import DbSession, todata
import pym.lib
import pym.i18n


_ = pyramid.i18n.TranslationStringFactory(pym.i18n.DOMAIN)
_tr = lambda s: s


json_serializer = functools.partial(
    json.dumps,
    sort_keys=False,
    indent=2,
    ensure_ascii=False,
    cls=pym.lib.JsonEncoder
)

json_deserializer = json.loads

crud_entity = pam.User

browse_field_list = [
    crud_entity.id,
    crud_entity.is_enabled,
    crud_entity.is_blocked,
    crud_entity.principal,
    crud_entity.email,
    crud_entity.first_name,
    crud_entity.last_name,
    crud_entity.display_name,
    crud_entity.pwd_expires,
    crud_entity.descr
]

edit_field_list = [
    crud_entity.is_enabled,
    crud_entity.is_blocked,
    crud_entity.principal,
    crud_entity.pwd,
    crud_entity.pwd_expires,
    crud_entity.email,
    crud_entity.first_name,
    crud_entity.last_name,
    crud_entity.display_name,
    crud_entity.descr
]

default_col_defs = {
    crud_entity.id: {'width': '50'},
    crud_entity.is_enabled: {'width': '50'},
    crud_entity.is_blocked: {'width': '50'},
    crud_entity.principal: {},
    crud_entity.pwd: {},
    crud_entity.pwd_expires: {},
    crud_entity.email: {},
    crud_entity.first_name: {},
    crud_entity.last_name: {},
    crud_entity.display_name: {},
    crud_entity.descr: {}
}


def build_schema(field_list, translate_func):
    includes = []
    coldefs = []
    for x in field_list:
        includes.append(x.key)
        colal = x.info.get('colanderalchemy', {})
        cd = {
            'field': x.key,
            'displayName': translate_func(colal.get('title', x.key)),
            'width': '200'
        }
        dcd = default_col_defs.get(x, None)
        if dcd:
            for k, v in dcd.items():
                cd[k] = translate_func(v)
        coldefs.append(cd)
    schema = colanderalchemy.SQLAlchemySchemaNode(crud_entity, includes=includes)
    return schema, coldefs


@view_defaults(
    context=pym.auth.models.IUserMgrNode,
    permission='manage_auth'
)
class UserView(object):

    def __init__(self, context, request):
        global _tr
        _tr = request.localizer.translate

        self.context = context
        self.request = request
        self.sess = DbSession()
        self.urls = dict(
            entity_rest_url=request.resource_path(context, 'xhr')
        )

    @view_config(
        name='',
        renderer='pym:auth/templates/user/index.mako',
    )
    def index(self):
        sess = self.sess
        rs = sess.query(*browse_field_list)
        data = todata(rs, fmap={'pwd': lambda x: ''})
        sch, coldefs = build_schema(
            browse_field_list, self.request.localizer.translate)
        return dict(
            data=json_serializer(data),
            coldefs=json_serializer(coldefs),
            urls=json_serializer(self.urls)
        )

    @view_config(
        name='xhr',
        renderer='json',
        request_method='GET'
    )
    def xhr_load_browse_data(self):
        sess = self.sess
        try:
            rs = sess.query(*browse_field_list)
        except sa.exc.SQLAlchemyError as exc:
            # TODO Log exception
            return hexc.HTTPException(detail=str(exc))
        else:
            data = todata(rs, fmap={'pwd': lambda x: ''})
        return data

    @view_config(
        name='xhr',
        renderer='json',
        request_method='GET',
        subpath='id/\d+/r'
    )
    def xhr_load_entity(self):
        try:
            id_ = int(self.request.named_subpaths['id'])
        except (KeyError, ValueError):
            return hexc.HTTPBadRequest(detail=_tr(_("Missing ID")))

        sess = self.sess
        try:
            entity = sess.query(pam.User).get(id_)
        except sa.exc.SQLAlchemyError as exc:
            # TODO Log exception
            return hexc.HTTPException(detail=str(exc))
        else:
            if not entity:
                return hexc.HTTPNotFound(detail=_tr(_("Invalid ID")))
            data = todata(entity, fmap={'pwd': lambda x: ''})
        return data

    @view_config(
        name='xhr',
        renderer='json',
        request_method='POST'
    )
    def xhr_create_entity(self):
        resp = pym.lib.JsonResp()
        sess = self.sess
        entity = pam.User()
        entity.owner_id = self.request.user.uid
        try:
            sess.flush()
        except sa.exc.SQLAlchemyError as exc:
            # TODO Log exception
            return hexc.HTTPException(detail=str(exc))
        return resp.resp

    @view_config(
        name='xhr',
        renderer='json',
        request_method='PUT',
        subpath='id/\d+/r'
    )
    def xhr_update_entity(self):
        resp = pym.lib.JsonResp()
        try:
            id_ = int(self.request.named_subpaths['id'])
        except (KeyError, ValueError):
            return hexc.HTTPBadRequest(detail=_tr(_("Missing ID")))

        sess = self.sess
        try:
            entity = sess.query(pam.User).get(id_)
        except sa.exc.SQLAlchemyError as exc:
            # TODO Log exception
            return hexc.HTTPException(detail=str(exc))
        else:
            if not entity:
                return hexc.HTTPNotFound(detail=_tr(_("Invalid ID")))
            # TODO validate body data
            # TODO update and save entity
            entity.editor_id = self.request.user.uid
            entity.mtime = datetime.datetime.now()
            try:
                sess.flush()
            except sa.exc.SQLAlchemyError as exc:
                # TODO Log exception
                return hexc.HTTPException(detail=str(exc))
            return resp.resp