#! /usr/bin/env python2


"""Pagure specific hook to trigger a build on a readthedocs.org project.
"""

from __future__ import print_function, unicode_literals

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

_config = pagure.config.config
abspath = os.path.abspath(os.environ['GIT_DIR'])


def run_as_post_receive_hook():
    reponame = pagure.lib.git.get_repo_name(abspath)
    username = pagure.lib.git.get_username(abspath)
    namespace = pagure.lib.git.get_repo_namespace(abspath)
    session = pagure.lib.create_session(_config['DB_URL'])
    if _config.get('HOOK_DEBUG', False):
        print('repo:     ', reponame)
        print('user:     ', username)
        print('namespace:', namespace)

    repo = pagure.lib.get_authorized_project(
        session, reponame, user=username, namespace=namespace)
    if not repo:
        print('Unknown repo %s of username: %s' % (reponame, username))
        session.close()
        sys.exit(1)

    hook = pagure.lib.plugins.get_plugin('Read the Doc')
    hook.db_object()

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

    url = repo.rtd_hook.api_url
    if not url:
        print('No API url specified to trigger the build, please update '
              'the configuration')
        session.close()
        return 1
    if not repo.rtd_hook.api_token:
        print('No API token specified to trigger the build, please update '
              'the configuration')
        session.close()
        return 1

    for line in sys.stdin:
        if _config.get('HOOK_DEBUG', False):
            print(line)
        (oldrev, newrev, refname) = line.strip().split(' ', 2)

        refname = refname.replace('refs/heads/', '')
        if branches:
            if refname in branches:
                print('Starting RTD build at %s' % (url))
                requests.post(
                    url,
                    data={
                        'branches': refname,
                        'token': repo.rtd_hook.api_token
                    },
                    timeout=60,
                )
        else:
            print('Starting RTD build at %s' % (url))
            requests.post(
                url,
                data={
                    'branches': refname,
                    'token': repo.rtd_hook.api_token
                },
                timeout=60,
            )

    session.close()


def main(args):
    run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
