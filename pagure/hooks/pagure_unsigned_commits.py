# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import absolute_import, unicode_literals

import sqlalchemy as sa
import wtforms

try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm

from sqlalchemy.orm import backref, relation

import pagure.config
import pagure.lib.git
from pagure.hooks import BaseHook, BaseRunner
from pagure.lib.model import BASE, Project

_config = pagure.config.reload_config()


class PagureUnsignedCommitTable(BASE):
    """Stores information about the pagure hook deployed on a project.

    Table -- hook_pagure_unsigned_commit
    """

    __tablename__ = "hook_pagure_unsigned_commit"

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
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref(
            "pagure_unsigned_commit_hook",
            cascade="delete, delete-orphan",
            single_parent=True,
            uselist=False,
        ),
    )


class PagureUnsignerRunner(BaseRunner):
    """Runner for the hook blocking unsigned commits."""

    @staticmethod
    def pre_receive(
        session, username, project, repotype, repodir, changes, pull_request
    ):
        """Run the pre-receive tasks of a hook.

        For args, see BaseRunner.runhook.
        """

        if repotype != "main":
            print("Only enforcing sign-off-by on the main git repo")
            return

        for refname in changes:
            (oldrev, newrev) = changes[refname]

            if set(newrev) == set(["0"]):
                print(
                    "Deleting a reference/branch, so we won't run the "
                    "hook to block unsigned commits"
                )
                return

            commits = pagure.lib.git.get_revs_between(
                oldrev, newrev, repodir, refname
            )
            for commit in commits:
                if _config.get("HOOK_DEBUG", False):
                    print("Processing commit: %s" % commit)
                signed = False
                for line in pagure.lib.git.read_git_lines(
                    ["log", "--no-walk", commit], repodir
                ):
                    if line.lower().strip().startswith("signed-off-by"):
                        signed = True
                        break
                if _config.get("HOOK_DEBUG", False):
                    print(" - Commit: %s is signed: %s" % (commit, signed))
                if not signed:
                    print("Commit %s is not signed" % commit)
                    raise Exception("Commit %s is not signed" % commit)


class PagureUnsignedCommitForm(FlaskForm):
    """Form to configure the pagure hook."""

    active = wtforms.BooleanField("Active", [wtforms.validators.Optional()])


class PagureUnsignedCommitHook(BaseHook):
    """PagurPagureUnsignedCommit hook."""

    name = "Block Un-Signed commits"
    description = (
        "Using this hook you can block any push with commits "
        'missing a "Signed-Off-By"'
    )
    form = PagureUnsignedCommitForm
    db_object = PagureUnsignedCommitTable
    backref = "pagure_unsigned_commit_hook"
    form_fields = ["active"]
    hook_type = "pre-receive"
    runner = PagureUnsignerRunner
