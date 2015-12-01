#! /usr/bin/env python2


"""Pagure specific hook to add comment on issues if the commits fixes or
relates to an issue.
"""

import os
import re
import sys
import subprocess

from sqlalchemy.exc import SQLAlchemyError

if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure
import pagure.exceptions
import pagure.lib.link


abspath = os.path.abspath(os.environ['GIT_DIR'])


def generate_revision_change_log(new_commits_list):

    print 'Detailed log of new commits:\n\n'
    commitid = None
    for line in pagure.lib.git.read_git_lines(
            ['log', '--no-walk'] + new_commits_list + ['--'], abspath):
        if line.startswith('commit'):
            commitid = line.split('commit ')[-1]

        line = line.strip()

        print '*', line
        for issue in pagure.lib.link.get_relation(
                pagure.SESSION,
                pagure.lib.git.get_repo_name(abspath),
                pagure.lib.git.get_username(abspath),
                line,
                'fixes'):
            fixes_commit(commitid, issue, pagure.APP.config.get('APP_URL'))

        for issue in pagure.lib.link.get_relation(
                pagure.SESSION,
                pagure.lib.git.get_repo_name(abspath),
                pagure.lib.git.get_username(abspath),
                line,
                'relates'):
            relates_commit(commitid, issue, pagure.APP.config.get('APP_URL'))


def relates_commit(commitid, issue, app_url=None):
    ''' Add a comment to an issue that this commit relates to it. '''

    url = '../%s' % commitid[:8]
    if app_url:
        if app_url.endswith('/'):
            app_url = app_url[:-1]
        project = issue.project.path.split('.git')[0]
        if issue.project.is_fork:
            project = 'fork/%s' % project
        url = '%s/%s/%s' % (app_url, project, commitid[:8])

    comment = ''' Commit [%s](%s) relates to this ticket''' % (
        commitid[:8], url)

    try:
        message = pagure.lib.add_issue_comment(
            pagure.SESSION,
            issue=issue,
            comment=comment,
            user=pagure.lib.git.get_pusher_email(commitid, abspath),
            ticketfolder=pagure.APP.config['TICKETS_FOLDER'],
        )
        pagure.SESSION.commit()
    except pagure.exceptions.PagureException as err:
        print err
    except SQLAlchemyError as err:  # pragma: no cover
        pagure.SESSION.rollback()
        pagure.APP.logger.exception(err)


def fixes_commit(commitid, issue, app_url=None):
    ''' Add a comment to an issue that this commit fixes it and update
    the status if the commit is in the master branch. '''

    url = '../%s' % commitid[:8]
    if app_url:
        if app_url.endswith('/'):
            app_url = app_url[:-1]
        project = issue.project.path.split('.git')[0]
        if issue.project.is_fork:
            project = 'fork/%s' % project
        url = '%s/%s/%s' % (app_url, project, commitid[:8])

    comment = ''' Commit [%s](%s) fixes this ticket''' % (
        commitid[:8], url)

    try:
        message = pagure.lib.add_issue_comment(
            pagure.SESSION,
            issue=issue,
            comment=comment,
            user=pagure.lib.git.get_pusher_email(commitid, abspath),
            ticketfolder=pagure.APP.config['TICKETS_FOLDER'],
        )
        pagure.SESSION.commit()
    except pagure.exceptions.PagureException as err:
        print err
    except SQLAlchemyError as err:  # pragma: no cover
        pagure.SESSION.rollback()
        pagure.APP.logger.exception(err)

    branches = [
        item.replace('* ', '')
        for item in pagure.lib.git.read_git_lines(
            ['branch', '--contains', commitid], abspath)
    ]

    if 'master' in branches:
        try:
            pagure.lib.edit_issue(
                pagure.SESSION,
                issue,
                ticketfolder=pagure.APP.config['TICKETS_FOLDER'],
                user=pagure.lib.git.get_pusher_email(commitid, abspath),
                status='Fixed')
            pagure.SESSION.commit()
        except pagure.exceptions.PagureException as err:
            print err
        except SQLAlchemyError as err:  # pragma: no cover
            pagure.SESSION.rollback()
            pagure.APP.logger.exception(err)


def run_as_post_receive_hook():

    changes = []
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

        generate_revision_change_log(
            pagure.lib.git.get_revs_between(oldrev, newrev, abspath))

    if pagure.APP.config.get('HOOK_DEBUG', False):
        print 'repo:', pagure.lib.git.get_repo_name(abspath)
        print 'user:', pagure.lib.git.get_username(abspath)


def main(args):
        run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
