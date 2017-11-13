# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import sqlalchemy as sa
import wtforms
try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from pagure.hooks import BaseHook
from pagure.lib.model import BASE, Project
from pagure.utils import get_repo_path


class FedmsgTable(BASE):
    """ Stores information about the fedmsg hook deployed on a project.

    Table -- hook_fedmsg
    """

    __tablename__ = 'hook_fedmsg'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        'Project', remote_side=[Project.id],
        backref=backref(
            'fedmsg_hook', cascade="delete, delete-orphan",
            single_parent=True, uselist=False)
    )


class FedmsgForm(FlaskForm):
    ''' Form to configure the fedmsg hook. '''
    active = wtforms.BooleanField(
        'Active',
        [wtforms.validators.Optional()]
    )


class Fedmsg(BaseHook):
    ''' Fedmsg hooks. '''

    name = 'Fedmsg'
    description = 'This hook pushes the commit messages'\
        ' to the Fedora bus to be consumed by other applications.'
    form = FedmsgForm
    db_object = FedmsgTable
    backref = 'fedmsg_hook'
    form_fields = ['active']

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = [get_repo_path(project)]
        cls.base_install(repopaths, dbobj, 'fedmsg', 'fedmsg_hook.py')

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = [get_repo_path(project)]
        cls.base_remove(repopaths, 'fedmsg')
