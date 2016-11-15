#! /usr/bin/env python2


"""Pagure specific hook to trigger a build on a readthedocs.org project.
"""

import os
import sys

import requests

from sqlalchemy.exc import SQLAlchemyError


if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure
import pagure.exceptions
import pagure.lib.link
import pagure.lib.plugins


abspath = os.path.abspath(os.environ['GIT_DIR'])


def run_as_post_receive_hook():
    reponame = pagure.lib.git.get_repo_name(abspath)
    username = pagure.lib.git.get_username(abspath)
    namespace = pagure.lib.git.get_repo_namespace(abspath)
    if pagure.APP.config.get('HOOK_DEBUG', False):
        print 'repo:     ', reponame
        print 'user:     ', username
        print 'namespace:', namespace

    repo = pagure.lib._get_project(pagure.SESSION, reponame, user=username, namespace=namespace)
    if not repo:
        print 'Unknown repo %s of username: %s' % (reponame, username)
        sys.exit(1)

    plugin = pagure.lib.plugins.get_plugin('Read the Doc')
    dbobj = plugin.db_object()
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
        if pagure.APP.config.get('HOOK_DEBUG', False):
            print line
        (oldrev, newrev, refname) = line.strip().split(' ', 2)

        refname = refname.replace('refs/heads/', '')
        if branches:
            if refname in branches:
                print 'Starting RTD build for %s' % (
                    repo.rtd_hook.project_name.strip())
                requests.post(url)
        else:
            print 'Starting RTD build for %s' % (
                repo.rtd_hook.project_name.strip())
            requests.post(url)


def main(args):
    run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
