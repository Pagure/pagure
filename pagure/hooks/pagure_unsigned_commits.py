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


class PagureUnsignedCommitTable(BASE):
    """ Stores information about the pagure hook deployed on a project.

    Table -- hook_pagure_unsigned_commit
    """

    __tablename__ = 'hook_pagure_unsigned_commit'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        'Project', foreign_keys=[project_id], remote_side=[Project.id],
        backref=backref(
            'pagure_unsigned_commit_hook', cascade="delete, delete-orphan",
            single_parent=True)
    )


class PagureUnsignedCommitForm(wtf.Form):
    ''' Form to configure the pagure hook. '''

    active = wtforms.BooleanField(
        'Active',
        [wtforms.validators.Optional()]
    )


class PagureUnsignedCommitHook(BaseHook):
    ''' PagurPagureUnsignedCommit hook. '''

    name = 'Block Un-Signed commits'
    description = 'Using this hook you can block any push with commits '\
        'missing a "Signed-Off-By"'
    form = PagureUnsignedCommitForm
    db_object = PagureUnsignedCommitTable
    backref = 'pagure_unsigned_commit_hook'
    form_fields = ['active']
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
        hook_file = os.path.join(hook_files, 'pagure_block_unsigned.py')

        # Init the git repo in case
        pygit2.Repository(repopath)

        # Install the hook itself
        hook_path = os.path.join(
            repopath, 'hooks', 'pre-receive.pagureunsignedcommit')
        if not os.path.exists(hook_path):
            os.symlink(hook_file, hook_path)

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopath = get_repo_path(project)
        hook_path = os.path.join(
            repopath, 'hooks', 'pre-receive.pagureunsignedcommit')
        if os.path.exists(hook_path):
            os.unlink(hook_path)
