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
import progit.lib.link


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
            keepends=False,):
        if line.startswith('commit'):
            commitid = line.split('commit ')[-1]

        line = line.strip()

        print '*', line
        for issue in progit.lib.link.get_relation(
                progit.SESSION, get_repo_name(), get_username(),
                line, 'fixes'):
            fixes_commit(commitid, issue, progit.APP.config.get('APP_URL'))

        for issue in progit.lib.link.get_relation(
                progit.SESSION, get_repo_name(), get_username(),
                line, 'relates'):
            relates_commit(commitid, issue, progit.APP.config.get('APP_URL'))


def relates_commit(commitid, issue, app_url=None):
    ''' Add a comment to an issue that this commit relates to it. '''

    url = '../%s' % commitid[:8]
    if app_url:
        if app_url.endswith('/'):
            app_url = app_url[:-1]
        url = '%s/%s/%s' % (
            app_url, issue.project.path.split('.git')[0], commitid[:8])

    comment = ''' Commit [%s](%s) relates to this ticket''' % (
        commitid[:8], url)

    try:
        message = progit.lib.add_issue_comment(
            progit.SESSION,
            issue=issue,
            comment=comment,
            user=get_pusher(commitid),
            ticketfolder=progit.APP.config['TICKETS_FOLDER'],
        )
        progit.SESSION.commit()
    except progit.exceptions.ProgitException as err:
        print err
    except SQLAlchemyError, err:  # pragma: no cover
        progit.SESSION.rollback()
        progit.APP.logger.exception(err)


def fixes_commit(commitid, issue, app_url=None):
    ''' Add a comment to an issue that this commit fixes it and update
    the status if the commit is in the master branch. '''

    url = '../%s' % commitid[:8]
    if app_url:
        if app_url.endswith('/'):
            app_url = app_url[:-1]
        url = '%s/%s/%s' % (
            app_url, issue.project.path.split('.git')[0], commitid[:8])

    comment = ''' Commit [%s](%s) fixes this ticket''' % (
        commitid[:8], url)

    try:
        message = progit.lib.add_issue_comment(
            progit.SESSION,
            issue=issue,
            comment=comment,
            user=get_pusher(commitid),
            ticketfolder=progit.APP.config['TICKETS_FOLDER'],
        )
        progit.SESSION.commit()
    except progit.exceptions.ProgitException as err:
        print err
    except SQLAlchemyError, err:  # pragma: no cover
        progit.SESSION.rollback()
        progit.APP.logger.exception(err)

    branches = [
        item.replace('* ', '') for item in read_git_lines(
            ['branch', '--contains', commitid],
            keepends=False)
    ]

    if 'master' in branches:
        try:
            progit.lib.edit_issue(
                progit.SESSION,
                issue,
                ticketfolder=progit.APP.config['TICKETS_FOLDER'],
                status='Fixed')
            progit.SESSION.commit()
        except progit.exceptions.ProgitException as err:
            print err
        except SQLAlchemyError, err:  # pragma: no cover
            progit.SESSION.rollback()
            progit.APP.logger.exception(err)


def get_commits_id(fromrev, torev):
    ''' Retrieve the list commit between two revisions and return the list
    of their identifier.
    '''
    cmd = ['rev-list', '%s...%s' % (torev, fromrev)]
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
    print 'user:', get_username()


def main(args):
        run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
