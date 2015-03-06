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

from progit.hooks import BaseHook
from progit.lib.model import BASE, Project
from progit import SESSION, APP, get_repo_path


class MailTable(BASE):
    """ Stores information about the irc hook deployed on a project.

    Table -- hook_mail
    """

    __tablename__ = 'hook_mail'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    mail_to = sa.Column(sa.Text, nullable=False)
    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        'Project', remote_side=[Project.id], backref='mail_hook',
        cascade="delete, delete-orphan", single_parent=True)


class MailForm(wtf.Form):
    ''' Form to configure the mail hook. '''
    mail_to = wtforms.TextField(
        'Mail to <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    active = wtforms.BooleanField(
        'Acive',
        [wtforms.validators.Optional()]
    )


class Mail(BaseHook):
    ''' Mail hooks. '''

    name = 'Mail'
    form = MailForm
    db_object = MailTable
    backref = 'mail_hook'
    form_fields = ['mail_to', 'active']

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
        repo_obj.config.set_multivar(
            'multimailhook.mailingList',
            '',
            dbobj.mail_to
        )
        repo_obj.config.set_multivar(
            'multimailhook.environment', '', 'gitolite')

        # Install the hook itself
        shutil.copyfile(
            os.path.join(hook_files, 'git_multimail.py'),
            os.path.join(repopath, 'hooks', 'post-receive.mail')
        )
        os.chmod(os.path.join(repopath, 'hooks', 'post-receive.mail'), 0755)

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``progit.model.Project`` object to which the hook
            should be installed

        '''
        repopath = get_repo_path(project)

        hook_path = os.path.join(repopath, 'hooks', 'post-receive.mail')
        if os.path.exists(hook_path):
            os.unlink(hook_path)
