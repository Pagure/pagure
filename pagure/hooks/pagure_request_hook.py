# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

import os

import flask
import sqlalchemy as sa
import wtforms

try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

import pagure.lib.git
from pagure.config import config as pagure_config
from pagure.hooks import BaseHook, BaseRunner
from pagure.lib.model import BASE, Project


class PagureRequestsTable(BASE):
    """ Stores information about the pagure requests hook deployed on a
    project.

    Table -- hook_pagure_requests
    """

    __tablename__ = "hook_pagure_requests"

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
            "pagure_hook_requests",
            cascade="delete, delete-orphan",
            single_parent=True,
            uselist=False,
        ),
    )


class PagureRequestRunner(BaseRunner):
    """ Runner for the hook updating the db about requests on push to the
    git repo containing the meta-data about pull-requests.
    """

    @staticmethod
    def post_receive(session, username, project, repotype, repodir, changes):
        """ Run the default post-receive hook.

        For args, see BaseRunner.runhook.
        """

        if repotype != "requests":
            print(
                "The pagure requests hook only runs on the requests "
                "git repo.")
            return

        for refname in changes:
            (oldrev, newrev) = changes[refname]

            if set(newrev) == set(["0"]):
                print(
                    "Deleting a reference/branch, so we won't run the "
                    "pagure hook"
                )
                return

            commits = pagure.lib.git.get_revs_between(
                oldrev, newrev, repodir, refname
            )

            pagure.lib.tasks_services.load_json_commits_to_db.delay(
                name=project.name,
                commits=commits,
                abspath=repodir,
                data_type="pull-request",
                agent=username,
                namespace=project.namespace,
                username=project.user.user if project.is_fork else None,
            )


class PagureRequestsForm(FlaskForm):
    """ Form to configure the pagure hook. """

    active = wtforms.BooleanField("Active", [wtforms.validators.Optional()])


class PagureRequestHook(BaseHook):
    """ Pagure request hook. """

    name = "Pagure requests"
    description = (
        "Pagure specific hook to update pull-requests stored "
        "in the database based on the information pushed in the requests "
        "git repository."
    )
    form = PagureRequestsForm
    db_object = PagureRequestsTable
    backref = "pagure_hook_requests"
    form_fields = ["active"]
    runner = PagureRequestRunner

    @classmethod
    def set_up(cls, project):
        """ Install the generic post-receive hook that allow us to call
        multiple post-receive hooks as set per plugin.
        """
        repopath = os.path.join(pagure_config["REQUESTS_FOLDER"], project.path)
        if not os.path.exists(repopath):
            flask.abort(404, "No git repo found")

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), "files"
        )

        # Make sure the hooks folder exists
        hookfolder = os.path.join(repopath, "hooks")
        if not os.path.exists(hookfolder):
            os.makedirs(hookfolder)

        # Install the main post-receive file
        postreceive = os.path.join(hookfolder, "post-receive")
        hook_file = os.path.join(hook_files, "post-receive")
        if not os.path.exists(postreceive):
            os.symlink(hook_file, postreceive)

    @classmethod
    def install(cls, project, dbobj):
        """ Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        """
        repopaths = [
            os.path.join(pagure_config["REQUESTS_FOLDER"], project.path)
        ]

        cls.base_install(
            repopaths, dbobj, "pagure-requests", "pagure_hook_requests.py"
        )

    @classmethod
    def remove(cls, project):
        """ Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        """
        repopaths = [
            os.path.join(pagure_config["REQUESTS_FOLDER"], project.path)
        ]

        cls.base_remove(repopaths, "pagure-requests")
