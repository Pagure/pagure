# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os

import sqlalchemy as sa
import wtforms
try:
    from flask_wtf import FlaskForm as FlaskForm
except:
    from flask_wtf import Form as FlaskForm
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from pagure.hooks import BaseHook
from pagure.lib.model import BASE, Project
from pagure import APP, get_repo_path


class PagureTable(BASE):
    """ Stores information about the pagure hook deployed on a project.

    Table -- hook_pagure
    """

    __tablename__ = 'hook_pagure'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    project = relation(
        'Project', remote_side=[Project.id],
        backref=backref(
            'pagure_hook', cascade="delete, delete-orphan",
            single_parent=True, uselist=False)
    )


class PagureForm(FlaskForm):
    ''' Form to configure the pagure hook. '''
    active = wtforms.BooleanField(
        'Active',
        [wtforms.validators.Optional()]
    )


DESCRIPTION = '''
Pagure specific hook to add a comment to issues or pull requests if the pushed
commits fix them
or relate to them. This is determined based on the commit message.

To reference an issue/PR you need to use one of recognized keywords followed by
a reference to the issue or PR, separated by whitespace and and optional colon.
Such references can be either:

 * The issue/PR number preceded by the `#` symbol
 * The full URL of the issue or PR

If using the full URL, it is possible to reference issues in other projects.

The recognized keywords are:

 * fix/fixed/fixes
 * relate/related/relates
 * merge/merges/merged
 * close/closes/closed

Examples:

 * Fixes #21
 * related: https://pagure.io/myproject/issue/32
 * this commit merges #74
 * Merged: https://pagure.io/myproject/pull-request/74

Capitalization does not matter; neither does the colon between keyword and
number.


'''


class PagureHook(BaseHook):
    ''' Pagure hook. '''

    name = 'Pagure'
    description = DESCRIPTION
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

        cls.base_install(repopaths, dbobj, 'pagure', 'pagure_hook.py')

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

        cls.base_remove(repopaths, 'pagure')
