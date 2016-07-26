# -*- coding: utf-8 -*-


import os
import uuid

import sqlalchemy as sa
import pygit2

from wtforms import validators, TextField, BooleanField
from flask.ext import wtf
from sqlalchemy.orm import relation, backref
from sqlalchemy.ext.declarative import declarative_base

from pagure.hooks import BaseHook, RequiredIf
from pagure.lib.model import BASE, Project
from pagure import get_repo_path
from pagure import APP, SESSION


class PagureCI(BASE):

    __tablename__ = 'hook_pagure_ci'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE',ondelete='CASCADE'),
        nullable=False,
        unique=False,
        index=True)
    pagure_ci_token = sa.Column(sa.String(32), nullable=True, unique=True,
                            index=True)

    active = sa.Column(sa.Boolean, nullable=False, default=False)
    display_name = sa.Column(sa.String(64), nullable=False, default='Jenkins')
    pagure_name = sa.Column(sa.String(255))

    jenkins_name = sa.Column(sa.String(255))
    jenkins_url = sa.Column(sa.String(255), nullable=False,
                            default='http://jenkins.fedorainfracloud.org/')
    jenkins_token = sa.Column(sa.String(64))

    project = relation(
        'Project',
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref(
            'hook_pagure_ci', cascade="delete, delete-orphan",
            single_parent=True)
    )

    def __init__(self):
        self.pagure_ci_token = uuid.uuid4().hex


class ConfigNotFound(Exception):
    pass


class Service(object):
    PAGURE = PagureCI.pagure_name
    JENKINS = PagureCI.jenkins_name


def get_configs(project_name, service):
    """Returns all configurations with given name on a service.

    :raises ConfigNotFound: when no configuration matches
    """
    cfg = SESSION.query(PagureCI).filter(
        service == project_name).all()
    if not cfg:
        raise ConfigNotFound(project_name)
    return cfg


class JenkinsForm(wtf.Form):

    '''Form to configure Jenkins hook'''

    pagure_name = TextField('Name of project in Pagure',
                            [validators.Required(),
                             validators.Length(max=255)])

    jenkins_name = TextField('Name of project in Jenkins',
                             [validators.Required(),
                              validators.Length(max=255)])

    jenkins_url = TextField('Jenkins URL',
                            [validators.Required(),
                             validators.Length(max=255)],
                            default='http://jenkins.fedorainfracloud.org/')

    jenkins_token = TextField('Jenkins token',
                              [validators.Required()])

    active = BooleanField('Active', [validators.Optional()])


class PagureCiHook(BaseHook):
    ''' Jenkins hooks. '''

    name = 'Pagure CI'
    description = 'This hook help to set up CI for the project'\
        ' the changes made by the pushes to the git repository.'
    form = JenkinsForm
    db_object = PagureCI
    backref = 'hook_pagure_ci'
    form_fields = [
        'pagure_name', 'jenkins_name',
        'jenkins_url', 'jenkins_token', 'active'
    ]

    @classmethod
    def set_up(cls, project):
        ''' Install the generic post-receive hook that allow us to call
        multiple post-receive hooks as set per plugin.
        '''
        pass

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        pass

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        pass
