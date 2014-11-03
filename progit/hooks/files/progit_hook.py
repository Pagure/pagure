#! /usr/bin/env python2


"""Progit specific hook to add comment on issues if the commits fixes or
relates to an issue.
"""

import os
import re
import sys
import subprocess


if 'PROGIT_CONFIG' not in os.environ \
        and os.path.exists('/etc/progit/progit.cfg'):
    print 'Using configuration file `/etc/progit/progit.cfg`'
    os.environ['PROGIT_CONFIG'] = '/etc/progit/progit.cfg'


import progit
import progit.exceptions


FIXES = [
    re.compile('fixe?[sd]?:?\s?#(\d+)', re.I),
    re.compile('.*\s+fixe?[sd]?:?\s?#(\d+)', re.I),
    re.compile('fixe?[sd]?:?\s?https?://.*/(\w+)/issue/(\d+)', re.I),
    re.compile('.*\s+fixe?[sd]?:?\s?https?://.*/(\w+)/issue/(\d+)', re.I),
]

RELATES = [
    re.compile('relate[sd]?:?\s?(to)?\s?#(\d+)', re.I),
    re.compile('.*\s+relate[sd]?:?\s?#(\d+)', re.I),
    re.compile('relate[sd]?:?\s?(to)?\s?https?://.*/(\w+)/issue/(\d+)', re.I),
    re.compile('.*\s+relate[sd]?:?\s?https?://.*/(\w+)/issue/(\d+)', re.I),
]

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


def generate_revision_change_log(new_commits_list):

    print 'Detailed log of new commits:\n\n'
    commitid = None
    for line in read_git_lines(
            ['log', '--no-walk']
            + new_commits_list
            + ['--'],
            keepends=False,
        ):
        if line.startswith('commit'):
            commitid = line.split('commit ')[-1]

        line = line.strip()

        print '*', line
        for motif in FIXES:
            if motif.match(line):
                print 'fixes', motif.match(line).groups()
                project = None
                if len(motif.match(line).groups()) > 2:
                    project = motif.match(line).group(2)
                fixes_commit(
                    commitid, motif.match(line).group(1), project
                )
        for motif in RELATES:
            if motif.match(line):
                print 'relates to', motif.match(line).groups()
                project = None
                if len(motif.match(line).groups()) > 2:
                    project = motif.match(line).group(2)
                relates_commit(
                    commitid, motif.match(line).group(1), project
                )


def relates_commit(commitid, issueid, project=None):
    ''' Add a comment to an issue that this commit relates to it. '''
    repo = project or get_repo_name()
    username = get_username()
    print 'username:', username

    issue = progit.lib.get_issue(progit.SESSION, repo.id, issueid)

    if issue is None or issue.project.name != repo:
        return

    comment = ''' Commit `%s <../%s>`_ relates to this ticket''' % (
        commitid[:8], commitid[:8])

    try:
        message = progit.lib.add_issue_comment(
            progit.SESSION,
            issue=issue,
            comment=comment,
            user=get_pusher(commitid),
        )
        progit.SESSION.commit()
    except progit.exceptions.ProgitException as err:
        print err


def fixes_commit(commitid, issueid, project=None):
    ''' Add a comment to an issue that this commit fixes it and update
    the status if the commit is in the master branch. '''
    issue = progit.lib.get_issue(progit.SESSION, issueid)

    repo = project or get_repo_name()

    if issue is None or issue.project.name != repo:
        return

    comment = ''' Commit `%s <../%s>`_ fixes this ticket''' % (
        commitid[:8], commitid[:8])

    try:
        message = progit.lib.add_issue_comment(
            progit.SESSION,
            issue=issue,
            comment=comment,
            user=get_pusher(commitid),
        )
        progit.SESSION.commit()
    except progit.exceptions.ProgitException as err:
        print err

    branches = [
        item.replace('* ', '') for item in read_git_lines(
            ['branch', '--contains', commitid],
            keepends=False)
    ]

    if 'master' in branches:
        try:
            progit.lib.edit_issue(progit.SESSION, issue, status='Fixed')
            progit.SESSION.commit()
        except progit.exceptions.ProgitException as err:
            print err


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


def get_username():
    ''' Return the username of the git repo based on its path.
    '''
    username = None
    repo = os.path.abspath(os.path.join(os.getcwd(), '..'))
    if progit.APP.config['FORK_FOLDER'] in repo:
        username = repo.split(progit.APP.config['FORK_FOLDER'])[1]
    return username


def get_pusher(commit):
    ''' Return the name of the person that pushed the commit. '''
    user = None
    output = read_git_lines(
        ['show', '--pretty=format:"%ae"', commit], keepends=False)
    if output:
        user = output[0].replace('"', '')
    if not user:
        user = os.environ.get('GL_USER', os.environ.get('USER', None))
    return user


def run_as_post_receive_hook():

    changes = []
    for line in sys.stdin:
        print line
        (oldrev, newrev, refname) = line.strip().split(' ', 2)

        print '  -- Old rev'
        print oldrev
        print '  -- New rev'
        print newrev
        print '  -- Ref name'
        print refname

        generate_revision_change_log(get_commits_id(oldrev, newrev))

    print 'repo:', get_repo_name()


def main(args):
        run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
