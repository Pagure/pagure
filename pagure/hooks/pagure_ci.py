# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import absolute_import, unicode_literals

import flask
import sqlalchemy as sa
import wtforms

try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm

from sqlalchemy.orm import backref, relationship as relation

import pagure.lib.login
from pagure.hooks import BaseHook, BaseRunner, RequiredIf
from pagure.lib.model import BASE, Project


class PagureCITable(BASE):
    """Stores information about the CI linked to on a project.

    Table -- hook_pagure_ci
    """

    __tablename__ = "hook_pagure_ci"

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    pagure_ci_token = sa.Column(sa.String(32), nullable=True, index=True)
    ci_type = sa.Column(sa.String(255), nullable=True)
    ci_url = sa.Column(sa.String(255), nullable=True, unique=False)
    ci_job = sa.Column(sa.String(255), nullable=True, unique=False)
    ci_username = sa.Column(sa.String(255), nullable=True, unique=False)
    ci_password = sa.Column(sa.String(255), nullable=True, unique=False)
    active = sa.Column(sa.Boolean, nullable=False, default=False)
    active_commit = sa.Column(sa.Boolean, nullable=False, default=False)
    active_pr = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        "Project",
        remote_side=[Project.id],
        backref=backref(
            "ci_hook",
            cascade="delete, delete-orphan",
            single_parent=True,
            uselist=False,
        ),
    )


class PagureCIRunner(BaseRunner):
    """Runner for the pagure-ci hook, it does nothing as the magic is part
    of the CI system itself (to see if there was a commit made and build if
    so).
    """

    pass


tmpl = """
{% if repo | hasattr('ci_hook') and repo.ci_hook and
    repo.ci_hook.pagure_ci_token %}

The token to be used by the CI to trigger the build is:
<pre>
{{ repo.ci_hook.pagure_ci_token}}
</pre>

The URL to be used to POST the results of your build is:
<pre>
{{ (config['APP_URL'][:-1] if config['APP_URL'].endswith('/')
  else config['APP_URL'])
  + url_for('api_ns.%s_ci_notification' % repo.ci_hook.ci_type,
    repo=repo.name, username=username, namespace=repo.namespace,
    pagure_ci_token=repo.ci_hook.pagure_ci_token) }}
</pre>

{% else %}
You will have access to the token used by the CI service to trigger the job
and the URL needed to report back the job status in pagure after the plugin
activation.
{% endif %}
"""


class PagureCiForm(FlaskForm):
    """Form to configure the CI hook."""

    ci_type = wtforms.SelectField(
        "Type of CI service",
        [RequiredIf(["active_commit", "active_pr"])],
        choices=[],
    )

    ci_url = wtforms.StringField(
        "URL to the project on the CI service",
        [
            RequiredIf(["active_commit", "active_pr"]),
            wtforms.validators.Length(max=255),
        ],
    )

    ci_username = wtforms.StringField(
        "Username to authenticate with if needed",
        [wtforms.validators.Optional(), wtforms.validators.Length(max=255)],
    )

    ci_password = wtforms.StringField(
        "Password to authenticate with if needed",
        [wtforms.validators.Optional(), wtforms.validators.Length(max=255)],
    )

    ci_job = wtforms.StringField(
        "Name of the job to trigger",
        [
            RequiredIf(["active_commit", "active_pr"]),
            wtforms.validators.Length(max=255),
        ],
    )

    # The active field is not render in the UI it used
    # to hold the result of a logical OR between active_pr
    # and active_commit.
    # The value of active is set in pagure.ui.plugins.view_plugin
    active = wtforms.BooleanField(
        "Activate Pagure CI service", [wtforms.validators.Optional()]
    )

    active_commit = wtforms.BooleanField(
        "Trigger CI job on commits", [wtforms.validators.Optional()]
    )

    active_pr = wtforms.BooleanField(
        "Trigger CI job on pull-requests", [wtforms.validators.Optional()]
    )

    def __init__(self, *args, **kwargs):
        """Calls the default constructor with the normal argument but
        uses the list of collection provided to fill the choices of the
        drop-down list.
        """
        super(PagureCiForm, self).__init__(*args, **kwargs)

        types = pagure.config.config.get("PAGURE_CI_SERVICES", [])
        self.ci_type.choices = [(ci_type, ci_type) for ci_type in types]


class PagureCi(BaseHook):
    """Continuous Integration (CI) hooks."""

    name = "Pagure CI"
    description = (
        "Integrate continuous integration (CI) services into your "
        "pagure project, providing you notifications for every pull-request "
        "opened in the project."
    )
    extra_info = tmpl
    form = PagureCiForm
    db_object = PagureCITable
    backref = "ci_hook"
    form_fields = ["ci_type", "ci_url", "ci_job", "active_commit", "active_pr"]
    runner = PagureCIRunner

    @classmethod
    def set_up(cls, project):
        """Install the generic post-receive hook that allow us to call
        multiple post-receive hooks as set per plugin.
        """
        pass

    @classmethod
    def install(cls, project, dbobj):
        """Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        """
        if not dbobj.pagure_ci_token:
            dbobj.pagure_ci_token = pagure.lib.login.id_generator(32)
            flask.g.session.commit()

    @classmethod
    def remove(cls, project):
        """Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        """
        if project.ci_hook is not None:
            project.ci_hook.pagure_ci_token = None
            flask.g.session.commit()
