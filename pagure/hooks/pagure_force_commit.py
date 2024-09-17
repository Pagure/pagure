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

from sqlalchemy.orm import backref, relationship as relation

import pagure.lib.git
from pagure.hooks import BaseHook, BaseRunner, RequiredIf
from pagure.lib.model import BASE, Project


class PagureForceCommitTable(BASE):
    """Stores information about the pagure hook deployed on a project.

    Table -- hook_pagure_force_commit
    """

    __tablename__ = "hook_pagure_force_commit"

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    branches = sa.Column(sa.Text, nullable=False, default="")

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        "Project",
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref(
            "pagure_force_commit_hook",
            cascade="delete, delete-orphan",
            single_parent=True,
            uselist=False,
        ),
    )


class PagureForceCommitRunner(BaseRunner):
    """Runner for the hook blocking force push."""

    @staticmethod
    def pre_receive(
        session, username, project, repotype, repodir, changes, pull_request
    ):
        """Run the pre-receive tasks of a hook.

        For args, see BaseRunner.runhook.
        """

        # Get the list of branches
        branches = []
        if project.pagure_force_commit_hook:
            branches = [
                branch.strip()
                for branch in project.pagure_force_commit_hook.branches.split(
                    ","
                )
                if branch.strip()
            ]

        for refname in changes:
            (oldrev, newrev) = changes[refname]

            refname = refname.replace("refs/heads/", "")
            if refname in branches or branches == ["*"]:

                if set(newrev) == set(["0"]):
                    raise Exception("Deletion is forbidden")
                elif pagure.lib.git.is_forced_push(oldrev, newrev, repodir):
                    raise Exception("Non fast-forward push is forbidden")


class PagureForceCommitForm(FlaskForm):
    """Form to configure the pagure hook."""

    branches = wtforms.StringField("Branches", [RequiredIf("active")])

    active = wtforms.BooleanField("Active", [wtforms.validators.Optional()])


class PagureForceCommitHook(BaseHook):
    """PagurPagureForceCommit hook."""

    name = "Block non fast-forward pushes"
    description = (
        "Using this hook you can block any non-fast-forward "
        "commit forced pushed to one or more branches.\n"
        "You can specify one or more branch names (sperated them using "
        "commas) or block all the branches by specifying: ``*``"
    )
    form = PagureForceCommitForm
    db_object = PagureForceCommitTable
    backref = "pagure_force_commit_hook"
    form_fields = ["branches", "active"]
    hook_type = "pre-receive"
    runner = PagureForceCommitRunner
