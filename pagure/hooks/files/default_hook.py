#! /usr/bin/env python2


"""Pagure specific hook to be added to all projects in pagure by default.
"""
from __future__ import print_function

import json
import os
import sys

import pygit2

from sqlalchemy.exc import SQLAlchemyError

if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure  # noqa: E402
import pagure.exceptions  # noqa: E402
import pagure.lib.link  # noqa: E402

from pagure.lib import REDIS  # noqa: E402


abspath = os.path.abspath(os.environ['GIT_DIR'])


def run_as_post_receive_hook():

    repo = pagure.lib.git.get_repo_name(abspath)
    username = pagure.lib.git.get_username(abspath)
    namespace = pagure.lib.git.get_repo_namespace(abspath)
    if pagure.APP.config.get('HOOK_DEBUG', False):
        print('repo:', repo)
        print('user:', username)
        print('namespace:', namespace)

    project = pagure.lib._get_project(
        pagure.SESSION, repo, user=username, namespace=namespace,
        with_lock=True)

    for line in sys.stdin:
        if pagure.APP.config.get('HOOK_DEBUG', False):
            print(line)
        (oldrev, newrev, refname) = line.strip().split(' ', 2)

        if pagure.APP.config.get('HOOK_DEBUG', False):
            print('  -- Old rev')
            print(oldrev)
            print('  -- New rev')
            print(newrev)
            print('  -- Ref name')
            print(refname)

        # Retrieve the default branch
        repo_obj = pygit2.Repository(abspath)
        default_branch = None
        if not repo_obj.is_empty and not repo_obj.head_is_unborn:
            default_branch = repo_obj.head.shorthand

        if set(newrev) == set(['0']):
            print("Deleting a reference/branch, so we won't run the "
                  "pagure hook")
            return

        refname = refname.replace('refs/heads/', '')
        commits = pagure.lib.git.get_revs_between(
            oldrev, newrev, abspath, refname)

        if REDIS:
            if refname == default_branch:
                print('Sending to redis to log activity and send commit '
                      'notification emails')
            else:
                print('Sending to redis to send commit notification emails')
            # If REDIS is enabled, notify subscribed users that there are new
            # commits to this project
            REDIS.publish(
                'pagure.logcom',
                json.dumps({
                    'project': project.to_json(public=True),
                    'abspath': abspath,
                    'branch': refname,
                    'default_branch': default_branch,
                    'commits': commits,
                })
            )
        else:
            print('Hook not configured to connect to pagure-logcom')
            print('/!\ Commit notification emails will not be sent and '
                  'commits won\'t be logged')

    try:
        # Reset the merge_status of all opened PR to refresh their cache
        pagure.lib.reset_status_pull_request(pagure.SESSION, project)
        pagure.SESSION.commit()
    except SQLAlchemyError as err:  # pragma: no cover
        pagure.SESSION.rollback()
        print(err)
        print('An error occured while running the default hook, please '
              'report it to an admin.')

    pagure.SESSION.remove()


def main(args):
    run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
