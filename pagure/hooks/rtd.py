# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os

import sqlalchemy as sa
import pygit2
import wtforms
from flask.ext import wtf
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from pagure.hooks import BaseHook, RequiredIf
from pagure.lib.model import BASE, Project
from pagure import APP, get_repo_path


class RtdTable(BASE):
    """ Stores information about the pagure hook deployed on a project.

    Table -- hook_rtd
    """

    __tablename__ = 'hook_rtd'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE', ondelete='CASCADE',
            name='hook_rtd_project_id_fkey'),
        nullable=False,
        unique=True,
        index=True)

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project_name = sa.Column(sa.Text, nullable=False)
    branches = sa.Column(sa.Text, nullable=True)

    project = relation(
        'Project', remote_side=[Project.id],
        backref=backref(
            'rtd_hook', cascade="delete, delete-orphan",
            single_parent=True)
    )


class RtdForm(wtf.Form):
    ''' Form to configure the pagure hook. '''
    project_name = wtforms.TextField(
        'Project name on readthedoc.org',
        [RequiredIf('active')]
    )
    branches = wtforms.TextField(
        'Restrict build to these branches only (comma separated)',
        [wtforms.validators.Optional()]
    )

    active = wtforms.BooleanField(
        'Active',
        [wtforms.validators.Optional()]
    )


class RtdHook(BaseHook):
    ''' Read The Doc hook. '''

    name = 'Read the Doc'
    description = 'Kick off a build of the documentation on readthedocs.org.'
    form = RtdForm
    db_object = RtdTable
    backref = 'rtd_hook'
    form_fields = ['active', 'project_name', 'branches']

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = [get_repo_path(project)]

        cls.base_install(repopaths, dbobj, 'rtd', 'rtd_hook.py')

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = [get_repo_path(project)]

        cls.base_remove(repopaths, 'rtd')
