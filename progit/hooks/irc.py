# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

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

from progit.hooks import BaseHook, RequiredIf
from progit.lib.model import BASE, Project
from progit import SESSION, APP, get_repo_path


class IrcTable(BASE):
    """ Stores information about the irc hook deployed on a project.

    Table -- hook_irc
    """

    __tablename__ = 'hook_irc'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    server = sa.Column(sa.Text, nullable=False)
    port = sa.Column(sa.Text, nullable=False)
    room = sa.Column(sa.Text, nullable=False)
    nick = sa.Column(sa.Text, nullable=True, default=None)
    nick_pass = sa.Column(sa.Text, nullable=True, default=None)
    active = sa.Column(sa.Boolean, nullable=False, default=False)
    join = sa.Column(sa.Boolean, nullable=False, default=True)
    ssl = sa.Column(sa.Boolean, nullable=False, default=True)

    project = relation(
        'Project', remote_side=[Project.id],
        backref=backref(
            'irc_hook', cascade="delete, delete-orphan",
            single_parent=True)
        )


class IrcForm(wtf.Form):
    ''' Form to configure the irc hook. '''
    server = wtforms.TextField(
        'Server <span class="error">*</span>',
        [RequiredIf('active')]
    )
    port = wtforms.TextField(
        'Port <span class="error">*</span>',
        [RequiredIf('active')]
    )
    room = wtforms.TextField(
        'Room <span class="error">*</span>',
        [RequiredIf('active')]
    )
    nick = wtforms.TextField(
        'Nick',
        [wtforms.validators.Optional()]
    )
    nick_pass = wtforms.TextField(
        'Nickserv Password',
        [wtforms.validators.Optional()]
    )

    active = wtforms.BooleanField(
        'Acive',
        [wtforms.validators.Optional()]
    )
    join = wtforms.BooleanField(
        'Message Without Join',
        [wtforms.validators.Optional()]
    )
    ssl = wtforms.BooleanField(
        'Use SSL',
        [wtforms.validators.Optional()]
    )


class Hook(BaseHook):
    ''' IRC hooks. '''

    name = 'IRC'
    form = IrcForm
    db_object = IrcTable
    backref = 'irc_hook'
    form_fields = [
        'server', 'port', 'room', 'nick', 'nick_pass', 'active', 'join',
        'ssl'
    ]

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``progit.model.Project`` object to which the hook
            should be installed

        '''
        repopath = get_repo_path(project)

        hook_files = os.path.join(
            os.path.dirname(os.path.realpath(__file__)), 'files')
        repo_obj = pygit2.Repository(repopath)

        # Configure the hook
        # repo_obj.config.set_multivar()

        # Install the hook itself
        #shutil.copyfile(
            #os.path.join(hook_files, 'git_irc.py'),
            #os.path.join(repopath, 'hooks', 'post-receive.irc')
        #)
        #os.chmod(os.path.join(repopath, 'hooks', 'post-receive.irc'), 0755)

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``progit.model.Project`` object to which the hook
            should be installed

        '''
        repopath = get_repo_path(project)

        #hook_path = os.path.join(repopath, 'hooks', 'post-receive.irc')
        #if os.path.exists(hook_path):
            #os.unlink(hook_path)
