# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import sqlalchemy as sa
import pygit2
import wtforms
try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from pagure.hooks import BaseHook, RequiredIf
from pagure.lib.model import BASE, Project
from pagure import get_repo_path


class MailTable(BASE):
    """ Stores information about the irc hook deployed on a project.

    Table -- hook_mail
    """

    __tablename__ = 'hook_mail'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    mail_to = sa.Column(sa.Text, nullable=False)
    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        'Project', remote_side=[Project.id],
        backref=backref(
            'mail_hook', cascade="delete, delete-orphan",
            single_parent=True, uselist=False)
    )


class MailForm(FlaskForm):
    ''' Form to configure the mail hook. '''
    mail_to = wtforms.TextField(
        'Mail to',
        [RequiredIf('active')]
    )
    active = wtforms.BooleanField(
        'Active',
        [wtforms.validators.Optional()]
    )


class Mail(BaseHook):
    ''' Mail hooks. '''

    name = 'Mail'
    description = 'Generate notification emails for pushes to a git '\
        'repository. This hook sends emails describing changes introduced '\
        'by pushes to a git repository.'
    form = MailForm
    db_object = MailTable
    backref = 'mail_hook'
    form_fields = ['mail_to', 'active']

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = [get_repo_path(project)]
        repo_obj = pygit2.Repository(repopaths[0])

        # Configure the hook
        repo_obj.config.set_multivar(
            'multimailhook.mailingList',
            '',
            dbobj.mail_to
        )
        repo_obj.config.set_multivar(
            'multimailhook.environment', '', 'gitolite')

        # Install the hook itself
        cls.base_install(repopaths, dbobj, 'mail', 'git_multimail.py')

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = [get_repo_path(project)]
        cls.base_remove(repopaths, 'mail')
