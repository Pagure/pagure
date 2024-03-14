# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import absolute_import, unicode_literals

import logging

import pygit2
import sqlalchemy as sa
import wtforms

try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import backref, relation

import pagure.config
import pagure.lib.git
import pagure.lib.query
from pagure.hooks import BaseHook, BaseRunner
from pagure.lib.model import BASE, Project

_log = logging.getLogger(__name__)
pagure_config = pagure.config.reload_config()


class PagureTable(BASE):
    """Stores information about the pagure hook deployed on a project.

    Table -- hook_pagure
    """

    __tablename__ = "hook_pagure"

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
            "pagure_hook",
            cascade="delete, delete-orphan",
            single_parent=True,
            uselist=False,
        ),
    )


def generate_revision_change_log(
    session, project, username, repodir, new_commits_list
):

    print("Detailed log of new commits:\n\n")
    commitid = None
    for line in pagure.lib.git.read_git_lines(
        ["log", "--no-walk"] + new_commits_list + ["--"], repodir
    ):
        if line.startswith("commit"):
            commitid = line.split("commit ")[-1]

        line = line.strip()
        print("*", line)
        for issue_or_pr in pagure.lib.link.get_relation(
            session,
            project.name,
            project.username if project.is_fork else None,
            project.namespace,
            line,
            "fixes",
            include_prs=True,
        ):
            if pagure_config.get("HOOK_DEBUG", False):
                print(commitid, relation)
            fixes_relation(
                session,
                username,
                commitid,
                issue_or_pr,
                pagure_config.get("APP_URL"),
            )

        for issue in pagure.lib.link.get_relation(
            session,
            project.name,
            project.username if project.is_fork else None,
            project.namespace,
            line,
            "relates",
        ):
            if pagure_config.get("HOOK_DEBUG", False):
                print(commitid, issue)
            relates_commit(
                session,
                username,
                commitid,
                issue,
                pagure_config.get("APP_URL"),
            )


def relates_commit(session, username, commitid, issue, app_url=None):
    """Add a comment to an issue that this commit relates to it."""

    url = "../%s" % commitid[:8]
    if app_url:
        if app_url.endswith("/"):
            app_url = app_url[:-1]
        project = issue.project.fullname
        if issue.project.is_fork:
            project = "fork/%s" % project
        url = "%s/%s/c/%s" % (app_url, project, commitid[:8])

    comment = """ Commit [%s](%s) relates to this ticket""" % (
        commitid[:8],
        url,
    )

    try:
        pagure.lib.query.add_issue_comment(
            session, issue=issue, comment=comment, user=username
        )
        session.commit()
    except pagure.exceptions.PagureException as err:
        print(err)
    except SQLAlchemyError as err:  # pragma: no cover
        session.rollback()
        _log.exception(err)


def fixes_relation(session, username, commitid, relation, app_url=None):
    """Add a comment to an issue or PR that this commit fixes it and update
    the status if the commit is in the master branch."""

    url = "../c/%s" % commitid[:8]
    if app_url:
        if app_url.endswith("/"):
            app_url = app_url[:-1]
        project = relation.project.fullname
        if relation.project.is_fork:
            project = "fork/%s" % project
        url = "%s/%s/c/%s" % (app_url, project, commitid[:8])

    comment = """ Commit [%s](%s) fixes this %s""" % (
        commitid[:8],
        url,
        relation.isa,
    )

    try:
        if relation.isa == "issue":
            pagure.lib.query.add_issue_comment(
                session, issue=relation, comment=comment, user=username
            )
        elif relation.isa == "pull-request":
            pagure.lib.query.add_pull_request_comment(
                session,
                request=relation,
                commit=None,
                tree_id=None,
                filename=None,
                row=None,
                comment=comment,
                user=username,
            )
        session.commit()
    except pagure.exceptions.PagureException as err:
        print(err)
    except SQLAlchemyError as err:  # pragma: no cover
        session.rollback()
        _log.exception(err)

    try:
        if relation.isa == "issue":
            pagure.lib.query.edit_issue(
                session,
                relation,
                user=username,
                status="Closed",
                close_status="Fixed",
            )
        elif relation.isa == "pull-request":
            pagure.lib.query.close_pull_request(
                session, relation, user=username, merged=True
            )
        session.commit()
    except pagure.exceptions.PagureException as err:
        print(err)
    except SQLAlchemyError as err:  # pragma: no cover
        session.rollback()
        print("ERROR", err)
        _log.exception(err)


class PagureRunner(BaseRunner):
    """Runner for the pagure's specific git hook."""

    @staticmethod
    def post_receive(
        session, username, project, repotype, repodir, changes, pull_request
    ):
        """Run the default post-receive hook.

        For args, see BaseRunner.runhook.
        """

        if repotype != "main":
            print("The pagure hook only runs on the main git repo.")
            return

        for refname in changes:
            (oldrev, newrev) = changes[refname]

            # Retrieve the default branch
            repo_obj = pygit2.Repository(repodir)
            default_branch = None
            if not repo_obj.is_empty and not repo_obj.head_is_unborn:
                default_branch = repo_obj.head.shorthand

            # Skip all branch but the default one
            refname = refname.replace("refs/heads/", "")
            if refname != default_branch:
                continue

            if set(newrev) == set(["0"]):
                print(
                    "Deleting a reference/branch, so we won't run the "
                    "pagure hook"
                )
                return

            generate_revision_change_log(
                session,
                project,
                username,
                repodir,
                pagure.lib.git.get_revs_between(
                    oldrev, newrev, repodir, refname
                ),
            )
            session.close()


class PagureForm(FlaskForm):
    """Form to configure the pagure hook."""

    active = wtforms.BooleanField("Active", [wtforms.validators.Optional()])


DESCRIPTION = """
Pagure specific hook to add a comment to issues or pull requests if the pushed
commits fix them
or relate to them. This is determined based on the commit message.

To reference an issue/PR you need to use one of recognized keywords followed by
a reference to the issue or PR, separated by whitespace and and optional colon.
Such references can be either:

 * The issue/PR number preceded by the `#` symbol
 * The full URL of the issue or PR

If using the full URL, it is possible to reference issues in other projects.

The recognized keywords are:

 * fix/fixed/fixes
 * relate/related/relates
 * merge/merges/merged
 * close/closes/closed

Examples:

 * Fixes #21
 * related: https://pagure.io/myproject/issue/32
 * this commit merges #74
 * Merged: https://pagure.io/myproject/pull-request/74

Capitalization does not matter; neither does the colon between keyword and
number.


"""


class PagureHook(BaseHook):
    """Pagure hook."""

    name = "Pagure"
    description = DESCRIPTION
    form = PagureForm
    db_object = PagureTable
    backref = "pagure_hook"
    form_fields = ["active"]
    runner = PagureRunner
