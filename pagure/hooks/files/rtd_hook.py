#! /usr/bin/env python2


"""Pagure specific hook to trigger a build on a readthedocs.org project.
"""

from __future__ import print_function

import os
import sys

import requests


if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure  # noqa: E402
import pagure.exceptions  # noqa: E402
import pagure.lib.link  # noqa: E402
import pagure.lib.plugins  # noqa: E402


_config = pagure.config.config.reload_config()
abspath = os.path.abspath(os.environ['GIT_DIR'])


def run_as_post_receive_hook():
    reponame = pagure.lib.git.get_repo_name(abspath)
    username = pagure.lib.git.get_username(abspath)
    namespace = pagure.lib.git.get_repo_namespace(abspath)
    if _config.get('HOOK_DEBUG', False):
        print('repo:     ', reponame)
        print('user:     ', username)
        print('namespace:', namespace)

    repo = pagure.lib.get_authorized_project(
        pagure.SESSION, reponame, user=username, namespace=namespace)
    if not repo:
        print('Unknown repo %s of username: %s' % (reponame, username))
        sys.exit(1)

    pagure.lib.plugins.get_plugin('Read the Doc')
    # Get the list of branches
    branches = [
        branch.strip()
        for branch in repo.rtd_hook.branches.split(',')
        if repo.rtd_hook]

    # Remove empty branches
    branches = [
        branch.strip()
        for branch in branches
        if branch]

    url = 'http://readthedocs.org/build/%s' % (
        repo.rtd_hook.project_name.strip()
    )

    for line in sys.stdin:
        if _config.get('HOOK_DEBUG', False):
            print(line)
        (oldrev, newrev, refname) = line.strip().split(' ', 2)

        refname = refname.replace('refs/heads/', '')
        if branches:
            if refname in branches:
                print('Starting RTD build for %s' % (
                      repo.rtd_hook.project_name.strip()))
                requests.post(url)
        else:
            print('Starting RTD build for %s' % (
                  repo.rtd_hook.project_name.strip()))
            requests.post(url)


def main(args):
    run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
