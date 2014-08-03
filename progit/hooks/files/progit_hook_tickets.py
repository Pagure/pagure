#! /usr/bin/env python2


"""Progit specific hook to update tickets stored in the database based on
the information pushed in the tickets git repository.
"""

import os
import re
import sys
import subprocess


# We need to access the database
if 'PROGIT_CONFIG' not in os.environ \
        and os.path.exists('/etc/progit/progit.cfg'):
    print 'Using configuration file `/etc/progit/progit.cfg`'
    os.environ['PROGIT_CONFIG'] = '/etc/progit/progit.cfg'

sys.path.insert(0, os.path.expanduser('~/repos/gitrepo/progit'))


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

    print 'Files changed by new commits:\n\n'
    file_list = []
    for line in read_git_lines(
            ['show', '--pretty="format:"', '--name-only', '-r']
            + new_commits_list,
            keepends=False,
        ):
        if line.strip():
            file_list.append(line.strip())

    return file_list


def get_commits_id(fromrev, torev):
    ''' Retrieve the list commit between two revisions and return the list
    of their identifier.
    '''
    cmd = ['rev-list', '%s...%s' %(torev, fromrev)]
    return read_git_lines(cmd)


def get_repo_name():
    ''' Return the name of the git repo based on its path.
    '''
    repo = os.path.basename(os.getcwd()).split('.git')[0]
    return repo


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

        file_list.union(
            set(get_files_to_load(get_commits_id(oldrev, newrev))))

    for filename in file_list:
        print 'To load: %s' % filename

    print 'repo:', get_repo_name()


def main(args):
        run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
