# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Slavek Kabrda <bkabrda@redhat.com>

"""

from __future__ import unicode_literals
import sys

import sqlalchemy as sa
import wtforms

try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from pagure.hooks import BaseHook, BaseRunner
from pagure.lib.model import BASE, Project


class PagureNoNewBranchesTable(BASE):
    """ Stores information about the pagure hook deployed on a project.

    Table -- hook_pagure_no_new_branches
    """

    __tablename__ = "hook_pagure_no_new_branches"

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
            "pagure_hook_no_new_branches",
            cascade="delete, delete-orphan",
            single_parent=True,
            uselist=False,
        ),
    )


class PagureNoNewBranchRunner(BaseRunner):
    """ Runner for the hook blocking new branches from being created. """

    @staticmethod
    def pre_receive(session, username, project, repotype, repodir, changes):
        """ Run the pre-receive tasks of a hook.

        For args, see BaseRunner.runhook.
        """

        for refname in changes:
            (oldrev, newrev) = changes[refname]

            if set(oldrev) == set(["0"]):
                raise Exception(
                    "Creating a new reference/branch is not "
                    "allowed in this project."
                )


class PagureNoNewBranchesForm(FlaskForm):
    """ Form to configure the pagure hook. """

    active = wtforms.BooleanField("Active", [wtforms.validators.Optional()])


class PagureNoNewBranchesHook(BaseHook):
    """ PagureNoNewBranches hook. """

    name = "Prevent creating new branches by git push"
    description = "This hook prevents creating new branches by git push."
    form = PagureNoNewBranchesForm
    db_object = PagureNoNewBranchesTable
    backref = "pagure_hook_no_new_branches"
    form_fields = ["active"]
    hook_type = "pre-receive"
    runner = PagureNoNewBranchRunner
