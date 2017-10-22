# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""
from __future__ import print_function

import argparse
import datetime
import logging
import os
import sys

import arrow

if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    print('Using configuration file `/etc/pagure/pagure.cfg`')
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'

import pagure.exceptions  # noqa: E402
import pagure.lib  # noqa: E402
import pagure.lib.git  # noqa: E402
import pagure.lib.tasks  # noqa: E402
from pagure import (SESSION, APP, generate_user_key_files)  # noqa: E402


_log = logging.getLogger(__name__)


WATCH = {
    '-1': 'reset the watch status to default',
    '0': 'unwatch, don\'t notify the user of anything',
    '1': 'watch issues and PRs',
    '2': 'watch commits',
    '3': 'watch issues, PRs and commits',
}


def _parser_refresh_gitolite(subparser):
    """ Set up the CLI argument parser for the refresh-gitolite action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

     """
    local_parser = subparser.add_parser(
        'refresh-gitolite',
        help='Re-generate the gitolite config file')
    local_parser.add_argument(
        '--user', help="User of the project (to use only on forks)")
    local_parser.add_argument(
        '--project', help="Project to update (as namespace/project if there "
        "is a namespace)")
    local_parser.add_argument(
        '--group', help="Group to refresh")
    local_parser.add_argument(
        '--all', dest="all_", default=False, action='store_true',
        help="Refresh all the projects")
    local_parser.set_defaults(func=do_generate_acl)


def _parser_refresh_ssh(subparser):
    """ Set up the CLI argument parser for the refresh-ssh action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        'refresh-ssh',
        help="Re-write to disk every user's ssh key stored in the database")
    local_parser.set_defaults(func=do_refresh_ssh)


def _parser_clear_hook_token(subparser):
    """ Set up the CLI argument parser for the clear-hook-token action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        'clear-hook-token',
        help='Generate a new hook token for every project in this instance')
    local_parser.set_defaults(func=do_generate_hook_token)


def _parser_admin_token_list(subparser):
    """ Set up the CLI argument parser for the admin-token list action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        'list', help="List the API admin token")
    local_parser.add_argument(
        '--user',
        help="User to associate or associated with the token")
    local_parser.add_argument(
        '--token', help="API token")
    local_parser.add_argument(
        '--active', default=False, action='store_true',
        help="Only list active API token")
    local_parser.add_argument(
        '--expired', default=False, action='store_true',
        help="Only list expired API token")
    local_parser.set_defaults(func=do_list_admin_token)


def _parser_admin_token_info(subparser):
    """ Set up the CLI argument parser for the admin-token info action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        'info', help="Provide some information about a specific API token")
    local_parser.add_argument(
        'token', help="API token")
    local_parser.set_defaults(func=do_info_admin_token)


def _parser_admin_token_expire(subparser):
    """ Set up the CLI argument parser for the admin-token expire action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    # Expire admin token
    local_parser = subparser.add_parser(
        'expire', help="Expire a specific API token")
    local_parser.add_argument(
        'token', help="API token")
    local_parser.set_defaults(func=do_expire_admin_token)


def _parser_admin_token_create(subparser):
    """ Set up the CLI argument parser for the admin-token create action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    # Create admin token
    local_parser = subparser.add_parser(
        'create', help="Create a new API token")
    local_parser.add_argument(
        'user', help="User to associate with the token")
    local_parser.set_defaults(func=do_create_admin_token)


def _parser_admin_token_update(subparser):
    """ Set up the CLI argument parser for the admin-token update action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    # Update admin token
    local_parser = subparser.add_parser(
        'update', help="Update the expiration date of an API token")
    local_parser.add_argument(
        'token', help="API token")
    local_parser.add_argument(
        'date', help="New expiration date")
    local_parser.set_defaults(func=do_update_admin_token)


def _parser_admin_token(subparser):
    """ Set up the CLI argument parser for the admin-token action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        'admin-token',
        help='Manages the admin tokens for this instance')

    subsubparser = local_parser.add_subparsers(title='actions')

    # list
    _parser_admin_token_list(subsubparser)
    # info
    _parser_admin_token_info(subsubparser)
    # expire
    _parser_admin_token_expire(subsubparser)
    # create
    _parser_admin_token_create(subsubparser)
    # update
    _parser_admin_token_update(subsubparser)


def _parser_get_watch(subparser):
    """ Set up the CLI argument parser for the get-watch action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    # Update watch status
    local_parser = subparser.add_parser(
        'get-watch', help="Get someone's watch status on a project")
    local_parser.add_argument(
        'project', help="Project (as namespace/project if there "
        "is a namespace) -- Fork not supported")
    local_parser.add_argument(
        'user', help="User to get the watch status of")
    local_parser.set_defaults(func=do_get_watch_status)


def _parser_update_watch(subparser):
    """ Set up the CLI argument parser for the update-watch action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    # Update watch status
    local_parser = subparser.add_parser(
        'update-watch', help="Update someone's watch status on a project")
    local_parser.add_argument(
        'project', help="Project to update (as namespace/project if there "
        "is a namespace) -- Fork not supported")
    local_parser.add_argument(
        'user', help="User to update the watch status of")
    local_parser.add_argument(
        '-s', '--status', help="Watch status to update to")
    local_parser.set_defaults(func=do_update_watch_status)


def _parser_read_only(subparser):
    """ Set up the CLI argument parser for the refresh-gitolite action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        'read-only',
        help='Get or set the read-only flag on a project')
    local_parser.add_argument(
        '--user', help="User of the project (to use only on forks)")
    local_parser.add_argument(
        'project', help="Project to update (as namespace/project if there "
        "is a namespace)")
    local_parser.add_argument(
        '--ro',
        help="Read-Only status to set (has to be: true or false), do not "
             "specify to get the current status")
    local_parser.set_defaults(func=do_read_only)


def parse_arguments():
    """ Set-up the argument parsing. """
    parser = argparse.ArgumentParser(
        description='The admin CLI for this pagure instance')

    parser.add_argument(
        '--debug', default=False, action='store_true',
        help='Increase the verbosity of the information displayed')

    subparser = parser.add_subparsers(title='actions')

    # refresh-gitolite
    _parser_refresh_gitolite(subparser)

    # refresh-ssh
    _parser_refresh_ssh(subparser)

    # clear-hook-token
    _parser_clear_hook_token(subparser)

    # Admin token actions
    _parser_admin_token(subparser)

    # get-watch
    _parser_get_watch(subparser)

    # update-watch
    _parser_update_watch(subparser)

    # read-only
    _parser_read_only(subparser)

    return parser.parse_args()


def _ask_confirmation():
    ''' Ask to confirm an action.
    '''
    action = raw_input('Do you want to continue? [y/N]')
    return action.lower() in ['y', 'yes']


def _get_input(text):
    ''' Ask the user for input. '''
    return raw_input(text)


def _get_project(arg_project, user=None):
    ''' From the project specified to the CLI, extract the actual project.
    '''
    namespace = None
    if '/' in arg_project:
        if arg_project.count('/') > 1:
            raise pagure.exceptions.PagureException(
                'Invalid project name, has more than one "/": %s' %
                arg_project)
        namespace, name = arg_project.split('/')
    else:
        name = arg_project

    return pagure.lib._get_project(
        SESSION, namespace=namespace, name=name, user=user)


def do_generate_acl(args):
    """ Regenerate the gitolite ACL file.


    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug('group:          %s', args.group)
    _log.debug('project:        %s', args.project)
    _log.debug('user:           %s', args.user)
    _log.debug('all:            %s', args.all_)

    title = None
    project = None
    if args.project:
        project = _get_project(args.project, user=args.user)
        title = project.fullname
    if args.all_:
        title = 'all'
        project = -1

    if not args.all_ and not args.project:
        print(
            'Please note that you have not selected a project or --all. '
            'Do you want to recompile the existing config file?')
        if not _ask_confirmation():
            return

    helper = pagure.lib.git_auth.get_git_auth_helper(
        APP.config['GITOLITE_BACKEND'])
    _log.debug('Got helper: %s', helper)

    group_obj = None
    if args.group:
        group_obj = pagure.lib.search_groups(SESSION, group_name=args.group)
    _log.debug(
        'Calling helper: %s with arg: project=%s, group=%s',
        helper, project, group_obj)

    print(
        'Do you want to re-generate the gitolite.conf file for group: %s '
        'and project: %s?' % (group_obj, title))
    if _ask_confirmation():
        helper.generate_acls(project=project, group=group_obj)
        pagure.lib.tasks.gc_clean()
        print('Gitolite ACLs updated')


def do_refresh_ssh(_):
    """ Regenerate the user key files.

    :arg _: the argparse object returned by ``parse_arguments()``, which is
        ignored as there are no argument to pass to this action.

    """
    print(
        'Do you want to re-generate all the ssh keys for every user in '
        'the database? (Depending on your instance this may take a while '
        'and result in an outage while it lasts)')
    if _ask_confirmation():
        generate_user_key_files()
        print('User key files regenerated')
        do_generate_acl()


def do_generate_hook_token(_):
    """ Regenerate the hook_token for each projects in the DB.

    :arg _: the argparse object returned by ``parse_arguments()``, which is
        ignored as there are no argument to pass to this action.

    """
    print(
        'Do you want to re-generate all the hook token for every user in '
        'the database? This will break every web-hook set-up on this '
        'instance. You should only ever run this for a security issue')
    if _ask_confirmation():
        pagure.lib.generate_hook_token(SESSION)
        print('Hook token all re-generated')


def do_list_admin_token(args):
    """ List the admin token.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug('user:           %s', args.user)
    _log.debug('token:          %s', args.token)
    _log.debug('active:         %s', args.active)
    _log.debug('expire:         %s', args.expired)

    acls = APP.config['ADMIN_API_ACLS']
    tokens = pagure.lib.search_token(
        SESSION, acls,
        user=args.user,
        active=args.active,
        expired=args.expired)

    for token in tokens:
        print('%s -- %s -- %s' % (
            token.id, token.user.user, token.expiration))
    if not tokens:
        print('No admin tokens found')


def do_info_admin_token(args):
    """ Print out information about the specified API token.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug('token:          %s', args.token)

    acls = APP.config['ADMIN_API_ACLS']
    token = pagure.lib.search_token(SESSION, acls, token=args.token)
    if not token:
        raise pagure.exceptions.PagureException('No such admin token found')

    print('%s -- %s -- %s' % (
        token.id, token.user.user, token.expiration))
    print('ACLs:')
    for acl in token.acls:
        print('  - %s' % acl.name)


def do_expire_admin_token(args):
    """ Expire a specific admin token.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug('token:          %s', args.token)

    acls = APP.config['ADMIN_API_ACLS']
    token = pagure.lib.search_token(SESSION, acls, token=args.token)
    if not token:
        raise pagure.exceptions.PagureException('No such admin token found')

    print('%s -- %s -- %s' % (
        token.id, token.user.user, token.expiration))
    print('ACLs:')
    for acl in token.acls:
        print('  - %s' % acl.name)

    print('Do you really want to expire this API token?')
    if _ask_confirmation():
        token.expiration = datetime.datetime.utcnow()
        SESSION.add(token)
        SESSION.commit()
        print('Token expired')


def do_update_admin_token(args):
    """ Update the expiration date of an admin token.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug('token:          %s', args.token)
    _log.debug('new date:       %s', args.date)

    acls = APP.config['ADMIN_API_ACLS']
    token = pagure.lib.search_token(SESSION, acls, token=args.token)
    if not token:
        raise pagure.exceptions.PagureException('No such admin token found')

    try:
        date = arrow.get(args.date, 'YYYY-MM-DD').replace(tzinfo='UTC')
    except Exception as err:
        _log.exception(err)
        raise pagure.exceptions.PagureException(
            'Invalid new expiration date submitted: %s, not of the format '
            'YYYY-MM-DD' % args.date
        )

    if date.naive.date() <= datetime.datetime.utcnow().date():
        raise pagure.exceptions.PagureException(
            'You are about to expire this API token using the wrong '
            'command, please use: pagure-admin admin-token expire'
        )

    print('%s -- %s -- %s' % (
        token.id, token.user.user, token.expiration))
    print('ACLs:')
    for acl in token.acls:
        print('  - %s' % acl.name)

    print(
        'Do you really want to update this API token to expire on %s?' %
        args.date)
    if _ask_confirmation():
        token.expiration = date.naive
        SESSION.add(token)
        SESSION.commit()
        print('Token updated')


def do_create_admin_token(args):
    """ Create a new admin token.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug('user:          %s', args.user)
    # Validate user first
    pagure.lib.get_user(SESSION, args.user)

    acls_list = APP.config['ADMIN_API_ACLS']
    for idx, acl in enumerate(acls_list):
        print('%s.  %s' % (idx, acl))

    print('Which ACLs do you want to associated with this token?')
    acls = _get_input('(Comma separated list): ')
    acls_idx = [int(acl.strip()) for acl in acls.split(',')]
    acls = [acls_list[acl] for acl in acls_idx]

    print('ACLs selected:')
    for idx, acl in enumerate(acls_idx):
        print('%s.  %s' % (acls_idx[idx], acls[idx]))

    print('Do you want to create this API token?')
    if _ask_confirmation():
        print(pagure.lib.add_token_to_user(SESSION, None, acls, args.user))


def do_get_watch_status(args):
    """ Get the watch status of an user on a project.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug('user:          %s', args.user)
    _log.debug('project:       %s', args.project)
    # Validate user
    pagure.lib.get_user(SESSION, args.user)

    # Get the project
    project = _get_project(args.project)

    if project is None:
        raise pagure.exceptions.PagureException(
            'No project found with: %s' % args.project)

    level = pagure.lib.get_watch_level_on_repo(
        session=SESSION,
        user=args.user,
        repo=project.name,
        repouser=None,
        namespace=project.namespace) or []

    # Specify that issues == 'issues & PRs'
    if 'issues' in level:
        level.append('pull-requests')

    print('On %s user: %s is watching the following items: %s' % (
        project.fullname, args.user, ', '.join(level) or None))


def do_update_watch_status(args):
    """ Update the watch status of an user on a project.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """

    _log.debug('user:          %s', args.user)
    _log.debug('status:        %s', args.status)
    _log.debug('project:       %s', args.project)

    # Validate user
    pagure.lib.get_user(SESSION, args.user)

    # Ask the status if none were given
    if args.status is None:
        print('The watch status can be one of the following: ')
        for lvl in WATCH:
            print('%s: %s' % (lvl, WATCH[lvl]))
        args.status = _get_input('Status:')

    # Validate the status
    if args.status not in WATCH:
        raise pagure.exceptions.PagureException(
            'Invalid status provided: %s not in %s' % (
                args.status, ', '.join(sorted(WATCH.keys()))))

    # Get the project
    project = _get_project(args.project)

    if project is None:
        raise pagure.exceptions.PagureException(
            'No project found with: %s' % args.project)

    print('Updating watch status of %s to %s (%s) on %s' % (
        args.user, args.status, WATCH[args.status], args.project))

    pagure.lib.update_watch_status(
        session=SESSION,
        project=project,
        user=args.user,
        watch=args.status)
    SESSION.commit()


def do_read_only(args):
    """ Set or update the read-only status of a project.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """

    _log.debug('project:       %s', args.project)
    _log.debug('user:          %s', args.user)
    _log.debug('read-only:     %s', args.ro)

    # Validate user
    pagure.lib.get_user(SESSION, args.user)

    # Get the project
    project = _get_project(args.project)

    if project is None:
        raise pagure.exceptions.PagureException(
            'No project found with: %s' % args.project)

    # Validate ro flag
    if args.ro and args.ro.lower() not in ['true', 'false']:
        raise pagure.exceptions.PagureException(
            'Invalid read-only status specified: %s is not in: '
            'true, false' % args.ro.lower())

    if not args.ro:
        print(
            'The current read-only flag of the project %s is set to %s' % (
                project.fullname, project.read_only))
    else:
        pagure.lib.update_read_only_mode(
            SESSION, project, read_only=(args.ro.lower() == 'true')
        )
        SESSION.commit()
        print(
            'The read-only flag of the project %s has been set to %s' % (
                project.fullname, args.ro.lower() == 'true'))


def main():
    """ Start of the application. """

    # Parse the arguments
    args = parse_arguments()

    logging.basicConfig()
    if args.debug:
        _log.setLevel(logging.DEBUG)

    # Act based on the arguments given
    return_code = 0
    try:
        args.func(args)
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return_code = 1
    except pagure.exceptions.PagureException as err:
        print(err)
        return_code = 3
    except Exception as err:
        print('Error: {0}'.format(err))
        logging.exception("Generic error catched:")
        return_code = 2

    return return_code


if __name__ == '__main__':
    sys.exit(main())
