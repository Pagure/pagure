# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os

import flask
import sqlalchemy as sa
import pygit2
import wtforms
from flask.ext import wtf
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from pagure.hooks import BaseHook
from pagure.lib.model import BASE, Project
from pagure import APP


class PagureRequestsTable(BASE):
    """ Stores information about the pagure requests hook deployed on a
    project.

    Table -- hook_pagure_requests
    """

    __tablename__ = 'hook_pagure_requests'

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
            'pagure_hook_requests', cascade="delete, delete-orphan",
            single_parent=True)
        )


class PagureRequestsForm(wtf.Form):
    ''' Form to configure the pagure hook. '''
    active = wtforms.BooleanField(
        'Active',
        [wtforms.validators.Optional()]
    )


class PagureRequestHook(BaseHook):
    ''' Pagure request hook. '''

    name = 'pagure requests'
    description='Pagure specific hook to update pull-requests stored in the database based on the information pushed in the requests git repository.'
    form = PagureRequestsForm
    db_object = PagureRequestsTable
    backref = 'pagure_hook_requests'
    form_fields = ['active']

    @classmethod
    def set_up(cls, project):
        ''' Install the generic post-receive hook that allow us to call
        multiple post-receive hooks as set per plugin.
        '''
        repopath = os.path.join(APP.config['REQUESTS_FOLDER'], project.path)
        if not os.path.exists(repopath):
            flask.abort(404, 'No git repo found')

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')

        # Make sure the hooks folder exists
        hookfolder = os.path.join(repopath, 'hooks')
        if not os.path.exists(hookfolder):
            os.makedirs(hookfolder)

        # Install the main post-receive file
        postreceive = os.path.join(hookfolder, 'post-receive')
        hook_file = os.path.join(hook_files, 'post-receive')
        if not os.path.exists(postreceive):
            os.symlink(hook_file, postreceive)

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopath = os.path.join(APP.config['REQUESTS_FOLDER'], project.path)
        if not os.path.exists(repopath):  # pragma: no cover
            # We cannot test this as un-existing repo should be catched
            # at the set_up() stage
            flask.abort(404, 'No git repo found')

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')
        pygit2.Repository(repopath)

        # Install the hook itself
        hook_path = os.path.join(
            repopath, 'hooks', 'post-receive.pagure-requests')
        if not os.path.exists(hook_path):
            os.symlink(
                os.path.join(hook_files, 'pagure_hook_requests.py'),
                hook_path
            )

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopath = os.path.join(APP.config['REQUESTS_FOLDER'], project.path)
        if not os.path.exists(repopath):
            flask.abort(404, 'No git repo found')

        hook_path = os.path.join(
            repopath, 'hooks', 'post-receive.pagure-requests')
        if os.path.exists(hook_path):
            os.unlink(hook_path)
