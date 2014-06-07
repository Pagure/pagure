#-*- coding: utf-8 -*-

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

from progit.hooks import BaseHook
from progit.model import BASE, Project
from progit import SESSION, APP


class ProgitTable(BASE):
    """ Stores information about the progit hook deployed on a project.

    Table -- hook_progit
    """

    __tablename__ = 'hook_progit'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        'Project', remote_side=[Project.id], backref='progit_hook')


class ProgitForm(wtf.Form):
    ''' Form to configure the progit hook. '''
    active = wtforms.BooleanField(
        'Acive',
        [wtforms.validators.Optional()]
    )


class Debug(BaseHook):
    ''' Progit hook. '''

    name = 'Progit hooks for tickets'
    form = ProgitForm
    db_object = ProgitTable
    backref = 'progit_hook'
    form_fields = ['active']

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``progit.model.Project`` object to which the hook
            should be installed

        '''
        repopath = os.path.join(APP.config['GIT_FOLDER'], project.path)
        if project.is_fork:
            repopath = os.path.join(APP.config['FORK_FOLDER'], project.path)
        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')
        repo_obj = pygit2.Repository(repopath)

        # Install the hook itself
        shutil.copyfile(
            os.path.join(hook_files, 'progit.py'),
            os.path.join(repopath, 'hooks', 'post-receive.progit')
        )
        os.chmod(os.path.join(repopath, 'hooks', 'post-receive.progit'), 0755)

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``progit.model.Project`` object to which the hook
            should be installed

        '''
        repopath = os.path.join(APP.config['GIT_FOLDER'], project.path)
        if project.is_fork:
            repopath = os.path.join(APP.config['FORK_FOLDER'], project.path)
        os.unlink(os.path.join(repopath, 'hooks', 'post-receive.progit'))
