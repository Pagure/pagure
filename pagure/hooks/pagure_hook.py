# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os
import shutil

import sqlalchemy as sa
import pygit2
import wtforms
from flask.ext import wtf
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from pagure.hooks import BaseHook
from pagure.lib.model import BASE, Project
from pagure import SESSION, APP, get_repo_path


class PagureTable(BASE):
    """ Stores information about the pagure hook deployed on a project.

    Table -- hook_pagure
    """

    __tablename__ = 'hook_pagure'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        'Project', remote_side=[Project.id],
        backref=backref(
            'pagure_hook', cascade="delete, delete-orphan",
            single_parent=True)
        )


class PagureForm(wtf.Form):
    ''' Form to configure the pagure hook. '''
    active = wtforms.BooleanField(
        'Acive',
        [wtforms.validators.Optional()]
    )


class PagureHook(BaseHook):
    ''' Pagure hook. '''

    name = 'pagure'
    form = PagureForm
    db_object = PagureTable
    backref = 'pagure_hook'
    form_fields = ['active']

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = [get_repo_path(project)]
        for folder in [
                APP.config.get('DOCS_FOLDER'),
                APP.config.get('REQUESTS_FOLDER')]:
            repopaths.append(
                os.path.join(folder, project.path)
            )

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')
        hook_file = os.path.join(hook_files, 'pagure_hook.py')

        for repopath in repopaths:
            print repopath
            # Init the git repo in case
            repo_obj = pygit2.Repository(repopath)

            # Install the hook itself
            hook_path = os.path.join(
                repopath, 'hooks', 'post-receive.pagure')
            os.symlink(hook_file, hook_path)
            os.chmod(hook_path, 0755)

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = [get_repo_path(project)]
        for folder in [
                APP.config.get('DOCS_FOLDER'),
                APP.config.get('REQUESTS_FOLDER')]:
            repopaths.append(
                os.path.join(folder, project.path)
            )

        for repopath in repopaths:
            hook_path = os.path.join(
                repopath, 'hooks', 'post-receive.pagure')
            if os.path.exists(hook_path):
                os.unlink(hook_path)
