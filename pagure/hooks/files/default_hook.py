#! /usr/bin/env python2


"""Pagure specific hook to be added to all projects in pagure by default.
"""
from __future__ import print_function

import os
import logging
import sys


if 'PAGURE_CONFIG' not in os.environ \
        and os.path.exists('/etc/pagure/pagure.cfg'):
    os.environ['PAGURE_CONFIG'] = '/etc/pagure/pagure.cfg'


import pygit2  # noqa: E402

import pagure  # noqa: E402
import pagure.flask_app  # noqa: E402
import pagure.exceptions  # noqa: E402
import pagure.lib.link  # noqa: E402
import pagure.lib.tasks  # noqa: E402
import pagure.lib.tasks_services  # noqa: E402


_config = pagure.config.reload_config()
_log = logging.getLogger(__name__)
abspath = os.path.abspath(os.environ['GIT_DIR'])


def send_fedmsg_notifications(project, topic, msg):
    ''' If the user asked for fedmsg notifications on commit, this will
    do it.
    '''
    import fedmsg
    config = fedmsg.config.load_config([], None)
    config['active'] = True
    config['endpoints']['relay_inbound'] = config['relay_inbound']
    fedmsg.init(name='relay_inbound', **config)

    pagure.lib.notify.log(
        project=project,
        topic=topic,
        msg=msg,
        redis=None,  # web-hook notification are handled separately
    )


def send_webhook_notifications(project, topic, msg):
    ''' If the user asked for webhook notifications on commit, this will
    do it.
    '''

    pagure.lib.tasks_services.webhook_notification.delay(
        topic=topic,
        msg=msg,
        namespace=project.namespace,
        name=project.name,
        user=project.user.username if project.is_fork else None,
    )


def send_notifications(session, project, refname, revs, forced):
    ''' Send out-going notifications about the commits that have just been
    pushed.
    '''

    auths = set()
    for rev in revs:
        email = pagure.lib.git.get_author_email(rev, abspath)
        name = pagure.lib.git.get_author(rev, abspath)
        author = pagure.lib.search_user(session, email=email) or name
        auths.add(author)

    authors = []
    for author in auths:
        if isinstance(author, basestring):
            author = author
        else:
            author = author.to_json(public=True)
        authors.append(author)

    if revs:
        revs.reverse()
        print("* Publishing information for %i commits" % len(revs))

        topic = 'git.receive'
        msg = dict(
            total_commits=len(revs),
            start_commit=revs[0],
            end_commit=revs[-1],
            branch=refname,
            forced=forced,
            authors=list(authors),
            agent=os.environ['GL_USER'],
            repo=project.to_json(public=True)
            if not isinstance(project, basestring) else project,
        )

        fedmsg_hook = pagure.lib.plugins.get_plugin('Fedmsg')
        fedmsg_hook.db_object()

        always_fedmsg = _config.get('ALWAYS_FEDMSG_ON_COMMITS') or None

        if always_fedmsg \
                or (project.fedmsg_hook and project.fedmsg_hook.active):
            try:
                print("  - to fedmsg")
                send_fedmsg_notifications(project, topic, msg)
            except Exception:
                _log.exception(
                    'Error sending fedmsg notifications on commit push')
        if project.settings.get('Web-hooks') and not project.private:
            try:
                print("  - to web-hooks")
                send_webhook_notifications(project, topic, msg)
            except Exception:
                _log.exception(
                    'Error sending web-hook notifications on commit push')

        if _config.get('PAGURE_CI_SERVICES') \
                and project.ci_hook \
                and project.ci_hook.active_commit \
                and not project.private:
            pagure.lib.tasks_services.trigger_ci_build.delay(
                project_name=project.fullname,
                cause=revs[-1],
                branch=refname,
                ci_type=project.ci_hook.ci_type
            )


def inform_pull_request_urls(
        session, project, commits, refname, default_branch):
    ''' Inform the user about the URLs to open a new pull-request or visit
    the existing one.
    '''
    target_repo = project
    if project.is_fork:
        target_repo = project.parent

    if commits and refname != default_branch\
            and target_repo.settings.get('pull_requests', True):
        print()
        prs = pagure.lib.search_pull_requests(
            session,
            project_id_from=project.id,
            status='Open',
            branch_from=refname,
        )
        # Link to existing PRs if there are any
        seen = len(prs) != 0
        for pr in prs:
            # Link tickets with pull-requests if the commit mentions it
            pagure.lib.tasks.link_pr_to_ticket.delay(pr.uid)

            # Inform the user about the PR
            print('View pull-request for %s' % refname)
            print('   %s/%s/pull-request/%s' % (
                _config['APP_URL'].rstrip('/'),
                pr.project.url_path,
                pr.id)
            )
        # If no existing PRs, provide the link to open one
        if not seen:
            print('Create a pull-request for %s' % refname)
            print('   %s/%s/diff/%s..%s' % (
                _config['APP_URL'].rstrip('/'),
                project.url_path,
                default_branch,
                refname)
            )
        print()


def run_as_post_receive_hook():

    repo = pagure.lib.git.get_repo_name(abspath)
    username = pagure.lib.git.get_username(abspath)
    namespace = pagure.lib.git.get_repo_namespace(abspath)
    if _config.get('HOOK_DEBUG', False):
        print('repo:', repo)
        print('user:', username)
        print('namespace:', namespace)

    session = pagure.lib.create_session(_config['DB_URL'])

    project = pagure.lib._get_project(
        session, repo, user=username, namespace=namespace,
        case=_config.get('CASE_SENSITIVE', False))

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

        forced = False
        if set(newrev) == set(['0']):
            print("Deleting a reference/branch, so we won't run the "
                  "pagure hook")
            return
        elif set(oldrev) == set(['0']):
            oldrev = '^%s' % oldrev
        elif pagure.lib.git.is_forced_push(oldrev, newrev, abspath):
            forced = True
            base = pagure.lib.git.get_base_revision(oldrev, newrev, abspath)
            if base:
                oldrev = base[0]

        refname = refname.replace('refs/heads/', '')
        commits = pagure.lib.git.get_revs_between(
            oldrev, newrev, abspath, refname)

        if refname == default_branch:
            print('Sending to redis to log activity and send commit '
                  'notification emails')
        else:
            print('Sending to redis to send commit notification emails')

        # This is logging the commit to the log table in the DB so we can
        # render commits in the calendar heatmap.
        # It is also sending emails about commits to people using the
        # 'watch' feature to be made aware of new commits.
        pagure.lib.tasks_services.log_commit_send_notifications.delay(
            name=repo,
            commits=commits,
            abspath=abspath,
            branch=refname,
            default_branch=default_branch,
            namespace=namespace,
            username=username,
        )

        # This one is sending fedmsg and web-hook notifications for project
        # that set them up
        send_notifications(session, project, refname, commits, forced)

        # Now display to the user if this isn't the default branch links to
        # open a new pr or review the existing one
        inform_pull_request_urls(
            session, project, commits, refname, default_branch)

    # Schedule refresh of all opened PRs
    parent = project.parent or project
    pagure.lib.tasks.refresh_pr_cache.delay(
        parent.name,
        parent.namespace,
        parent.user.user if parent.is_fork else None
    )

    session.remove()


def main(args):
    run_as_post_receive_hook()


if __name__ == '__main__':
    main(sys.argv[1:])
