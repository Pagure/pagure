# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os

import sqlalchemy as sa
import pygit2
from wtforms import validators, TextField, BooleanField
from flask.ext import wtf
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref
from sqlalchemy.ext.declarative import declarative_base

from pagure.hooks import BaseHook, RequiredIf
from pagure.lib.model import BASE, Project
from pagure import get_repo_path


class PagureCI(BASE):

    __tablename__ = 'hook_pagure_ci'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
            sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=False,
        unique=False,
        index=True)

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    name = sa.Column(sa.String(64))
    pagure_name = sa.Column(sa.String(255))
    pagure_url = sa.Column(sa.String(255))
    pagure_token = sa.Column(sa.String(64))

    jenkins_name = sa.Column(sa.String(255))
    jenkins_url = sa.Column(sa.String(255))
    jenkins_token = sa.Column(sa.String(64))
    hook_token = sa.Column(sa.String(64),
            nullable=True,
            unique=True,
            index=True)

    project = relation(
        'Project',
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref(
            'hook_pagure_ci', cascade="delete, delete-orphan",
            single_parent=True)
    )
    def __init__(self, name = None, display_name = None, owner = None,
                 pagure_name = None, pagure_url = None, pagure_token = None,
                 jenkins_name = None, jenkins_url = None, jenkins_token = None,
                 hook_token = None, active = False):
        self.name = name
        self.display_name = display_name
        self.owner = owner
        self.pagure_name = pagure_name
        self.pagure_url = pagure_url
        self.pagure_token = pagure_token

        self.jenkins_name = jenkins_name
        self.jenkins_url = jenkins_url
        self.jenkins_token = jenkins_token

        self.hook_token = hook_token
        self.active = active

    def __repr__(self):
        return '<PagureCI {.name}>'.format(self)

class ConfigNotFound(Exception):
    pass


class Service(object):
    PAGURE = PagureCI.pagure_name
    JENKINS = PagureCI.jenkins_name


def get_configs(project_name, service):
    """Returns all configurations with given name on a service.

    :raises ConfigNotFound: when no configuration matches
    """
    cfg = BASE.metadata.bind.query(PagureCI).filter(service == project_name).all()
    if len(cfg) == 0:
        raise ConfigNotFound(project_name)
    return cfg


class JenkinsForm(wtf.Form):

    '''Form to configure Jenkins hook'''
    name = TextField('Name',
                     [validators.Required(),
                      validators.Length(max=64)])
    display_name = TextField('Display name',
                             [validators.Required(),
                              validators.Length(max=64)],
                             default='Jenkins')
    pagure_name = TextField('Name of project in Pagure',
                            [validators.Required(),
                             validators.Length(max=255)])
    pagure_url = TextField('Pagure URL',
                           [validators.Required(),
                            validators.Length(max=255)],
                           default='https://pagure.io/')
    pagure_token = TextField('Pagure token',
                             [validators.Required()])

    jenkins_name = TextField('Name of project in Jenkins',
                             [validators.Required(),
                              validators.Length(max=255)])
    jenkins_url = TextField('Jenkins URL',
                            [validators.Required(),
                             validators.Length(max=255)],
                            default='http://jenkins.fedorainfracloud.org/')
    jenkins_token = TextField('Jenkins token',
                              [validators.Required()])
    active = BooleanField('Active',[validators.Optional()])


class Hook(BaseHook):
    ''' Jenkins hooks. '''

    name = 'Jenkins Hook'
    description = 'This hook help to set up CI for the project'\
        ' the changes made by the pushes to the git repository.'
    form = JenkinsForm
    db_object = PagureCI
    backref = 'pagure_ci_hook'
    form_fields = [
        'display_name','name', 'pagure_name', 'pagure_url', 'pagure_token', 'jenkins_name',
        'jenkins_url', 'jenkins_token','active'
    ]

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopath = get_repo_path(project)

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')
        repo_obj = pygit2.Repository(repopath)

        # Configure the hook
        #repo_obj.config.set_multivar(dbobj)

        # Install the hook itself
        hook_file = os.path.join(hook_files, 'jenkins_hook.py')
        if not os.path.exists(hook_file):
            os.symlink(
                hook_file,
                os.path.join(repopath, 'hooks', 'jenkins_hook.py')
            )

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopath = get_repo_path(project)

        #hook_path = os.path.join(repopath, 'hooks', 'post-receive.irc')
        #if os.path.exists(hook_path):
            #os.unlink(hook_path)
