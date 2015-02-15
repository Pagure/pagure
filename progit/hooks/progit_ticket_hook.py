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


class ProgitTicketsTable(BASE):
    """ Stores information about the progit tickets hook deployed on a project.

    Table -- hook_progit_tickets
    """

    __tablename__ = 'hook_progit_tickets'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        'Project', remote_side=[Project.id], backref='progit_hook_tickets',
        cascade="delete, delete-orphan", single_parent=True)


class ProgitTicketsForm(wtf.Form):
    ''' Form to configure the progit hook. '''
    active = wtforms.BooleanField(
        'Acive',
        [wtforms.validators.Optional()]
    )


class ProgitTicketHook(BaseHook):
    ''' Progit ticket hook. '''

    name = 'progit tickets'
    form = ProgitTicketsForm
    db_object = ProgitTicketsTable
    backref = 'progit_tickets_hook'
    form_fields = ['active']

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``progit.model.Project`` object to which the hook
            should be installed

        '''
        repopath = os.path.join(APP.config['TICKETS_FOLDER'], project.path)
        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')
        repo_obj = pygit2.Repository(repopath)

        # Install the hook itself
        shutil.copyfile(
            os.path.join(hook_files, 'progit_hook_tickets.py'),
            os.path.join(repopath, 'hooks', 'post-receive.progit')
        )
        os.chmod(
            os.path.join(repopath, 'hooks', 'post-receive.progit_tickets'),
            0755)

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``progit.model.Project`` object to which the hook
            should be installed

        '''
        repopath = os.path.join(APP.config['TICKETS_FOLDER'], project.path)
        hook_path = os.path.join(
            repopath, 'hooks', 'post-receive.progit_tickets')
        if os.path.exists(hook_path):
            os.unlink(hook_path)
