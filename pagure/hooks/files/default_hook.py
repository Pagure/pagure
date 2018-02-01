#! /usr/bin/env python2


"""Pagure specific hook to be added to all projects in pagure by default.
"""
from __future__ import print_function

import json
import os
import sys

import pygit2

import pagure  # noqa: E402
import pagure.flask_app  # noqa: E402
import pagure.exceptions  # noqa: E402
import pagure.lib.link  # noqa: E402
import pagure.lib.tasks  # noqa: E402

from pagure.lib import REDIS  # noqa: E402


if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


_config = pagure.config.config.reload_config()
abspath = os.path.abspath(os.environ['GIT_DIR'])


def run_as_post_receive_hook():

    repo = pagure.lib.git.get_repo_name(abspath)
    username = pagure.lib.git.get_username(abspath)
    namespace = pagure.lib.git.get_repo_namespace(abspath)
    if _config.get('HOOK_DEBUG', False):
        print('repo:', repo)
        print('user:', username)
        print('namespace:', namespace)

    project = pagure.lib._get_project(
        pagure.SESSION, repo, user=username, namespace=namespace,
        case=_config.get('CASE_SENSITIVE', False))

    for line in sys.stdin:
        if _config.get('HOOK_DEBUG', False):
            print(line)
        (oldrev, newrev, refname) = line.strip().split(' ', 2)

        if _config.get('HOOK_DEBUG', False):
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

        target_repo = project
        if project.is_fork:
            target_repo = project.parent

        if commits and refname != default_branch\
                and target_repo.settings.get('pull_requests', True):
            print()
            prs = pagure.lib.search_pull_requests(
                pagure.flask_app.SESSION,
                project_id_from=project.id,
                status='Open',
                branch_from=refname,
            )
            # Link to existing PRs if there are any
            seen = len(prs) != 0
            for pr in prs:
                print('View pull-request for %s' % refname)
                print('   %s/%s/pull-request/%s' % (
                    _config['APP_URL'].rstrip('/'),
                    pr.project.url_path,
                    pr.id)
                )
            # If no existing PRs, provide the link to open one
            if not seen:
                print('Create a pull-request for %s' % refname)
                print('   %s/%s/diff/%s..%s' % (
                    _config['APP_URL'].rstrip('/'),
                    project.url_path,
                    default_branch,
                    refname)
                )
            print()

    # Schedule refresh of all opened PRs
    parent = project.parent or project
    pagure.lib.tasks.refresh_pr_cache.delay(
        parent.name,
        parent.namespace,
        parent.user.user if parent.is_fork else None
    )

    pagure.SESSION.remove()


def main(args):
    run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
