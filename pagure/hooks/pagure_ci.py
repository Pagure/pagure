# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os

import sqlalchemy as sa
import wtforms
from flask.ext import wtf
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from pagure.hooks import BaseHook, RequiredIf
from pagure.lib.model import BASE, Project, TypeCi
from pagure import get_repo_path, SESSION, APP


class PagureCITable(BASE):
    """ Stores information about the CI linked to on a project.

    Table -- hook_pagure_ci
    """

    __tablename__ = 'hook_pagure_ci'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True)
    pagure_ci_token = sa.Column(
        sa.String(32),
        nullable=True,
        unique=True,
        index=True)
    type_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'type_ci.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        unique=True)
    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        'Project', remote_side=[Project.id],
        backref=backref(
            'ci_hook', cascade="delete, delete-orphan",
            single_parent=True)
    )

    type_ci = relation(
        'TypeCi', remote_side=[TypeCi.id],
    )


class PagureCiForm(wtf.Form):
    ''' Form to configure the CI hook. '''
    type_ci = wtforms.SelectField(
        'Type of CI service',
        [RequiredIf('active')],
        choices=[]
    )
    jenkins_url = wtforms.TextField(
        'URL to the project on the CI service',
        [RequiredIf('active'), wtforms.validators.Length(max=255)],
    )
    jenkins_token = wtforms.TextField(
        'CI token',
        [RequiredIf('active')],
    )
    active = wtforms.BooleanField(
        'Active',
        [wtforms.validators.Optional()]
    )

    def __init__(self, *args, **kwargs):
        """ Calls the default constructor with the normal argument but
        uses the list of collection provided to fill the choices of the
        drop-down list.
        """
        super(PagureCiForm, self).__init__(*args, **kwargs)

        types = APP.config.get('PAGURE_CI_SERVICES', [])
        self.type_ci.choices = [
            (ci_type, ci_type) for ci_type in types
        ]


class PagureCi(BaseHook):
    ''' Mail hooks. '''

    name = 'Pagure CI'
    description = 'Generate notification emails for pushes to a git repository. '\
        'This hook sends emails describing changes introduced by pushes to a git repository.'
    form = PagureCiForm
    db_object = PagureCITable
    backref = 'ci_hook'
    form_fields = ['type_ci', 'jenkins_url', 'jenkins_token', 'active']

    @classmethod
    def set_up(cls, project):
        ''' Install the generic post-receive hook that allow us to call
        multiple post-receive hooks as set per plugin.
        '''
        pass

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        pass

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        pass
