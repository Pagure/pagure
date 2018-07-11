#! /usr/bin/env python2


"""Pagure specific hook to add comment on issues if the commits fixes or
relates to an issue.
"""

from __future__ import print_function, unicode_literals

import logging
import os
import sys

import pygit2

from sqlalchemy.exc import SQLAlchemyError

if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pagure  # noqa: E402
import pagure.exceptions  # noqa: E402
import pagure.lib.link  # noqa: E402


_log = logging.getLogger(__name__)
_config = pagure.config.config

abspath = os.path.abspath(os.environ['GIT_DIR'])


def generate_revision_change_log(new_commits_list):

    print('Detailed log of new commits:\n\n')
    commitid = None
    for line in pagure.lib.git.read_git_lines(
            ['log', '--no-walk'] + new_commits_list + ['--'], abspath):
        if line.startswith('commit'):
            commitid = line.split('commit ')[-1]

        line = line.strip()
        session = pagure.lib.create_session(_config['DB_URL'])
        print('*', line)
        for relation in pagure.lib.link.get_relation(
                session,
                pagure.lib.git.get_repo_name(abspath),
                pagure.lib.git.get_username(abspath),
                pagure.lib.git.get_repo_namespace(abspath),
                line,
                'fixes',
                include_prs=True):
            if _config.get('HOOK_DEBUG', False):
                print(commitid, relation)
            fixes_relation(commitid, relation, session,
                           _config.get('APP_URL'))

        for issue in pagure.lib.link.get_relation(
                session,
                pagure.lib.git.get_repo_name(abspath),
                pagure.lib.git.get_username(abspath),
                pagure.lib.git.get_repo_namespace(abspath),
                line,
                'relates'):
            if _config.get('HOOK_DEBUG', False):
                print(commitid, issue)
            relates_commit(commitid, issue, session, _config.get('APP_URL'))

        session.close()


def relates_commit(commitid, issue, session, app_url=None):
    ''' Add a comment to an issue that this commit relates to it. '''

    url = '../%s' % commitid[:8]
    if app_url:
        if app_url.endswith('/'):
            app_url = app_url[:-1]
        project = issue.project.fullname
        if issue.project.is_fork:
            project = 'fork/%s' % project
        url = '%s/%s/c/%s' % (app_url, project, commitid[:8])

    comment = ''' Commit [%s](%s) relates to this ticket''' % (
        commitid[:8], url)

    user = os.environ.get(
        'GL_USER', pagure.lib.git.get_author_email(commitid, abspath))

    try:
        pagure.lib.add_issue_comment(
            session,
            issue=issue,
            comment=comment,
            user=user,
            ticketfolder=_config['TICKETS_FOLDER'],
        )
        session.commit()
    except pagure.exceptions.PagureException as err:
        print(err)
    except SQLAlchemyError as err:  # pragma: no cover
        session.rollback()
        _log.exception(err)


def fixes_relation(commitid, relation, session, app_url=None):
    ''' Add a comment to an issue or PR that this commit fixes it and update
    the status if the commit is in the master branch. '''

    url = '../c/%s' % commitid[:8]
    if app_url:
        if app_url.endswith('/'):
            app_url = app_url[:-1]
        project = relation.project.fullname
        if relation.project.is_fork:
            project = 'fork/%s' % project
        url = '%s/%s/c/%s' % (app_url, project, commitid[:8])

    comment = ''' Commit [%s](%s) fixes this %s''' % (
        commitid[:8], url, relation.isa)

    user = os.environ.get(
        'GL_USER', pagure.lib.git.get_author_email(commitid, abspath))

    try:
        if relation.isa == 'issue':
            pagure.lib.add_issue_comment(
                session,
                issue=relation,
                comment=comment,
                user=user,
                ticketfolder=_config['TICKETS_FOLDER'],
            )
        elif relation.isa == 'pull-request':
            pagure.lib.add_pull_request_comment(
                session,
                request=relation,
                commit=None,
                tree_id=None,
                filename=None,
                row=None,
                comment=comment,
                user=user,
                requestfolder=_config['REQUESTS_FOLDER'],
            )
        session.commit()
    except pagure.exceptions.PagureException as err:
        print(err)
    except SQLAlchemyError as err:  # pragma: no cover
        session.rollback()
        _log.exception(err)

    try:
        if relation.isa == 'issue':
            pagure.lib.edit_issue(
                session,
                relation,
                ticketfolder=_config['TICKETS_FOLDER'],
                user=user,
                status='Closed', close_status='Fixed')
        elif relation.isa == 'pull-request':
            pagure.lib.close_pull_request(
                session,
                relation,
                requestfolder=_config['REQUESTS_FOLDER'],
                user=user,
                merged=True)
        session.commit()
    except pagure.exceptions.PagureException as err:
        print(err)
    except SQLAlchemyError as err:  # pragma: no cover
        session.rollback()
        print('ERROR', err)
        _log.exception(err)


def run_as_post_receive_hook():

    for line in sys.stdin:
        if _config.get('HOOK_DEBUG', False):
            print(line)
        (oldrev, newrev, refname) = line.strip().split(' ', 2)

        if _config.get('HOOK_DEBUG', False):
            print('  -- Old rev')
            print(oldrev)
            print('  -- New rev')
            print(newrev)
            print('  -- Ref name')
            print(refname)

        # Retrieve the default branch
        repo_obj = pygit2.Repository(abspath)
        default_branch = None
        if not repo_obj.is_empty and not repo_obj.head_is_unborn:
            default_branch = repo_obj.head.shorthand

        # Skip all branch but the default one
        refname = refname.replace('refs/heads/', '')
        if refname != default_branch:
            continue

        if set(newrev) == set(['0']):
            print("Deleting a reference/branch, so we won't run the "
                  "pagure hook")
            return

        generate_revision_change_log(
            pagure.lib.git.get_revs_between(oldrev, newrev, abspath, refname))

    if _config.get('HOOK_DEBUG', False):
        print('ns  :', pagure.lib.git.get_repo_namespace(abspath))
        print('repo:', pagure.lib.git.get_repo_name(abspath))
        print('user:', pagure.lib.git.get_username(abspath))


def main(args):
    run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
