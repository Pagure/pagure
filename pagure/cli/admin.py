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

if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    print('Using configuration file `/etc/pagure/pagure.cfg`')
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'

import pagure.exceptions  # noqa
import pagure.lib  # noqa
import pagure.lib.git  # noqa
from pagure import (SESSION, APP, generate_user_key_files)  # noqa


_log = logging.getLogger(__name__)


def parse_arguments():
    """ Set-up the argument parsing. """
    parser = argparse.ArgumentParser(
        description='The admin CLI for this pagure instance')

    parser.add_argument(
        '--debug', default=False, action='store_true',
        help='Increase the verbosity of the information displayed')
    parser.set_defaults(func=lambda a, k: print(parser.format_help()))

    subparsers = parser.add_subparsers(title='actions')

    # refresh-gitolite
    parser_gitolite = subparsers.add_parser(
        'refresh-gitolite',
        help='Re-generate the gitolite config file')
    parser_gitolite.set_defaults(func=do_generate_acl)

    # refresh-ssh
    parser_ssh = subparsers.add_parser(
        'refresh-ssh',
        help="Re-write to disk every user's ssh key stored in the database")
    parser_ssh.set_defaults(func=do_refresh_ssh)

    # clear-hook-token
    parser_hook_token = subparsers.add_parser(
        'clear-hook-token',
        help='Generate a new hook token for every project in this instance')
    parser_hook_token.set_defaults(func=do_generate_hook_token)

    # Admin token actions
    parser_admin_token = subparsers.add_parser(
        'admin-token',
        help='Manages the admin tokens for this instance')

    subsubparsers = parser_admin_token.add_subparsers(title='actions')

    # List admin token
    parser_admin_list_token = subsubparsers.add_parser(
        'list',  help="List the API admin token")
    parser_admin_list_token.add_argument(
        '--user',
        help="User to associate or associated with the token")
    parser_admin_list_token.add_argument(
        '--token', help="API token")
    parser_admin_list_token.add_argument(
        '--active', default=False, action='store_true',
        help="Only list active API token")
    parser_admin_list_token.add_argument(
        '--expired', default=False, action='store_true',
        help="Only list expired API token")
    parser_admin_token.set_defaults(func=do_list_admin_token)

    # Info about admin token
    parser_admin_info_token = subsubparsers.add_parser(
        'info',  help="Provide some information about a specific API token")
    parser_admin_info_token.add_argument(
        'token', help="API token")
    parser_admin_info_token.set_defaults(func=do_info_admin_token)

    # Expire admin token
    parser_admin_expire_token = subsubparsers.add_parser(
        'expire',  help="Expire a specific API token")
    parser_admin_expire_token.add_argument(
        'token', help="API token")
    parser_admin_expire_token.set_defaults(func=do_expire_admin_token)

    # Create admin token
    parser_admin_create_token = subsubparsers.add_parser(
        'create',  help="Create a new API token")
    parser_admin_create_token.add_argument(
        'user', help="User to associate with the token")
    parser_admin_create_token.set_defaults(func=do_create_admin_token)

    return parser.parse_args()


def _ask_confirmation():
    ''' Ask to confirm an action.
    '''
    action = raw_input('Do you want to continue? [y/N]')
    return action.lower() in ['y', 'yes']


def do_generate_acl(_):
    """ Regenerate the gitolite ACL file.


    :arg _: the argparse object returned by ``parse_arguments()``, which is
        ignored as there are no argument to pass to this action.

    """
    cmd = pagure.lib.git._get_gitolite_command()
    if not cmd:
        raise pagure.exceptions.PagureException(
            '/!\ un-able to generate the right gitolite command')
    print(
        'Do you want to re-generate the gitolite.conf file then '
        'calling: %s' % cmd)
    if _ask_confirmation():
        pagure.lib.git.generate_gitolite_acls()
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
        SESSION, acls, active=args.active, expired=args.expired)
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
    acls = raw_input('(Conna separated list): ')
    acls_idx = [int(acl.strip()) for acl in acls.split(',')]
    acls = [acls_list[acl] for acl in acls_idx]

    print('ACLs selected:')
    for idx, acl in enumerate(acls_idx):
        print('%s.  %s' % (acls_idx[idx], acls[idx]))

    print('Do you want to create this API token?')
    if _ask_confirmation():
        print(pagure.lib.add_token_to_user(SESSION, None, acls, args.user))


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
