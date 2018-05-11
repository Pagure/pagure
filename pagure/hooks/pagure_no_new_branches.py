# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Slavek Kabrda <bkabrda@redhat.com>

"""

from __future__ import unicode_literals

import os

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


class PagureNoNewBranchesTable(BASE):
    """ Stores information about the pagure hook deployed on a project.

    Table -- hook_pagure_no_new_branches
    """

    __tablename__ = 'hook_pagure_no_new_branches'

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
            'pagure_hook_no_new_branches',
            cascade="delete, delete-orphan",
            single_parent=True, uselist=False)
    )


class PagureNoNewBranchesForm(FlaskForm):
    ''' Form to configure the pagure hook. '''
    active = wtforms.BooleanField(
        'Active',
        [wtforms.validators.Optional()]
    )


class PagureNoNewBranchesHook(BaseHook):
    ''' PagureNoNewBranches hook. '''

    name = 'Prevent creating new branches by git push'
    description = 'This hook prevents creating new branches by git push.'
    form = PagureNoNewBranchesForm
    db_object = PagureNoNewBranchesTable
    backref = 'pagure_hook_no_new_branches'
    form_fields = ['active']
    hook_type = 'pre-receive'

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = [get_repo_path(project)]

        cls.base_install(repopaths, dbobj, 'pagure_no_new_branches',
                         'pagure_no_new_branches')

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        cls.base_remove(repopaths, 'pagure_no_new_branches')
