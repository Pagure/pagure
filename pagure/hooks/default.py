# -*- coding: utf-8 -*-

"""
 (c) 2016-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import absolute_import, print_function, unicode_literals

import logging

import pygit2
import six

import pagure.config
import pagure.exceptions
import pagure.lib.query
import pagure.lib.tasks
import pagure.lib.tasks_services
import pagure.utils
from pagure.hooks import BaseHook, BaseRunner

_config = pagure.config.reload_config()
_log = logging.getLogger(__name__)


FEDMSG_INIT = False


def send_fedmsg_notifications(project, topic, msg):
    """If the user or admin asked for fedmsg notifications on commit, this will
    do it.
    """

    fedmsg_hook = pagure.lib.plugins.get_plugin("Fedmsg")
    fedmsg_hook.db_object()

    always_fedmsg = _config.get("ALWAYS_FEDMSG_ON_COMMITS") or None

    # Send fedmsg and fedora-messaging notification
    # (if fedmsg and fedora-messaging are there and set-up)
    if always_fedmsg or (project.fedmsg_hook and project.fedmsg_hook.active):
        if _config.get("FEDMSG_NOTIFICATIONS", True):
            try:
                global FEDMSG_INIT
                print("  - to fedmsg")
                import fedmsg

                config = fedmsg.config.load_config([], None)
                config["active"] = True
                config["endpoints"]["relay_inbound"] = config["relay_inbound"]
                if not FEDMSG_INIT:
                    fedmsg.init(name="relay_inbound", **config)
                    FEDMSG_INIT = True

                pagure.lib.notify.fedmsg_publish(topic=topic, msg=msg)
            except Exception:
                _log.exception(
                    "Error sending fedmsg notifications on commit push"
                )

        if _config.get("FEDORA_MESSAGING_NOTIFICATIONS", False):
            try:
                print("  - to fedora-message")
                pagure.lib.notify.fedora_messaging_publish(topic, msg)
            except Exception:
                _log.exception(
                    "Error sending fedora-messaging notifications on "
                    "commit push"
                )


def send_stomp_notifications(project, topic, msg):
    """If the user or admin asked for stomp notifications on commit, this will
    do it.
    """
    always_stomp = _config.get("ALWAYS_STOMP_ON_COMMITS") or None
    # Send stomp notification (if stomp is there and set-up)
    if always_stomp or (project.fedmsg_hook and project.fedmsg_hook.active):
        try:
            print("  - to stomp")
            pagure.lib.notify.stomp_publish(topic, msg)
        except Exception:
            _log.exception("Error sending stomp notifications on commit push")


def send_mqtt_notifications(project, topic, msg):
    """If the user or admin asked for mqtt notifications on commit, this will
    do it.
    """
    always_mqtt = _config.get("ALWAYS_MQTT_ON_COMMITS") or None
    # Send mqtt notification (if mqtt is there and set-up)
    if always_mqtt or (project.fedmsg_hook and project.fedmsg_hook.active):
        try:
            print("  - to mqtt")
            pagure.lib.notify.mqtt_publish(topic, msg)
        except Exception:
            _log.exception("Error sending stomp notifications on commit push")


def send_webhook_notifications(project, topic, msg):
    """If the user asked for webhook notifications on commit, this will
    do it.
    """
    if project.settings.get("Web-hooks"):
        try:
            print("  - to web-hooks")
            pagure.lib.tasks_services.webhook_notification.delay(
                topic=topic,
                msg=msg,
                namespace=project.namespace,
                name=project.name,
                user=project.user.username if project.is_fork else None,
            )
        except Exception:
            _log.exception(
                "Error sending web-hook notifications on commit push"
            )


def send_action_notification(
    session, subject, action, project, repodir, user, refname, rev
):
    """Send out-going notifications about the branch/tag."""
    email = pagure.lib.git.get_author_email(rev, repodir)
    name = pagure.lib.git.get_author(rev, repodir)
    author = pagure.lib.query.search_user(session, email=email) or name
    if not isinstance(author, six.string_types):
        author = author.to_json(public=True)
    else:
        author = {
            "fullname": author,
            "name": None,
            "url_path": None,
        }

    topic = "git.%s.%s" % (subject, action)
    msg = dict(
        authors=[author],
        agent=user,
        repo=project.to_json(public=True)
        if not isinstance(project, six.string_types)
        else project,
    )
    if subject == "branch":
        msg["branch"] = refname
        msg["rev"] = rev
    elif subject == "tag":
        msg["tag"] = refname
        msg["rev"] = rev

    # Send blink notification to any 3rd party plugins, if there are any
    pagure.lib.notify.blinker_publish(topic, msg)

    if not project.private:
        send_fedmsg_notifications(project, topic, msg)
        send_stomp_notifications(project, topic, msg)
        send_mqtt_notifications(project, topic, msg)
        send_webhook_notifications(project, topic, msg)


def send_notifications(
    session, project, repodir, user, refname, revs, forced, oldrev
):
    """Send out-going notifications about the commits that have just been
    pushed.
    """

    auths = set()
    for rev in revs:
        email = pagure.lib.git.get_author_email(rev, repodir)
        name = pagure.lib.git.get_author(rev, repodir)
        author = pagure.lib.query.search_user(session, email=email) or name
        auths.add(author)

    authors = []
    for author in auths:
        if not isinstance(author, six.string_types):
            author = author.to_json(public=True)
        else:
            author = {
                "fullname": author,
                "name": None,
                "url_path": None,
            }
        authors.append(author)

    if revs:
        revs.reverse()
        print("* Publishing information for %i commits" % len(revs))

        topic = "git.receive"
        msg = dict(
            total_commits=len(revs),
            start_commit=revs[0],
            end_commit=revs[-1],
            old_commit=oldrev,
            branch=refname,
            forced=forced,
            authors=list(authors),
            agent=user,
            repo=project.to_json(public=True)
            if not isinstance(project, six.string_types)
            else project,
        )

        # Send blink notification to any 3rd party plugins, if there are any
        pagure.lib.notify.blinker_publish(topic, msg)

        if not project.private:
            send_fedmsg_notifications(project, topic, msg)
            send_stomp_notifications(project, topic, msg)
            send_mqtt_notifications(project, topic, msg)
            send_webhook_notifications(project, topic, msg)

        if (
            _config.get("PAGURE_CI_SERVICES")
            and project.ci_hook
            and project.ci_hook.active_commit
            and not project.private
        ):
            pagure.lib.tasks_services.trigger_ci_build.delay(
                project_name=project.fullname,
                cause=revs[-1],
                branch=refname,
                ci_type=project.ci_hook.ci_type,
                branch_to=None,
            )


def inform_pull_request_urls(session, project, commits, refname, username):
    """Inform the user about the URLs to open a new pull-request or visit
    the existing one.
    """
    target_repo = project
    if project.is_fork:
        target_repo = project.parent

    taget_repo_obj = pygit2.Repository(target_repo.repopath("main"))
    if not taget_repo_obj.is_empty and not taget_repo_obj.head_is_unborn:
        default_branch = taget_repo_obj.head.shorthand

    pr_uids = []

    if (
        commits
        and refname != default_branch
        and target_repo.settings.get("pull_requests", True)
    ):
        print()
        prs = pagure.lib.query.search_pull_requests(
            session,
            project_id_from=target_repo.id,
            status="Open",
            branch_from=refname,
        )
        if project.id != target_repo.id:
            prs.extend(
                pagure.lib.query.search_pull_requests(
                    session,
                    project_id_from=project.id,
                    status="Open",
                    branch_from=refname,
                )
            )
        # Link to existing PRs if there are any
        seen = len(prs) != 0
        for pr in prs:
            # Refresh the PR in the db and everywhere else where needed
            pagure.lib.tasks.update_pull_request.delay(
                pr.uid, username=username
            )

            # Link tickets with pull-requests if the commit mentions it
            pagure.lib.tasks.link_pr_to_ticket.delay(pr.uid)

            # Inform the user about the PR
            print("View pull-request for %s" % refname)
            print(
                "   %s/%s/pull-request/%s"
                % (_config["APP_URL"].rstrip("/"), pr.project.url_path, pr.id)
            )
            pr_uids.append(pr.uid)

        # If no existing PRs, provide the link to open one
        if not seen:
            print("Create a pull-request for %s" % refname)
            print(
                "   %s/%s/diff/%s..%s"
                % (
                    _config["APP_URL"].rstrip("/"),
                    project.url_path,
                    default_branch,
                    refname,
                )
            )
        print()

    return pr_uids


class DefaultRunner(BaseRunner):
    """Runner for the default hook."""

    @staticmethod
    def post_receive(session, username, project, repotype, repodir, changes):
        """Run the default post-receive hook.

        For args, see BaseRunner.runhook.
        """
        if repotype != "main":
            if _config.get("HOOK_DEBUG", False):
                print("Default hook only runs on the main project repository")
            return

        if changes:
            # Retrieve the default branch
            repo_obj = pygit2.Repository(repodir)
            default_branch = None
            if not repo_obj.is_empty and not repo_obj.head_is_unborn:
                default_branch = repo_obj.head.shorthand

        pr_uids = []

        for refname in changes:
            (oldrev, newrev) = changes[refname]

            forced = False
            if set(newrev) == set(["0"]):
                if refname.startswith("refs/tags"):
                    refname = refname.replace("refs/tags/", "")
                    send_action_notification(
                        session,
                        "tag",
                        "deletion",
                        project,
                        repodir,
                        username,
                        refname,
                        oldrev,
                    )
                    print("Deleting a tag, so we won't run the pagure hook")
                elif refname.startswith("refs/heads/"):
                    refname = refname.replace("refs/heads/", "")
                    send_action_notification(
                        session,
                        "branch",
                        "deletion",
                        project,
                        repodir,
                        username,
                        refname,
                        oldrev,
                    )
                    print("Deleting a branch, so we won't run the pagure hook")
                else:
                    print(
                        "Deleting %s, so we wont run the pagure hook nor "
                        "send notifications" % refname
                    )
                continue
            elif set(oldrev) == set(["0"]):
                oldrev = "^%s" % oldrev
                if refname.startswith("refs/tags"):
                    refname = refname.replace("refs/tags/", "")
                    send_action_notification(
                        session,
                        "tag",
                        "creation",
                        project,
                        repodir,
                        username,
                        refname,
                        newrev,
                    )
                if refname.startswith("refs/heads/"):
                    refname = refname.replace("refs/heads/", "")
                    send_action_notification(
                        session,
                        "branch",
                        "creation",
                        project,
                        repodir,
                        username,
                        refname,
                        newrev,
                    )
            elif pagure.lib.git.is_forced_push(oldrev, newrev, repodir):
                forced = True
                base = pagure.lib.git.get_base_revision(
                    oldrev, newrev, repodir
                )
                if base:
                    oldrev = base[0]

            refname = refname.replace("refs/heads/", "")
            commits = pagure.lib.git.get_revs_between(
                oldrev, newrev, repodir, refname
            )

            log_all = _config.get("LOG_ALL_COMMITS", False)
            if log_all or refname == default_branch:
                print(
                    "Sending to redis to log activity and send commit "
                    "notification emails"
                )
            else:
                print("Sending to redis to send commit notification emails")

            # This is logging the commit to the log table in the DB so we can
            # render commits in the calendar heatmap.
            # It is also sending emails about commits to people using the
            # 'watch' feature to be made aware of new commits.
            pagure.lib.tasks_services.log_commit_send_notifications.delay(
                name=project.name,
                commits=commits,
                abspath=repodir,
                branch=refname,
                default_branch=default_branch,
                namespace=project.namespace,
                username=project.user.user if project.is_fork else None,
            )

            # This one is sending fedmsg and web-hook notifications for project
            # that set them up
            send_notifications(
                session,
                project,
                repodir,
                username,
                refname,
                commits,
                forced,
                oldrev,
            )

            # Now display to the user if this isn't the default branch links to
            # open a new pr or review the existing one
            pr_uids.extend(
                inform_pull_request_urls(
                    session,
                    project,
                    commits,
                    refname,
                    username,
                )
            )

        # Refresh of all opened PRs
        parent = project.parent or project
        if not _config.get("GIT_HOOK_DB_RO", False):
            pagure.lib.tasks.refresh_pr_cache(
                parent.name,
                parent.namespace,
                parent.user.user if parent.is_fork else None,
                but_uids=pr_uids,
            )
        else:
            pagure.lib.tasks.refresh_pr_cache.delay(
                parent.name,
                parent.namespace,
                parent.user.user if parent.is_fork else None,
                but_uids=pr_uids,
            )

        if not project.is_on_repospanner and _config.get(
            "GIT_GARBAGE_COLLECT", False
        ):
            pagure.lib.tasks.git_garbage_collect.delay(
                project.repopath("main")
            )


class Default(BaseHook):
    """Default hooks."""

    name = "default"
    description = (
        "Default hooks that should be enabled for each and every project."
    )
    runner = DefaultRunner

    @classmethod
    def is_enabled_for(cls, project):
        return True
