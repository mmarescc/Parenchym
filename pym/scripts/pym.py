# -*- coding: utf-8 -*-

"""
``pym`` has several sub-commands to manage your Pym setup: you can
manage principals (users), roles and role memberships as well as install new
sites and check the integrity of existing sites.

The sub-commands are::

    list-principals     List principals
    create-principal       Create principal
    update-principal    Update principal with given ID
    delete-principal    Delete principal with given ID
    list-roles          List roles
    create-role            Create role
    update-role         Update role with given ID
    delete-role         Delete role with given ID
    list-rolemembers    List rolemembers
    create-rolemember      Create rolemember
    delete-rolemember   Delete rolemember with given ID

Type ``pym -h`` for general help and a list of the sub-commands,
``pym sub-command -h`` to get help for that sub-command.

``pym`` allows you to use different formats for input and output.
Choices are json, yaml (default) and tsv.

Tsv is handy if you want to review the output in a spreadsheet::

    pym -c production.ini --format tsv list-principals > a && gnumeric a

Both, json and yaml allow inline-style. Here is an example of inline YAML::

    pym -c production.ini --format yaml create-principal \\
        '{principal: FOO5, email: foo5@here, pwd: FOO, roles: [foo, bar]}'
    TTY? True
    Locale? en_GB UTF-8
    id: 106
    display_name: FOO5
    email: foo5@here
    first_name: null
    csrf_token: null
    identity_url: null
    is_blocked: false
    is_enabled: false
    last_name: null
    login_time: null
    notes: null
    prev_login_time: null
    principal: FOO5
    pwd: FOO
    owner: 2
    ctime: '2012-12-07 07:47:23'
    editor: null
    mtime: null
    role_names:
    - foo
    - bar
    - users
    Done.

Here is an example of creating a new site::

    pym -c production.ini --format yaml create-site '{sitename: www.new-site.com, principal: {principal: sally, email: sally@example.com, pwd: FOO, first_name: Sally, last_name: Müller-Lüdenscheidt, roles: [some_role, other_role]}, title: Neue Site, site_template: default}'
    TTY? True
    Locale? en_GB UTF-8
    Proceed to create a site in /tmp/sites (yes/NO)? yes
    Copied template [...]/var/site-templates/default
    Created role 'www.new-site.com' (108)
    Created principal 'sally' (111)
    Set principal 'sally' as member of role 'www.new-site.com'
    Done.

To get an overview, which user is in which role, and if there are orphans (should not),
do::

    pym -c production.ini --format tsv list-rolemembers > a && gnumeric a

"""
import logging

import os
import sys
import transaction
import argparse
import yaml
import time
from collections import OrderedDict
import datetime

import pym.models
import pym.lib
import pym.cli
import pym.auth.manager as authmgr
import pym.auth.const


# Init YAML to dump an OrderedDict like a regular dict, i.e.
# without creating a specific object tag.
def _represent_ordereddict(self, data):
    return self.represent_mapping('tag:yaml.org,2002:map', data.items())

yaml.add_representer(OrderedDict, _represent_ordereddict)


class PymCli(pym.cli.Cli):

    def __init__(self):
        super().__init__()

    def list_users(self):
        from pym.auth.models import User
        qry = self._build_query(User)
        data = self._db_data_to_list(qry,
            fkmaps=dict(groups=lambda it: it.name))
        self._print(data)

    def list_users_with_groups(self):
        from pym.auth.models import User

        #qry = self._build_query(User)
        sess = pym.models.DbSession()
        users = sess.query(User)
        data = {}
        for u in users:
            k = "u:{} ({})".format(u.principal, u.id)
            groups = []
            for gr in u.groups:
                groups.append("g:{} ({})".format(gr.name, gr.id))
            data[k] = groups
        self._print(data)

    def create_user(self):
        data = self._parse(self.args.data)
        data['owner'] = pym.auth.const.ROOT_UID
        rs = authmgr.create_user(data)
        self._print(self._db_data_to_list([rs],
            fkmaps=dict(group_names=lambda it: it))[0])

    def update_user(self):
        data = self._parse(self.args.data)
        data['editor'] = pym.auth.const.ROOT_UID
        data['mtime'] = datetime.datetime.now()
        rs = authmgr.update_user(data)
        self._print(self._db_data_to_list([rs])[0])

    def delete_user(self):
        authmgr.delete_user(self.args.id)

    def list_groups(self):
        from pym.auth.models import Group
        qry = self._build_query(Group)
        data = self._db_data_to_list(qry)
        self._print(data)

    def list_groups_with_members(self):
        from pym.auth.models import Group
        #groups = self._build_query(Group)
        sess = pym.models.DbSession()
        groups = sess.query(Group)
        data = {}
        for gr in groups:
            k = 'g:{} ({})'.format(gr.name, gr.id)
            member_users = []
            for mu in gr.member_users:
                if not mu:
                    continue
                member_users.append('{} ({})'.format(mu.principal, mu.id))
            member_groups = []
            for mg in gr.member_groups:
                if not mg:
                    continue
                member_groups.append('{} ({})'.format(mg.name, mg.id))
            data[k] = {
                'u': member_users,
                'g': member_groups
            }
        self._print(data)

    def create_group(self):
        data = self._parse(self.args.data)
        data['owner'] = pym.auth.const.ROOT_UID
        rs = authmgr.create_group(data)
        self._print(self._db_data_to_list([rs])[0])

    def update_group(self):
        data = self._parse(self.args.data)
        data['editor'] = pym.auth.const.ROOT_UID
        data['mtime'] = datetime.datetime.now()
        rs = authmgr.update_group(data)
        self._print(self._db_data_to_list([rs])[0])

    def delete_group(self):
        authmgr.delete_group(self.args.id)

    def list_group_members(self):
        pass
        # from pym.auth.models import User, Group, GroupMember
        # groups = self._build_query(Group)
        # fields = ['id', 'group_id', 'group', 'user_id', 'principal',
        #     'is_enabled', 'is_blocked', 'owner', 'ctime']
        # data = {}
        # for gr in groups:
        #     grdat = {
        #         'user'
        #     }
        # self._print(data)

    def create_group_member(self):
        data = self._parse(self.args.data)
        data['owner'] = pym.auth.const.ROOT_UID
        rs = authmgr.create_group_member(data)
        self._print(self._db_data_to_list([rs])[0])

    def delete_group_member(self):
        authmgr.delete_group_member(self.args.id)

    def _build_query(self, entity):
        sess = pym.models.DbSession()
        if isinstance(entity, list):
            entities = entity
            entity = entities[0]
        else:
            entities = [entity]
        qry = sess.query(entities)
        if self.args.idlist:
            qry = qry.filter(entity.id.in_(self.args.idlist))
        else:
            if self.args.filter:
                qry = qry.filter(self.args.filter)
        if self.args.order:
            qry = qry.order_by(self.args.order)
        return qry


def parse_args(app_class, runner):
    # Main parser
    parser = argparse.ArgumentParser(description="""Pym command-line
        interface.""",
        epilog="""
        Samples:

        pym -c production.ini --format tsv list-group-members --order
        'group_name, principal_principal' > /tmp/a.txt && gnumeric /tmp/a.txt
        """)

    app_class.add_parser_args(parser, (
        ('config', True),
        ('locale', False),
        ('format', False),
        ('alembic-config', False)
    ))

    parser.add_argument('--dry-run', action="store_true",
        help="The database changes will be rolled back.")
    subparsers = parser.add_subparsers(title="Commands", dest="subparser_name",
        help="""Type 'pym COMMAND --help'""")

    # Parent parser for DB editing
    parser_db_edit = argparse.ArgumentParser(description="Database editing",
        add_help=False)
    parser_db_edit.add_argument('data',
        help="The data. For updates, field ID must be present.")

    # Parent parser for DB deleting
    parser_db_delete = argparse.ArgumentParser(description="Database deleting",
        add_help=False)
    parser_db_delete.add_argument('id', type=int,
        help="The ID")

    # Parent parser for DB listers
    parser_db_lister = argparse.ArgumentParser(description="Database lister",
        add_help=False)
    parser_db_lister.add_argument('idlist', nargs='*', type=int, metavar='ID',
        help="""Filter by these IDs""")
    parser_db_lister.add_argument('--filter',
        help="""Define filter with literal SQL (WHERE clause, e.g. 'id between
        200 and 300')""")
    parser_db_lister.add_argument('--order',
        help="""Define sort order with literal SQL (ORDER BY clause, e.g. 'name
        DESC')""")

    # Parser cmd list-users
    parser_list_users = subparsers.add_parser('list-users',
        parents=[parser_db_lister],
        help="List users")
    parser_list_users.set_defaults(func=runner.list_users)
    parser_list_users_with_groups = subparsers.add_parser('list-users-with-groups',
        parents=[parser_db_lister],
        help="List users with their groups.")
    parser_list_users_with_groups.set_defaults(func=runner.list_users_with_groups)

    # Parser cmd create-user
    parser_create_user = subparsers.add_parser('create-user',
        parents=[parser_db_edit],
        help="Create user",
        epilog="""You might want to try command 'list-users'
            to see which fields are available."""
    )
    parser_create_user.set_defaults(func=runner.create_user)

    # Parser cmd update-user
    parser_update_user = subparsers.add_parser('update-user',
        parents=[parser_db_edit],
        help="Update user with given ID",
        epilog="""You might want to try command 'list-users'
            to see which fields are available."""
    )
    parser_update_user.set_defaults(func=runner.update_user)

    # Parser cmd delete-user
    parser_delete_user = subparsers.add_parser('delete-user',
        parents=[parser_db_delete],
        help="Delete user with given ID",
    )
    parser_delete_user.set_defaults(func=runner.delete_user)

    # Parser cmd list-groups
    parser_list_groups = subparsers.add_parser('list-groups',
        parents=[parser_db_lister],
        help="List groups")
    parser_list_groups.set_defaults(func=runner.list_groups)
    parser_list_groups_with_members = subparsers.add_parser('list-groups-with-members',
        parents=[parser_db_lister],
        help="List groups with their members.")
    parser_list_groups_with_members.set_defaults(func=runner.list_groups_with_members)

    # Parser cmd create-group
    parser_create_group = subparsers.add_parser('create-group',
        parents=[parser_db_edit],
        help="Create group")
    parser_create_group.set_defaults(func=runner.create_group)

    # Parser cmd update-group
    parser_update_group = subparsers.add_parser('update-group',
        parents=[parser_db_edit],
        help="Update group with given ID")
    parser_update_group.set_defaults(func=runner.update_group)

    # Parser cmd delete-group
    parser_delete_group = subparsers.add_parser('delete-group',
        parents=[parser_db_delete],
        help="Delete group with given ID")
    parser_delete_group.set_defaults(func=runner.delete_group)

    # Parser cmd list-group-members
    parser_list_group_members = subparsers.add_parser('list-group-members',
        parents=[parser_db_lister],
        help="List group-members")
    parser_list_group_members.set_defaults(func=runner.list_group_members)

    # Parser cmd create-group-member
    parser_create_group_member = subparsers.add_parser('create-group-member',
        parents=[parser_db_edit],
        help="Create group-member")
    parser_create_group_member.set_defaults(func=runner.create_group_member)

    # Parser cmd delete-group-member
    parser_delete_group_member = subparsers.add_parser('delete-group-member',
        parents=[parser_db_delete],
        help="Delete group-member with given ID")
    parser_delete_group_member.set_defaults(func=runner.delete_group_member)

    return parser.parse_args()


def main(argv=None):
    if not argv:
        argv = sys.argv
    start_time = time.time()
    app_name = os.path.basename(argv[0])
    lgg = logging.getLogger('cli.' + app_name)

    runner = PymCli()
    args = parse_args(PymCli, runner)

    runner.init_app(args, lgg=lgg, setup_logging=True)
    transaction.begin()
    # noinspection PyBroadException
    try:
        args.func()
    except Exception as exc:
        transaction.abort()
        lgg.exception(exc)
        lgg.fatal('Changes rolled back.')
        lgg.fatal('Program aborted!')
    else:
        if args.dry_run:
            transaction.abort()
            lgg.info('Dry-run. Changes rolled back.')
        else:
            transaction.commit()
            lgg.info('Changes committed.')
    finally:
        lgg.info('{} secs.'.format(time.time() - start_time))
        # Do some cleanup or saving etc.
