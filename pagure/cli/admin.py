# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""
from __future__ import print_function

import argparse
import logging

import pagure.exceptions
import pagure.lib
import pagure.lib.git
from pagure import (SESSION, generate_user_key_files)


_log = logging.getLogger(__name__)


def parse_arguments():
    """ Set-up the argument parsing. """
    parser = argparse.ArgumentParser(
        description='The admin CLI for this pagure instance')

    parser.add_argument(
        '--debug', default=False, action='store_true',
        help='Increase the verbosity of the information displayed')
    parser.set_defaults(func=lambda a, k : print(parser.format_help()))

    subparsers = parser.add_subparsers(title='actions')

    # refresh-gitolite
    parser_gitolite = subparsers.add_parser(
        'refresh-gitolite',
        help='Re-generate the gitolite confi file')
    parser_gitolite.set_defaults(func=do_generate_acl)

    # refresh-ssh
    parser_ssh = subparsers.add_parser(
        'refresh-ssh',
        help='Re-write to disk every user\'s ssh key stored in the database')
    parser_ssh.set_defaults(func=do_refresh_ssh)

    # clear-hook-token
    parser_hook_token = subparsers.add_parser(
        'clear-hook-token',
        help='Generate a new hook token for every project in this instance')
    parser_hook_token.set_defaults(func=do_generate_hook_token)

    return parser.parse_args()


def _ask_confirmation():
    ''' Ask to confirm an action
    '''
    action = raw_input('Do you want to continue? [y/N]')
    return action.lower() in ['y', 'yes']


def do_generate_acl():
    """ Regenerate the gitolite ACL file. """
    cmd = pagure.lib.git._get_gitolite_command()
    if not cmd:
        raise pagure.exceptions.PagureException(
            '/!\ un-able to generate the right gitolite command')
    print('Do you want to re-generate the gitolite.conf file then '
        'calling: %s' % cmd)
    if _ask_confirmation():
        pagure.lib.git.generate_gitolite_acls()
        print('Gitolite ACLs updated')


def do_refresh_ssh():
    """ Regenerate the user key files. """
    print('Do you want to re-generate all the ssh keys for every user in '
        'the database? (Depending on your instance this may take a while '
        'and result in an outage while it lasts)')
    if _ask_confirmation():
        generate_user_key_files()
        print('User key files regenerated')
        do_generate_acl()


def do_generate_hook_token():
    """ Regenerate the hook_token for each projects in the DB. """
    print('Do you want to re-generate all the hook token for every user in '
        'the database? This will break every web-hook set-up on this '
        'instance. You should only ever run this for a security issue')
    if _ask_confirmation():
        pagure.lib.generate_hook_token(SESSION)
        print('Hook token all re-generated')


def main():
    """ Start of the application. """

    # TODO: figure out if the user is allowed to run this tool at all
    #   -> require root?
    #   -> check if pagure's config file is readable?
    #   -> Ask for something private in pagure's config file?

    # Parse the arguments
    args = parse_arguments()

    logging.basicConfig()
    if args.debug:
        _log.setLevel(logging.DEBUG)

    # Act based on the arguments given
    return_code = 0
    try:
        args.func()
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
