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


class PagureForceCommitTable(BASE):
    """ Stores information about the pagure hook deployed on a project.

    Table -- hook_pagure_force_commit
    """

    __tablename__ = 'hook_pagure_force_commit'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    branches = sa.Column(sa.Text, nullable=False)

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        'Project', foreign_keys=[project_id], remote_side=[Project.id],
        backref=backref(
            'pagure_force_commit_hook', cascade="delete, delete-orphan",
            single_parent=True)
    )


class PagureForceCommitForm(wtf.Form):
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
        'commit forced pushed to one or more branches'
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
        repopath = get_repo_path(project)

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')
        hook_file = os.path.join(hook_files, 'pagure_force_commit_hook.py')

        # Init the git repo in case
        pygit2.Repository(repopath)

        # Install the hook itself
        hook_path = os.path.join(
            repopath, 'hooks', 'pre-receive.pagureforcecommit')
        if not os.path.exists(hook_path):
            os.symlink(hook_file, hook_path)

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = get_repo_path(project)
        hook_path = os.path.join(
            repopath, 'hooks', 'pre-receive.pagureforcecommit')
        if os.path.exists(hook_path):
            os.unlink(hook_path)
