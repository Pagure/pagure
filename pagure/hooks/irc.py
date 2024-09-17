# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import absolute_import, unicode_literals

import pygit2
import sqlalchemy as sa
import wtforms

try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm

from sqlalchemy.orm import backref, relationship as relation

from pagure.hooks import BaseHook, RequiredIf
from pagure.lib.model import BASE, Project
from pagure.utils import get_repo_path


class IrcTable(BASE):
    """Stores information about the irc hook deployed on a project.

    Table -- hook_irc
    """

    __tablename__ = "hook_irc"

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    server = sa.Column(sa.Text, nullable=False, default="")
    port = sa.Column(sa.Text, nullable=False, default="")
    room = sa.Column(sa.Text, nullable=False, default="")
    nick = sa.Column(sa.Text, nullable=True, default=None)
    nick_pass = sa.Column(sa.Text, nullable=True, default=None)
    active = sa.Column(sa.Boolean, nullable=False, default=False)
    join = sa.Column(sa.Boolean, nullable=False, default=True)
    ssl = sa.Column(sa.Boolean, nullable=False, default=True)

    project = relation(
        "Project",
        remote_side=[Project.id],
        backref=backref(
            "irc_hook",
            cascade="delete, delete-orphan",
            single_parent=True,
            uselist=False,
        ),
    )


class IrcForm(FlaskForm):
    """Form to configure the irc hook."""

    server = wtforms.StringField(
        'Server <span class="error">*</span>', [RequiredIf("active")]
    )
    port = wtforms.StringField(
        'Port <span class="error">*</span>', [RequiredIf("active")]
    )
    room = wtforms.StringField(
        'Room <span class="error">*</span>', [RequiredIf("active")]
    )
    nick = wtforms.StringField("Nick", [wtforms.validators.Optional()])
    nick_pass = wtforms.StringField(
        "Nickserv Password", [wtforms.validators.Optional()]
    )

    active = wtforms.BooleanField("Active", [wtforms.validators.Optional()])
    join = wtforms.BooleanField(
        "Message Without Join", [wtforms.validators.Optional()]
    )
    ssl = wtforms.BooleanField("Use SSL", [wtforms.validators.Optional()])


class Hook(BaseHook):
    """IRC hooks."""

    name = "IRC"
    description = (
        "This hook sends message to the mention channel regarding"
        " the changes made by the pushes to the git repository."
    )
    form = IrcForm
    db_object = IrcTable
    backref = "irc_hook"
    form_fields = [
        "server",
        "port",
        "room",
        "nick",
        "nick_pass",
        "active",
        "join",
        "ssl",
    ]

    @classmethod
    def install(cls, project, dbobj):
        """Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        """
        repopaths = [get_repo_path(project)]

        repo_obj = pygit2.Repository(repopaths[0])  # noqa

        # Configure the hook
        # repo_obj.config.set_multivar()

        # Install the hook itself
        # cls.base_install(repopaths, dbobj, 'irc', 'git_irc.py')

    @classmethod
    def remove(cls, project):
        """Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        """
        repopaths = [get_repo_path(project)]  # noqa

        # cls.base_remove(repopaths, 'irc')
