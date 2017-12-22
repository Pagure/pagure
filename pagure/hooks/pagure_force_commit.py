# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import sqlalchemy as sa
import pygit2
import wtforms
try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from pagure.hooks import BaseHook, RequiredIf
from pagure.lib.model import BASE, Project
from pagure.utils import get_repo_path


class PagureForceCommitTable(BASE):
    """ Stores information about the pagure hook deployed on a project.

    Table -- hook_pagure_force_commit
    """

    __tablename__ = 'hook_pagure_force_commit'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    branches = sa.Column(sa.Text, nullable=False)

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        'Project', foreign_keys=[project_id], remote_side=[Project.id],
        backref=backref(
            'pagure_force_commit_hook', cascade="delete, delete-orphan",
            single_parent=True, uselist=False)
    )


class PagureForceCommitForm(FlaskForm):
    ''' Form to configure the pagure hook. '''
    branches = wtforms.TextField(
        'Branches',
        [RequiredIf('active')]
    )

    active = wtforms.BooleanField(
        'Active',
        [wtforms.validators.Optional()]
    )


class PagureForceCommitHook(BaseHook):
    ''' PagurPagureForceCommit hook. '''

    name = 'Block non fast-forward pushes'
    description = 'Using this hook you can block any non-fast-forward '\
        'commit forced pushed to one or more branches.\n'\
        'You can specify one or more branch names (sperated them using '\
        'commas) or block all the branches by specifying: ``*``'
    form = PagureForceCommitForm
    db_object = PagureForceCommitTable
    backref = 'pagure_force_commit_hook'
    form_fields = ['branches', 'active']
    hook_type = 'pre-receive'

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        # Init the git repo in case
        repopaths = [get_repo_path(project)]
        pygit2.Repository(repopaths[0])

        cls.base_install(repopaths, dbobj, 'pagureforcecommit',
                         'pagure_force_commit_hook.py')

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = [get_repo_path(project)]
        cls.base_remove(repopaths, 'pagureforcecommit')
