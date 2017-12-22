#! /usr/bin/env python2


"""Pagure specific hook to block non-fastforward pushes.
"""

from __future__ import print_function

import os
import sys


if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure  # noqa: E402
import pagure.exceptions  # noqa: E402
import pagure.lib.link  # noqa: E402
import pagure.lib.plugins  # noqa: E402


_config = pagure.config.config.reload_config()
abspath = os.path.abspath(os.environ['GIT_DIR'])


def run_as_pre_receive_hook():
    reponame = pagure.lib.git.get_repo_name(abspath)
    namespace = pagure.lib.git.get_repo_namespace(abspath)
    username = pagure.lib.git.get_username(abspath)
    if _config.get('HOOK_DEBUG', False):
        print('repo:     ', reponame)
        print('user:     ', username)
        print('namspaces:', namespace)

    repo = pagure.lib._get_project(
        pagure.SESSION, reponame, user=username, namespace=namespace,
        case=_config.get('CASE_SENSITIVE', False))

    if not repo:
        print('Unknown repo %s of username: %s in namespace %s' % (
            reponame, username, namespace))
        sys.exit(1)

    plugin = pagure.lib.plugins.get_plugin('Block non fast-forward pushes')
    plugin.db_object()
    # Get the list of branches
    branches = []
    if repo.pagure_force_commit_hook:
        branch.strip()
        for branch in repo.pagure_force_commit_hook.branches.split(',')
        if branch.strip()]

    for line in sys.stdin:
        if _config.get('HOOK_DEBUG', False):
            print(line)
        (oldrev, newrev, refname) = line.strip().split(' ', 2)

        refname = refname.replace('refs/heads/', '')
        if refname in branches or branches == ['*']:
            if _config.get('HOOK_DEBUG', False):
                print('  -- Old rev')
                print(oldrev)
                print('  -- New rev')
                print(newrev)
                print('  -- Ref name')
                print(refname)

            if set(newrev) == set(['0']):
                print("Deletion is forbidden")
                sys.exit(1)
            elif pagure.lib.git.is_forced_push(oldrev, newrev, abspath):
                print("Non fast-forward push are forbidden")
                sys.exit(1)


def main(args):
    run_as_pre_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
