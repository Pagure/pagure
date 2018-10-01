# -*- coding: utf-8 -*-

"""
 (c) 2016-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, print_function

import logging

import pygit2
import sqlalchemy as sa
import six
import wtforms

try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

import pagure.config
import pagure.exceptions
import pagure.lib.tasks
import pagure.lib.tasks_services
import pagure.utils
from pagure.hooks import BaseHook, BaseRunner
from pagure.lib.model import BASE, Project


_config = pagure.config.reload_config()
_log = logging.getLogger(__name__)


class DefaultTable(BASE):
    """ Stores information about the default hook of a project.

    Table -- hook_default
    """

    __tablename__ = "hook_default"

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        "Project",
        remote_side=[Project.id],
        backref=backref(
            "default_hook",
            cascade="delete, delete-orphan",
            single_parent=True,
            uselist=False,
        ),
    )


def send_fedmsg_notifications(project, topic, msg):
    """ If the user asked for fedmsg notifications on commit, this will
    do it.
    """
    import fedmsg

    config = fedmsg.config.load_config([], None)
    config["active"] = True
    config["endpoints"]["relay_inbound"] = config["relay_inbound"]
    fedmsg.init(name="relay_inbound", **config)

    pagure.lib.notify.log(
        project=project,
        topic=topic,
        msg=msg,
        redis=None,  # web-hook notification are handled separately
    )


def send_webhook_notifications(project, topic, msg):
    """ If the user asked for webhook notifications on commit, this will
    do it.
    """

    pagure.lib.tasks_services.webhook_notification.delay(
        topic=topic,
        msg=msg,
        namespace=project.namespace,
        name=project.name,
        user=project.user.username if project.is_fork else None,
    )


def send_notifications(session, project, repodir, user, refname, revs, forced):
    """ Send out-going notifications about the commits that have just been
    pushed.
    """

    auths = set()
    for rev in revs:
        email = pagure.lib.git.get_author_email(rev, repodir)
        name = pagure.lib.git.get_author(rev, repodir)
        author = pagure.lib.search_user(session, email=email) or name
        auths.add(author)

    authors = []
    for author in auths:
        if not isinstance(author, six.string_types):
            author = author.to_json(public=True)
        authors.append(author)

    if revs:
        revs.reverse()
        print("* Publishing information for %i commits" % len(revs))

        topic = "git.receive"
        msg = dict(
            total_commits=len(revs),
            start_commit=revs[0],
            end_commit=revs[-1],
            branch=refname,
            forced=forced,
            authors=list(authors),
            agent=user,
            repo=project.to_json(public=True)
            if not isinstance(project, six.string_types)
            else project,
        )

        fedmsg_hook = pagure.lib.plugins.get_plugin("Fedmsg")
        fedmsg_hook.db_object()

        always_fedmsg = _config.get("ALWAYS_FEDMSG_ON_COMMITS") or None

        if always_fedmsg or (
            project.fedmsg_hook and project.fedmsg_hook.active
        ):
            try:
                print("  - to fedmsg")
                send_fedmsg_notifications(project, topic, msg)
            except Exception:
                _log.exception(
                    "Error sending fedmsg notifications on commit push"
                )
        if project.settings.get("Web-hooks") and not project.private:
            try:
                print("  - to web-hooks")
                send_webhook_notifications(project, topic, msg)
            except Exception:
                _log.exception(
                    "Error sending web-hook notifications on commit push"
                )

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
            )


def inform_pull_request_urls(
    session, project, commits, refname, default_branch
):
    """ Inform the user about the URLs to open a new pull-request or visit
    the existing one.
    """
    target_repo = project
    if project.is_fork:
        target_repo = project.parent

    if (
        commits
        and refname != default_branch
        and target_repo.settings.get("pull_requests", True)
    ):
        print()
        prs = pagure.lib.search_pull_requests(
            session,
            project_id_from=project.id,
            status="Open",
            branch_from=refname,
        )
        # Link to existing PRs if there are any
        seen = len(prs) != 0
        for pr in prs:
            # Link tickets with pull-requests if the commit mentions it
            pagure.lib.tasks.link_pr_to_ticket.delay(pr.uid)

            # Inform the user about the PR
            print("View pull-request for %s" % refname)
            print(
                "   %s/%s/pull-request/%s"
                % (_config["APP_URL"].rstrip("/"), pr.project.url_path, pr.id)
            )
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


class DefaultRunner(BaseRunner):
    """ Runner for the default hook."""

    @staticmethod
    def post_receive(session, username, project, repotype, repodir, changes):
        """ Run the default post-receive hook.

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

        for refname in changes:
            (oldrev, newrev) = changes[refname]

            forced = False
            if set(newrev) == set(["0"]):
                print(
                    "Deleting a reference/branch, so we won't run the "
                    "pagure hook"
                )
                return
            elif set(oldrev) == set(["0"]):
                oldrev = "^%s" % oldrev
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

            if refname == default_branch:
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
                session, project, repodir, username, refname, commits, forced
            )

            # Now display to the user if this isn't the default branch links to
            # open a new pr or review the existing one
            inform_pull_request_urls(
                session, project, commits, refname, default_branch
            )

        # Schedule refresh of all opened PRs
        parent = project.parent or project
        pagure.lib.tasks.refresh_pr_cache.delay(
            parent.name,
            parent.namespace,
            parent.user.user if parent.is_fork else None,
        )

        session.remove()


class DefaultForm(FlaskForm):
    """ Form to configure the default hook. """

    active = wtforms.BooleanField("Active", [wtforms.validators.Optional()])

    def __init__(self, *args, **kwargs):
        """ Calls the default constructor with the normal argument but
        uses the list of collection provided to fill the choices of the
        drop-down list.
        """
        super(DefaultForm, self).__init__(*args, **kwargs)


class Default(BaseHook):
    """ Default hooks. """

    name = "default"
    description = (
        "Default hooks that should be enabled for each and every project."
    )

    form = DefaultForm
    db_object = DefaultTable
    backref = "default_hook"
    form_fields = ["active"]
    runner = DefaultRunner
