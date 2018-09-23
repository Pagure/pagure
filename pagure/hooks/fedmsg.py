# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

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


class FedmsgTable(BASE):
    """ Stores information about the fedmsg hook deployed on a project.

    Table -- hook_fedmsg
    """

    __tablename__ = "hook_fedmsg"

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
            "fedmsg_hook",
            cascade="delete, delete-orphan",
            single_parent=True,
            uselist=False,
        ),
    )


class FedmsgRunner(BaseRunner):
    """ Runner for the fedmsg hook, it does nothing as all the magic is
    part of the default hook/runner.
    """
    pass


class FedmsgForm(FlaskForm):
    """ Form to configure the fedmsg hook. """

    active = wtforms.BooleanField("Active", [wtforms.validators.Optional()])


DESCRIPTION = """
This hook pushes commit notification to the fedmsg bus to be consumed by other
applications.

It is different from the fedmsg setting present in the project options block
which publishes notifications about events happening in the project via
pagure's (web) user interface, for example: new tickets, new comments, new
pull-requests and so on.
This hook on the other only acts on commits.
"""


class Fedmsg(BaseHook):
    """ Fedmsg hooks. """

    name = "Fedmsg"
    description = DESCRIPTION
    form = FedmsgForm
    db_object = FedmsgTable
    backref = "fedmsg_hook"
    form_fields = ["active"]
    runner = FedmsgRunner

    @classmethod
    def install(cls, project, dbobj):
        """ Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        This no longer does anything as the code has now been merged into
        the default hook. So we still need this for people to opt in/out of
        sending fedmsg notifications on commit push, but other than that
        this plugin doesn't do much anymore.

        """
        pass

    @classmethod
    def remove(cls, project):
        """ Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        This no longer does anything as the code has now been merged into
        the default hook. So we still need this for people to opt in/out of
        sending fedmsg notifications on commit push, but other than that
        this plugin doesn't do much anymore.

        """
        pass
