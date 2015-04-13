#! /usr/bin/env python2


"""Pagure specific hook to update pull-requests stored in the database
based on the information pushed in the requests git repository.
"""

import json
import os
import re
import sys
import subprocess


# We need to access the database
if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    print 'Using configuration file `/etc/pagure/pagure.cfg`'
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'

sys.path.insert(0, os.path.expanduser('~/repos/gitrepo/pagure'))

import pagure.lib.git


def read_git_output(args, input=None, keepends=False, **kw):
    """Read the output of a Git command."""

    return read_output(['git'] + args, input=input, keepends=keepends, **kw)


def read_git_lines(args, keepends=False, **kw):
    """Return the lines output by Git command.

    Return as single lines, with newlines stripped off."""

    return read_git_output(args, keepends=True, **kw).splitlines(keepends)


def read_output(cmd, input=None, keepends=False, **kw):
    if input:
        stdin = subprocess.PIPE
    else:
        stdin = None
    p = subprocess.Popen(
        cmd, stdin=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kw
        )
    (out, err) = p.communicate(input)
    retcode = p.wait()
    if retcode:
        print 'ERROR: %s =-- %s' % (cmd, retcode)
    if not keepends:
        out = out.rstrip('\n\r')
    return out


def get_files_to_load(new_commits_list):

    print 'Files changed by new commits:\n'
    file_list = []
    new_commits_list.reverse()
    for commit in new_commits_list:
        filenames = read_git_lines(
            ['diff-tree', '--no-commit-id', '--name-only', '-r', commit],
            keepends=False)
        for line in filenames:
            if line.strip():
                file_list.append(line.strip())

    return file_list


def get_commits_id(fromrev, torev):
    ''' Retrieve the list commit between two revisions and return the list
    of their identifier.
    '''
    cmd = ['rev-list', '%s...%s' % (torev, fromrev)]
    if set(fromrev) == set('0'):
        cmd = ['rev-list', '%s' % torev]
    output = read_git_lines(cmd)
    return output


def get_repo_name():
    ''' Return the name of the git repo based on its path.
    '''
    repo = os.path.basename(os.getcwd()).split('.git')[0]
    return repo


def get_username():
    ''' Return the username of the git repo based on its path.
    '''
    username = None
    repo = os.path.abspath(os.path.join(os.getcwd(), '..'))
    if pagure.APP.config['REQUESTS_FOLDER'] in repo:
        username = repo.split(pagure.APP.config['REQUESTS_FOLDER'])[1]
    return username


def run_as_post_receive_hook():

    file_list = set()
    for line in sys.stdin:
        print line
        (oldrev, newrev, refname) = line.strip().split(' ', 2)

        print '  -- Old rev'
        print oldrev
        print '  -- New rev'
        print newrev
        print '  -- Ref name'
        print refname

        tmp = set(get_files_to_load(get_commits_id(oldrev, newrev)))
        file_list = file_list.union(tmp)

    reponame = get_repo_name()
    username = get_username()
    print 'repo:', reponame, username

    for filename in file_list:
        print 'To load: %s' % filename
        data = ''.join(read_git_lines(['show', 'HEAD:%s' % filename]))
        if data:
            data = json.loads(data)
        if data:
            pagure.lib.git.update_request_from_git(
                pagure.SESSION,
                reponame=reponame,
                username=username,
                request_uid=filename,
                json_data=data,
                gitfolder=pagure.APP.config['GIT_FOLDER'],
                forkfolder=pagure.APP.config['FORK_FOLDER'],
                docfolder=pagure.APP.config['DOCS_FOLDER'],
                ticketfolder=pagure.APP.config['TICKETS_FOLDER'],
                requestfolder=pagure.APP.config['REQUESTS_FOLDER'],
            )


def main(args):
    run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
