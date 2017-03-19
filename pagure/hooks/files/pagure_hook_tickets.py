#! /usr/bin/env python2


"""Pagure specific hook to update tickets stored in the database based on
the information pushed in the tickets git repository.
"""
from __future__ import print_function

import json
import os
import re
import sys
import subprocess


# We need to access the database
if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'

import pagure
import pagure.lib.git

from pagure.lib import REDIS


abspath = os.path.abspath(os.environ['GIT_DIR'])


def run_as_post_receive_hook():

    repo = pagure.lib.git.get_repo_name(abspath)
    username = pagure.lib.git.get_username(abspath)
    namespace = pagure.lib.git.get_repo_namespace(
        abspath, gitfolder=pagure.APP.config['TICKETS_FOLDER'])
    if pagure.APP.config.get('HOOK_DEBUG', False):
        print('repo:', repo)
        print('user:', username)
        print('namespace:', namespace)

    project = pagure.lib._get_project(
        pagure.SESSION, repo, user=username, namespace=namespace)

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

        if set(newrev) == set(['0']):
            print("Deleting a reference/branch, so we won't run the "
                  "pagure hook")
            return

        commits = pagure.lib.git.get_revs_between(
            oldrev, newrev, abspath, refname)

        if REDIS:
            print('Sending to redis to load the data')
            REDIS.publish('pagure.loadjson',
                    json.dumps({
                        'project': project.to_json(public=True),
                        'abspath': abspath,
                        'commits': commits,
                        'data_type': 'ticket',
                        'agent': os.environ.get('GL_USER'),
                    }
                    ))
            print(
                'A report will be emailed to you once the load is finished')
        else:
            print('Hook not configured to connect to pagure-loadjson')
            print('/!\ Your data will not be loaded into the database!')


def main(args):
    run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
