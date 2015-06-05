# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os

import sqlalchemy as sa
import wtforms
from flask.ext import wtf
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from pagure.hooks import BaseHook
from pagure.lib.model import BASE, Project
from pagure import get_repo_path


class FedmsgTable(BASE):
    """ Stores information about the fedmsg hook deployed on a project.

    Table -- hook_fedmsg
    """

    __tablename__ = 'hook_fedmsg'

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
            'fedmsg_hook', cascade="delete, delete-orphan",
            single_parent=True)
        )


class FedmsgForm(wtf.Form):
    ''' Form to configure the fedmsg hook. '''
    active = wtforms.BooleanField(
        'Active',
        [wtforms.validators.Optional()]
    )


class Fedmsg(BaseHook):
    ''' Fedmsg hooks. '''

    name = 'Fedmsg'
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
        repopath = get_repo_path(project)
        if not os.path.exists(repopath):
            flask.abort(404, 'No git repo found')

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')

        # Make sure the hooks folder exists
        hookfolder = os.path.join(repopath, 'hooks')
        if not os.path.exists(hookfolder):
            os.makedirs(hookfolder)

        # Install the hook itself
        hook_file = os.path.join(repopath, 'hooks', 'post-receive.fedmsg')
        if not os.path.exists(hook_file):
            os.symlink(
                os.path.join(hook_files, 'fedmsg_hook.py'),
                hook_file
            )

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopath = get_repo_path(project)

        hook_path = os.path.join(repopath, 'hooks', 'post-receive.fedmsg')
        if os.path.exists(hook_path):
            os.unlink(hook_path)
