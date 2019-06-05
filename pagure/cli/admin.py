# -*- coding: utf-8 -*-

"""
 (c) 2017-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import print_function, unicode_literals, absolute_import

import argparse
import datetime
import logging
import os
import requests
from string import Template
import sys
import pygit2

import arrow
from six.moves import input

if "PAGURE_CONFIG" not in os.environ and os.path.exists(
    "/etc/pagure/pagure.cfg"
):
    print("Using configuration file `/etc/pagure/pagure.cfg`")
    os.environ["PAGURE_CONFIG"] = "/etc/pagure/pagure.cfg"

import pagure.config  # noqa: E402
import pagure.exceptions  # noqa: E402
import pagure.lib.git  # noqa: E402
import pagure.lib.model  # noqa: E402
import pagure.lib.model_base  # noqa: E402
import pagure.lib.query  # noqa: E402
import pagure.lib.tasks_utils  # noqa: E402
from pagure.flask_app import generate_user_key_files  # noqa: E402
from pagure.utils import get_repo_path  # noqa: E402


_config = pagure.config.reload_config()
session = pagure.lib.model_base.create_session(_config["DB_URL"])
_log = logging.getLogger(__name__)


WATCH = {
    "-1": "reset the watch status to default",
    "0": "unwatch, don't notify the user of anything",
    "1": "watch issues and PRs",
    "2": "watch commits",
    "3": "watch issues, PRs and commits",
}


def _parser_refresh_gitolite(subparser):
    """ Set up the CLI argument parser for the refresh-gitolite action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

     """
    local_parser = subparser.add_parser(
        "refresh-gitolite", help="Re-generate the gitolite config file"
    )
    local_parser.add_argument(
        "--user", help="User of the project (to use only on forks)"
    )
    local_parser.add_argument(
        "--project",
        help="Project to update (as namespace/project if there "
        "is a namespace)",
    )
    local_parser.add_argument("--group", help="Group to refresh")
    local_parser.add_argument(
        "--all",
        dest="all_",
        default=False,
        action="store_true",
        help="Refresh all the projects",
    )
    local_parser.set_defaults(func=do_generate_acl)


def _parser_refresh_ssh(subparser):
    """ Set up the CLI argument parser for the refresh-ssh action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        "refresh-ssh",
        help="Re-write to disk every user's ssh key stored in the database",
    )
    local_parser.set_defaults(func=do_refresh_ssh)


def _parser_clear_hook_token(subparser):
    """ Set up the CLI argument parser for the clear-hook-token action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        "clear-hook-token",
        help="Generate a new hook token for every project in this instance",
    )
    local_parser.set_defaults(func=do_generate_hook_token)


def _parser_admin_token_list(subparser):
    """ Set up the CLI argument parser for the admin-token list action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        "list", help="List the API admin token"
    )
    local_parser.add_argument(
        "--user", help="User to associate or associated with the token"
    )
    local_parser.add_argument("--token", help="API token")
    local_parser.add_argument(
        "--active",
        default=False,
        action="store_true",
        help="Only list active API token",
    )
    local_parser.add_argument(
        "--expired",
        default=False,
        action="store_true",
        help="Only list expired API token",
    )
    local_parser.add_argument(
        "--all",
        default=False,
        action="store_true",
        help="Only list all API token instead of only those with admin ACLs",
    )
    local_parser.set_defaults(func=do_list_admin_token)


def _parser_admin_token_info(subparser):
    """ Set up the CLI argument parser for the admin-token info action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        "info", help="Provide some information about a specific API token"
    )
    local_parser.add_argument("token", help="API token")
    local_parser.set_defaults(func=do_info_admin_token)


def _parser_admin_token_expire(subparser):
    """ Set up the CLI argument parser for the admin-token expire action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    # Expire admin token
    local_parser = subparser.add_parser(
        "expire", help="Expire a specific API token"
    )
    local_parser.add_argument("token", help="API token")
    local_parser.add_argument(
        "--all",
        default=False,
        action="store_true",
        help="Act on any API token instead of only those with admin ACLs",
    )
    local_parser.set_defaults(func=do_expire_admin_token)


def _parser_admin_token_create(subparser):
    """ Set up the CLI argument parser for the admin-token create action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    # Create admin token
    local_parser = subparser.add_parser(
        "create", help="Create a new API token"
    )
    local_parser.add_argument("user", help="User to associate with the token")
    local_parser.add_argument(
        "expiration_date", help="Expiration date for the new token"
    )
    local_parser.set_defaults(func=do_create_admin_token)


def _parser_admin_token_update(subparser):
    """ Set up the CLI argument parser for the admin-token update action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    # Update admin token
    local_parser = subparser.add_parser(
        "update", help="Update the expiration date of an API token"
    )
    local_parser.add_argument("token", help="API token")
    local_parser.add_argument("date", help="New expiration date")
    local_parser.add_argument(
        "--all",
        default=False,
        action="store_true",
        help="Act on any API token instead of only those with admin ACLs",
    )
    local_parser.set_defaults(func=do_update_admin_token)


def _parser_admin_token(subparser):
    """ Set up the CLI argument parser for the admin-token action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        "admin-token", help="Manages the admin tokens for this instance"
    )

    subsubparser = local_parser.add_subparsers(title="actions")

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
        "get-watch", help="Get someone's watch status on a project"
    )
    local_parser.add_argument(
        "project",
        help="Project (as namespace/project if there "
        "is a namespace) -- Fork not supported",
    )
    local_parser.add_argument("user", help="User to get the watch status of")
    local_parser.set_defaults(func=do_get_watch_status)


def _parser_update_watch(subparser):
    """ Set up the CLI argument parser for the update-watch action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    # Update watch status
    local_parser = subparser.add_parser(
        "update-watch", help="Update someone's watch status on a project"
    )
    local_parser.add_argument(
        "project",
        help="Project to update (as namespace/project if there "
        "is a namespace) -- Fork not supported",
    )
    local_parser.add_argument(
        "user", help="User to update the watch status of"
    )
    local_parser.add_argument(
        "-s", "--status", help="Watch status to update to"
    )
    local_parser.set_defaults(func=do_update_watch_status)


def _parser_read_only(subparser):
    """ Set up the CLI argument parser for the read-only action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        "read-only", help="Get or set the read-only flag on a project"
    )
    local_parser.add_argument(
        "--user", help="User of the project (to use only on forks)"
    )
    local_parser.add_argument(
        "project",
        help="Project to update (as namespace/project if there "
        "is a namespace)",
    )
    local_parser.add_argument(
        "--ro",
        help="Read-Only status to set (has to be: true or false), do not "
        "specify to get the current status",
    )
    local_parser.set_defaults(func=do_read_only)


def _parser_new_group(subparser):
    """ Set up the CLI argument parser for the new-group action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        "new-group", help="Create a new group on this pagure instance"
    )
    local_parser.add_argument("group_name", help="Name of the group")
    local_parser.add_argument(
        "username",
        help="Name of the user creating the group "
        "(will be added to the group once created)",
    )
    local_parser.add_argument("--display", help="Display name of the group")
    local_parser.add_argument(
        "--description", help="Short description of the group"
    )
    local_parser.set_defaults(func=do_new_group)


def _parser_list_groups(subparser):
    """ Set up the CLI argument parser for the list-groups action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        "list-groups", help="Lists existing groups on this pagure instance"
    )
    local_parser.set_defaults(func=do_list_groups)


def _parser_block_user(subparser):
    """ Set up the CLI argument parser for the block-user action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

    """
    local_parser = subparser.add_parser(
        "block-user",
        help="Prevents an user to interact with this pagure instance until "
        "the specified date",
    )
    local_parser.add_argument(
        "username", default=None, nargs="?", help="Name of the user to block"
    )
    local_parser.add_argument(
        "date",
        nargs="?",
        default=None,
        help="Date before which the user is not welcome on this pagure "
        "instance",
    )
    local_parser.add_argument(
        "--list",
        default=False,
        action="store_true",
        help="List all blocked users",
    )
    local_parser.set_defaults(func=do_block_user)


def _parser_upload_repospanner_hooks(subparser):
    """ Set up the CLI argument parser to upload repospanner hook.

    Args:
        subparser: An argparse subparser
    """
    local_parser = subparser.add_parser(
        "upload-repospanner-hook", help="Upload repoSpanner hook script"
    )
    local_parser.add_argument(
        "region", help="repoSpanner region where to " "upload hook"
    )
    local_parser.set_defaults(func=do_upload_repospanner_hooks)


def _parser_ensure_project_hooks(subparser):
    """ Set up the CLI argument parser to ensure project hooks are setup

    Args:
        subparser: An argparse subparser
    """
    local_parser = subparser.add_parser(
        "ensure-project-hooks",
        help="Ensure all projects have their hooks setup",
    )
    local_parser.add_argument(
        "hook", help="repoSpanner hook ID to set", default=None
    )
    local_parser.set_defaults(func=do_ensure_project_hooks)


def _parser_delete_project(subparser):
    """ Set up the CLI argument parser for the delete-project action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

     """
    local_parser = subparser.add_parser(
        "delete-project", help="Delete the project specified"
    )
    local_parser.add_argument(
        "--user", help="User of the project (to use only on forks)"
    )
    local_parser.add_argument(
        "project",
        help="Project to update (as namespace/project if there "
        "is a namespace)",
    )
    local_parser.add_argument(
        "action_user",
        help="Username of the user doing the action (ie: deleting the "
        "project)",
    )
    local_parser.set_defaults(func=do_delete_project)


def _parser_create_branch(subparser):
    """ Set up the CLI argument parser for the create-branch action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

     """
    local_parser = subparser.add_parser(
        "create-branch",
        help="Create the specified branch in the specified project",
    )
    local_parser.add_argument(
        "--user", help="User of the project (to use only on forks)"
    )
    local_parser.add_argument(
        "project",
        help="Project to update (as namespace/project if there "
        "is a namespace)",
    )
    local_parser.add_argument(
        "--from-branch",
        default=None,
        help="Name of the branch on which to base the new one",
    )
    local_parser.add_argument(
        "--from-commit",
        default=None,
        help="Commit on which to base the new branch",
    )
    local_parser.add_argument(
        "new_branch", help="Name of the new branch to create"
    )
    local_parser.add_argument(
        "action_user",
        help="Username of the user doing the action (ie: creating the "
        "branch)",
    )
    local_parser.set_defaults(func=do_create_branch)


def _parser_set_default_branch(subparser):
    """ Set up the CLI argument parser for the set-default-branch action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

     """
    local_parser = subparser.add_parser(
        "set-default-branch", help="Set the specified branch as default"
    )
    local_parser.add_argument(
        "project",
        help="Project to update (as namespace/project if there "
        "is a namespace)",
    )
    local_parser.add_argument(
        "--user", help="User of the project (to use only on forks)"
    )
    local_parser.add_argument(
        "branch", help="Name of the branch to be set as default"
    )
    local_parser.set_defaults(func=do_set_default_branch)


def _parser_update_acls(subparser):
    """ Set up the CLI argument parser for the update-acls action.

    :arg subparser: an argparse subparser allowing to have action's specific
        arguments

     """

    local_parser = subparser.add_parser(
        "update-acls",
        help="Update the ACLs stored in the database with the ones defined "
        "in the configuration file (addition only, no ACLs are removed from "
        "the database).",
    )
    local_parser.set_defaults(func=do_update_acls)


def parse_arguments(args=None):
    """ Set-up the argument parsing. """
    parser = argparse.ArgumentParser(
        description="The admin CLI for this pagure instance"
    )

    parser.add_argument(
        "-c", "--config", default=None, help="Specify a configuration to use"
    )

    parser.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help="Increase the verbosity of the information displayed",
    )

    subparser = parser.add_subparsers(title="actions")

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

    # new-group
    _parser_new_group(subparser)

    # list-groups
    _parser_list_groups(subparser)

    # block-user
    _parser_block_user(subparser)

    # upload-repospanner-hooks
    _parser_upload_repospanner_hooks(subparser)

    # ensure-project-hooks
    _parser_ensure_project_hooks(subparser)

    # delete-project
    _parser_delete_project(subparser)

    # create-branch
    _parser_create_branch(subparser)

    # set-default-branch
    _parser_set_default_branch(subparser)

    # update-acls
    _parser_update_acls(subparser)

    return parser.parse_args(args)


def _ask_confirmation():
    """ Ask to confirm an action.
    """
    action = input("Do you want to continue? [y/N]")
    return action.lower() in ["y", "yes"]


def _get_input(text):
    """ Ask the user for input. """
    return input(text)


def _get_project(arg_project, user=None):
    """ From the project specified to the CLI, extract the actual project.
    """
    namespace = None
    if "/" in arg_project:
        if arg_project.count("/") > 1:
            raise pagure.exceptions.PagureException(
                'Invalid project name, has more than one "/": %s' % arg_project
            )
        namespace, name = arg_project.split("/")
    else:
        name = arg_project

    return pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )


def _check_project(_project, **kwargs):
    """ Check that the project extracted with args is a valid project """
    if _project is None:
        raise pagure.exceptions.PagureException(
            "No project found with: {}".format(
                ", ".join(
                    ["{}={}".format(k, v) for k, v in sorted(kwargs.items())]
                )
            )
        )


def do_generate_acl(args):
    """ Regenerate the gitolite ACL file.


    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug("group:          %s", args.group)
    _log.debug("project:        %s", args.project)
    _log.debug("user:           %s", args.user)
    _log.debug("all:            %s", args.all_)

    title = None
    project = None
    if args.project:
        project = _get_project(args.project, user=args.user)
        title = project.fullname
    if args.all_:
        title = "all"
        project = -1

    if not args.all_ and not args.project:
        print(
            "Please note that you have not selected a project or --all. "
            "Do you want to recompile the existing config file?"
        )
        if not _ask_confirmation():
            return

    helper = pagure.lib.git_auth.get_git_auth_helper()
    _log.debug("Got helper: %s", helper)

    group_obj = None
    if args.group:
        group_obj = pagure.lib.query.search_groups(
            session, group_name=args.group
        )
    _log.debug(
        "Calling helper: %s with arg: project=%s, group=%s",
        helper,
        project,
        group_obj,
    )

    print(
        "Do you want to re-generate the gitolite.conf file for group: %s "
        "and project: %s?" % (group_obj, title)
    )
    if _ask_confirmation():
        helper.generate_acls(project=project, group=group_obj)
        pagure.lib.tasks_utils.gc_clean()
        print("Gitolite ACLs updated")


def do_refresh_ssh(_):
    """ Regenerate the user key files.

    :arg _: the argparse object returned by ``parse_arguments()``, which is
        ignored as there are no argument to pass to this action.

    """
    print(
        "Do you want to re-generate all the ssh keys for every user in "
        "the database? (Depending on your instance this may take a while "
        "and result in an outage while it lasts)"
    )
    if _ask_confirmation():
        generate_user_key_files()
        print("User key files regenerated")
        do_generate_acl()


def do_generate_hook_token(_):
    """ Regenerate the hook_token for each projects in the DB.

    :arg _: the argparse object returned by ``parse_arguments()``, which is
        ignored as there are no argument to pass to this action.

    """
    print(
        "Do you want to re-generate all the hook token for every user in "
        "the database? This will break every web-hook set-up on this "
        "instance. You should only ever run this for a security issue"
    )
    if _ask_confirmation():
        pagure.lib.query.generate_hook_token(session)
        print("Hook token all re-generated")


def do_list_admin_token(args):
    """ List the admin token.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug("user:           %s", args.user)
    _log.debug("token:          %s", args.token)
    _log.debug("active:         %s", args.active)
    _log.debug("expire:         %s", args.expired)
    _log.debug("all:            %s", args.all)

    acls = pagure.config.config["ADMIN_API_ACLS"]
    if args.all:
        acls = None
    tokens = pagure.lib.query.search_token(
        session, acls, user=args.user, active=args.active, expired=args.expired
    )

    for token in tokens:
        print("%s -- %s -- %s" % (token.id, token.user.user, token.expiration))
    if not tokens:
        print("No admin tokens found")


def do_info_admin_token(args):
    """ Print out information about the specified API token.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug("token:          %s", args.token)

    token = pagure.lib.query.search_token(session, acls=None, token=args.token)
    if not token:
        raise pagure.exceptions.PagureException("No such admin token found")

    print("%s -- %s -- %s" % (token.id, token.user.user, token.expiration))
    print("ACLs:")
    for acl in token.acls:
        print("  - %s" % acl.name)


def do_expire_admin_token(args):
    """ Expire a specific admin token.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug("token:          %s", args.token)
    _log.debug("all:            %s", args.all)

    acls = pagure.config.config["ADMIN_API_ACLS"]
    if args.all:
        acls = None
    token = pagure.lib.query.search_token(session, acls, token=args.token)
    if not token:
        raise pagure.exceptions.PagureException("No such admin token found")

    print("%s -- %s -- %s" % (token.id, token.user.user, token.expiration))
    print("ACLs:")
    for acl in token.acls:
        print("  - %s" % acl.name)

    print("Do you really want to expire this API token?")
    if _ask_confirmation():
        token.expiration = datetime.datetime.utcnow()
        session.add(token)
        session.commit()
        print("Token expired")


def do_update_admin_token(args):
    """ Update the expiration date of an admin token.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug("token:          %s", args.token)
    _log.debug("new date:       %s", args.date)
    _log.debug("all:            %s", args.all)

    acls = pagure.config.config["ADMIN_API_ACLS"]
    if args.all:
        acls = None
    token = pagure.lib.query.search_token(session, acls, token=args.token)
    if not token:
        raise pagure.exceptions.PagureException("No such admin token found")

    try:
        date = arrow.get(args.date, "YYYY-MM-DD").replace(tzinfo="UTC")
    except Exception as err:
        _log.exception(err)
        raise pagure.exceptions.PagureException(
            "Invalid new expiration date submitted: %s, not of the format "
            "YYYY-MM-DD" % args.date
        )

    if date.naive.date() <= datetime.datetime.utcnow().date():
        raise pagure.exceptions.PagureException(
            "You are about to expire this API token using the wrong "
            "command, please use: pagure-admin admin-token expire"
        )

    print("%s -- %s -- %s" % (token.id, token.user.user, token.expiration))
    print("ACLs:")
    for acl in token.acls:
        print("  - %s" % acl.name)

    print(
        "Do you really want to update this API token to expire on %s?"
        % args.date
    )
    if _ask_confirmation():
        token.expiration = date.naive
        session.add(token)
        session.commit()
        print("Token updated")


def do_create_admin_token(args):
    """ Create a new admin token.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug("user:          %s", args.user)
    # Validate user first
    pagure.lib.query.get_user(session, args.user)

    # Validate the expiration date
    try:
        expiration_date = arrow.get(
            args.expiration_date, "YYYY-MM-DD"
        ).replace(tzinfo="UTC")
        expiration_date = expiration_date.date()
    except Exception as err:
        _log.exception(err)
        raise pagure.exceptions.PagureException(
            "Invalid expiration date submitted: %s, not of the format "
            "YYYY-MM-DD" % args.expiration_date
        )

    acls_list = pagure.config.config["ADMIN_API_ACLS"]
    for idx, acl in enumerate(acls_list):
        print("%s.  %s" % (idx, acl))

    print("Which ACLs do you want to associated with this token?")
    acls = _get_input("(Comma separated list): ")
    acls_idx = [int(acl.strip()) for acl in acls.split(",")]
    acls = [acls_list[acl] for acl in acls_idx]

    print("ACLs selected:")
    for idx, acl in enumerate(acls_idx):
        print("%s.  %s" % (acls_idx[idx], acls[idx]))

    print("Do you want to create this API token?")
    if _ask_confirmation():
        print(
            pagure.lib.query.add_token_to_user(
                session,
                project=None,
                acls=acls,
                username=args.user,
                expiration_date=expiration_date,
            )
        )


def do_delete_project(args):
    """ Delete a project.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug("project:       %s", args.project)
    _log.debug("user:          %s", args.user)
    _log.debug("user deleting: %s", args.action_user)

    # Validate users
    pagure.lib.query.get_user(session, args.user)
    pagure.lib.query.get_user(session, args.action_user)

    # Get the project
    project = _get_project(args.project, user=args.user)

    _check_project(project, project=args.project, user=args.user)

    print(
        "Are you sure you want to delete: %s?\n  This cannot be undone!"
        % project.fullname
    )
    if not _ask_confirmation():
        return

    pagure.lib.tasks.delete_project(
        namespace=project.namespace,
        name=project.name,
        user=project.user.user if project.is_fork else None,
        action_user=args.action_user,
    )
    session.commit()
    print("Project deleted")


def do_update_acls(args):
    """ Update the ACLs in the database from the list present in the
    configuration file.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    acls = _config.get("ACLS", {})
    _log.debug("ACLS:       %s", acls)

    pagure.lib.model.create_default_status(session, acls=acls)
    print(
        "ACLS in the database synced with the list in the configuration file"
    )


def do_get_watch_status(args):
    """ Get the watch status of an user on a project.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    _log.debug("user:          %s", args.user)
    _log.debug("project:       %s", args.project)
    # Validate user
    pagure.lib.query.get_user(session, args.user)

    # Get the project
    project = _get_project(args.project)

    _check_project(project, project=args.project)

    level = (
        pagure.lib.query.get_watch_level_on_repo(
            session=session,
            user=args.user,
            repo=project.name,
            repouser=None,
            namespace=project.namespace,
        )
        or []
    )

    # Specify that issues == 'issues & PRs'
    if "issues" in level:
        level.append("pull-requests")

    print(
        "On %s user: %s is watching the following items: %s"
        % (project.fullname, args.user, ", ".join(level) or None)
    )


def do_update_watch_status(args):
    """ Update the watch status of an user on a project.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """

    _log.debug("user:          %s", args.user)
    _log.debug("status:        %s", args.status)
    _log.debug("project:       %s", args.project)

    # Validate user
    pagure.lib.query.get_user(session, args.user)

    # Ask the status if none were given
    if args.status is None:
        print("The watch status can be one of the following: ")
        for lvl in WATCH:
            print("%s: %s" % (lvl, WATCH[lvl]))
        args.status = _get_input("Status:")

    # Validate the status
    if args.status not in WATCH:
        raise pagure.exceptions.PagureException(
            "Invalid status provided: %s not in %s"
            % (args.status, ", ".join(sorted(WATCH.keys())))
        )

    # Get the project
    project = _get_project(args.project)

    _check_project(project, project=args.project)

    print(
        "Updating watch status of %s to %s (%s) on %s"
        % (args.user, args.status, WATCH[args.status], args.project)
    )

    pagure.lib.query.update_watch_status(
        session=session, project=project, user=args.user, watch=args.status
    )
    session.commit()


def do_read_only(args):
    """ Set or update the read-only status of a project.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """

    _log.debug("project:       %s", args.project)
    _log.debug("user:          %s", args.user)
    _log.debug("read-only:     %s", args.ro)

    # Validate user
    pagure.lib.query.get_user(session, args.user)

    # Get the project
    project = _get_project(args.project, user=args.user)

    _check_project(project, project=args.project)

    # Validate ro flag
    if args.ro and args.ro.lower() not in ["true", "false"]:
        raise pagure.exceptions.PagureException(
            "Invalid read-only status specified: %s is not in: "
            "true, false" % args.ro.lower()
        )

    if not args.ro:
        print(
            "The current read-only flag of the project %s is set to %s"
            % (project.fullname, project.read_only)
        )
    else:
        pagure.lib.query.update_read_only_mode(
            session, project, read_only=(args.ro.lower() == "true")
        )
        session.commit()
        print(
            "The read-only flag of the project %s has been set to %s"
            % (project.fullname, args.ro.lower() == "true")
        )


def do_new_group(args):
    """ Create a new group in this pagure instance.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """

    _log.debug("name:               %s", args.group_name)
    _log.debug("display-name:       %s", args.display)
    _log.debug("description:        %s", args.description)
    _log.debug("username:           %s", args.username)

    # Validate user
    pagure.lib.query.get_user(session, args.username)

    if not args.username:
        raise pagure.exceptions.PagureException(
            "An username must be provided to associate with the group"
        )

    if not args.display:
        raise pagure.exceptions.PagureException(
            "A display name must be provided for the group"
        )

    if pagure.config.config.get("ENABLE_GROUP_MNGT") is False:
        print("Group management has been turned off for this pagure instance")
        if not _ask_confirmation():
            return

    msg = pagure.lib.query.add_group(
        session=session,
        group_name=args.group_name,
        display_name=args.display,
        description=args.description,
        group_type="user",
        user=args.username,
        is_admin=True,
        blacklist=pagure.config.config["BLACKLISTED_GROUPS"],
    )
    session.commit()
    print("Group `%s` created." % args.group_name)
    print(msg)


def do_list_groups(args):
    """ Lists existing groups in this pagure instance.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """

    msg = pagure.lib.query.search_groups(session=session)
    if msg:
        print("List of groups on this Pagure instance:")
        for group in msg:
            print(group)
    else:
        print("No groups found in this pagure instance.")


def do_list_blocked_users(args):
    """ List all the blocked users.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """
    date = None
    if args.date:
        try:
            date = arrow.get(args.date, "YYYY-MM-DD").replace(tzinfo="UTC")
            date = date.datetime
        except Exception as err:
            _log.exception(err)
            raise pagure.exceptions.PagureException(
                "Invalid date submitted: %s, not of the format "
                "YYYY-MM-DD" % args.date
            )

    blocked_users = pagure.lib.query.get_blocked_users(
        session, username=args.username or None, date=date
    )
    if blocked_users:
        print("Users blocked:")
        for user in blocked_users:
            print(
                " %s  -  %s"
                % (
                    user.user.ljust(20),
                    user.refuse_sessions_before.isoformat(),
                )
            )
    else:
        print("No users are currently blocked")


def do_block_user(args):
    """ Block the specified user from all interactions with pagure until the
    specified date.

    :arg args: the argparse object returned by ``parse_arguments()``.

    """

    _log.debug("username:           %s", args.username)
    _log.debug("date:               %s", args.date)
    _log.debug("list:               %s", args.list)

    if args.list:
        return do_list_blocked_users(args)

    if not args.username:
        raise pagure.exceptions.PagureException(
            "An username must be specified"
        )

    try:
        date = arrow.get(args.date, "YYYY-MM-DD").replace(tzinfo="UTC")
    except Exception as err:
        _log.exception(err)
        raise pagure.exceptions.PagureException(
            "Invalid date submitted: %s, not of the format "
            "YYYY-MM-DD" % args.date
        )

    # Validate user
    user = pagure.lib.query.get_user(session, args.username)

    print(
        "The user `%s` will be blocked from all interaction with this "
        "pagure instance until: %s." % (user.username, date.isoformat())
    )
    if not _ask_confirmation():
        return

    user.refuse_sessions_before = date.datetime
    session.add(user)
    session.commit()


def do_upload_repospanner_hooks(args):
    """ Upload hooks to repoSpanner

    Args:
        args (argparse.Namespace): Parsed arguments
    """
    regioninfo = pagure.config.config["REPOSPANNER_REGIONS"].get(args.region)
    if not regioninfo:
        raise ValueError(
            "repoSpanner region %s not in config file" % args.region
        )

    env = {
        "config": os.environ.get("PAGURE_CONFIG", "/etc/pagure/pagure.cfg"),
        "pypath": os.environ.get("PYTHONPATH", "None"),
    }
    sourcefile = os.path.abspath(
        os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "../hooks/files/repospannerhook",
        )
    )
    with open(sourcefile, "r") as source:
        template = source.read()
    hookcontents = Template(template).substitute(env)

    resp = requests.post(
        "%s/admin/hook/admin.git/upload" % regioninfo["url"],
        data=hookcontents,
        headers={"X-Object-Size": str(len(hookcontents))},
        verify=regioninfo["ca"],
        cert=(
            regioninfo["admin_cert"]["cert"],
            regioninfo["admin_cert"]["key"],
        ),
    )
    resp.raise_for_status()
    resp = resp.json()
    _log.debug("Response json: %s", resp)
    if not resp["Success"]:
        raise Exception("Error in repoSpanner API call: %s" % resp["Error"])
    hook = resp["Info"]
    print("Hook ID for region %s: %s" % (args.region, hook))
    return hook


def do_ensure_project_hooks(args):
    """ Ensures that all projects have their hooks setup

    Args:
        args (argparse.Namespace): Parsed arguments
    """
    projects = []
    query = session.query(pagure.lib.model.Project).order_by(
        pagure.lib.model.Project.id
    )
    for project in query.all():
        print("Ensuring hooks for %s" % project.fullname)
        projects.append(project.fullname)
        pagure.lib.git.set_up_project_hooks(
            project, project.repospanner_region, hook=args.hook
        )
    return projects


def do_create_branch(args):
    """ Creates the specified git branch

    Args:
        args (argparse.Namespace): Parsed arguments
    """
    _log.debug("project:         %s", args.project)
    _log.debug("user:            %s", args.user)
    _log.debug("new branch:      %s", args.new_branch)
    _log.debug("from branch:     %s", args.from_branch)
    _log.debug("from commit:     %s", args.from_commit)
    _log.debug("user creating:   %s", args.action_user)

    if not args.from_branch and not args.from_commit:
        raise pagure.exceptions.PagureException(
            "You must create the branch from something, either a commit "
            "or another branch"
        )
    if args.from_branch and args.from_commit:
        raise pagure.exceptions.PagureException(
            "You must create the branch from something, either a commit "
            "or another branch, not from both"
        )

    # Validate users
    pagure.lib.query.get_user(session, args.action_user)

    # Get the project
    project = _get_project(args.project, user=args.user)

    _check_project(project, project=args.project, user=args.user)

    try:
        pagure.lib.git.new_git_branch(
            args.action_user,
            project,
            args.new_branch,
            from_branch=args.from_branch,
            from_commit=args.from_commit,
        )
    except ValueError:
        if args.from_commit:
            raise pagure.exceptions.PagureException(
                "No commit %s found from which to branch" % (args.from_commit)
            )
        else:  # pragma: no-cover
            raise

    print("Branch created")


def do_set_default_branch(args):
    """ Sets the specified git branch as default

    Args:
        args (argparse.Namespace): Parsed arguments
    """
    _log.debug("project:         %s", args.project)
    _log.debug("user:            %s", args.user)
    _log.debug("branch:          %s", args.branch)

    # Get the project
    project = _get_project(args.project, user=args.user)

    _check_project(project, project=args.project, user=args.user)

    repo_path = get_repo_path(project)
    repo_obj = pygit2.Repository(repo_path)

    if args.branch not in repo_obj.listall_branches():
        raise pagure.exceptions.PagureException(
            "No %s branch found on project: %s" % (args.branch, args.project)
        )

    pagure.lib.git.git_set_ref_head(project, args.branch)

    print("Branch %s set as default" % (args.branch))


def main():
    """ Start of the application. """

    # Parse the arguments
    args = parse_arguments()

    if args.config:
        config = args.config
        if not config.startswith("/"):
            config = os.path.join(os.getcwd(), config)
        os.environ["PAGURE_CONFIG"] = config

        global session, _config
        _config = pagure.config.reload_config()
        session = pagure.lib.model_base.create_session(_config["DB_URL"])

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
        print("Error: {0}".format(err))
        logging.exception("Generic error catched:")
        return_code = 2
    finally:
        session.remove()

    return return_code


if __name__ == "__main__":
    sys.exit(main())
