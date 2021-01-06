# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


from __future__ import unicode_literals, absolute_import

import sqlalchemy as sa
import requests
import wtforms

try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

import pagure
from pagure.hooks import BaseHook, BaseRunner
from pagure.lib.model import BASE, Project

_config = pagure.config.config


class RtdTable(BASE):
    """Stores information about the pagure hook deployed on a project.

    Table -- hook_rtd
    """

    __tablename__ = "hook_rtd"

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    branches = sa.Column(sa.Text, nullable=True)
    api_url = sa.Column(sa.Text, nullable=False)
    api_token = sa.Column(sa.Text, nullable=False)

    project = relation(
        "Project",
        remote_side=[Project.id],
        backref=backref(
            "rtd_hook",
            cascade="delete, delete-orphan",
            single_parent=True,
            uselist=False,
        ),
    )


class RtdForm(FlaskForm):
    """ Form to configure the pagure hook. """

    api_url = wtforms.StringField(
        "URL endpoint used to trigger the builds",
        [wtforms.validators.Optional()],
    )
    api_token = wtforms.StringField(
        "API token provided by readthedocs", [wtforms.validators.Optional()]
    )
    branches = wtforms.StringField(
        "Restrict build to these branches only (comma separated)",
        [wtforms.validators.Optional()],
    )

    active = wtforms.BooleanField("Active", [wtforms.validators.Optional()])


DESCRIPTION = """
Git hook to trigger building documentation on the readthedocs.org service
when a commit is pushed to the repository.

If you specify one or more branches (using commas `,` to separate them) only
pushes made to these branches will trigger a new build of the documentation.

To set up this hook, you will need to login to https://readthedocs.org/
Go to your project's admin settings, and in the ``Integrations`` section
add a new ``Generic API incoming webhook``.

This will give you access to one URL and one API token, both of which you
will have to provide below.

"""


class RtdRunner(BaseRunner):
    @staticmethod
    def post_receive(session, username, project, repotype, repodir, changes):
        """Perform the RTD Post Receive hook.

        For arguments, see BaseRunner.runhook.
        """
        # Get the list of branches
        branches = [
            branch.strip() for branch in project.rtd_hook.branches.split(",")
        ]

        # Remove empty branches
        branches = [branch.strip() for branch in branches if branch]

        url = project.rtd_hook.api_url
        if not url:
            print(
                "No API url specified to trigger the build, please update "
                "the configuration"
            )
        if not project.rtd_hook.api_token:
            print(
                "No API token specified to trigger the build, please update "
                "the configuration"
            )

        for refname in changes:
            oldrev, newrev = changes[refname]
            if _config.get("HOOK_DEBUG", False):
                print("%s: %s -> %s" % (refname, oldrev, newrev))

            refname = refname.replace("refs/heads/", "")
            if branches:
                if refname in branches:
                    print("Starting RTD build at %s" % (url))
                    requests.post(
                        url,
                        data={
                            "branches": refname,
                            "token": project.rtd_hook.api_token,
                        },
                        timeout=60,
                    )
            else:
                print("Starting RTD build at %s" % (url))
                requests.post(
                    url,
                    data={
                        "branches": refname,
                        "token": project.rtd_hook.api_token,
                    },
                    timeout=60,
                )


class RtdHook(BaseHook):
    """ Read The Doc hook. """

    name = "Read the Doc"
    description = DESCRIPTION
    form = RtdForm
    db_object = RtdTable
    runner = RtdRunner
    backref = "rtd_hook"
    form_fields = ["active", "api_url", "api_token", "branches"]
