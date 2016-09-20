#! /usr/bin/env python2


"""Pagure specific hook to update tickets stored in the database based on
the information pushed in the tickets git repository.
"""

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


abspath = os.path.abspath(os.environ['GIT_DIR'])


def get_files_to_load(new_commits_list):

    print 'Files changed by new commits:\n'
    file_list = []
    new_commits_list.reverse()
    for commit in new_commits_list:
        if commit == new_commits_list[0]:
            filenames = pagure.lib.git.read_git_lines(
                ['diff-tree', '--no-commit-id', '--name-only', '-r', '--root',
                    commit], abspath)
        else:
            filenames = pagure.lib.git.read_git_lines(
                ['diff-tree', '--no-commit-id', '--name-only', '-r', commit],
                abspath)
        for line in filenames:
            if line.strip():
                file_list.append(line.strip())

    return file_list


def run_as_post_receive_hook():

    file_list = set()
    for line in sys.stdin:
        if pagure.APP.config.get('HOOK_DEBUG', False):
            print line
        (oldrev, newrev, refname) = line.strip().split(' ', 2)

        if pagure.APP.config.get('HOOK_DEBUG', False):
            print '  -- Old rev'
            print oldrev
            print '  -- New rev'
            print newrev
            print '  -- Ref name'
            print refname

        if set(newrev) == set(['0']):
            print "Deleting a reference/branch, so we won't run the "\
                "pagure hook"
            return

        tmp = set(get_files_to_load(
            pagure.lib.git.get_revs_between(oldrev, newrev, abspath, refname)))
        file_list = file_list.union(tmp)

    reponame = pagure.lib.git.get_repo_name(abspath)
    username = pagure.lib.git.get_username(abspath)
    namespace = pagure.lib.git.get_repo_namespace(
        abspath, gitfolder=pagure.APP.config['TICKETS_FOLDER'])
    print 'repo:', reponame, username, namespace

    for filename in file_list:
        print 'To load: %s' % filename
        json_data = None
        data = ''.join(
            pagure.lib.git.read_git_lines(
                ['show', 'HEAD:%s' % filename], abspath))
        if data and 'files' not in filename:
            try:
                json_data = json.loads(data)
            except:
                pass
        if json_data:
            pagure.lib.git.update_ticket_from_git(
                pagure.SESSION,
                reponame=reponame,
                namespace=namespace,
                username=username,
                issue_uid=filename,
                json_data=json_data)


def main(args):
    run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
