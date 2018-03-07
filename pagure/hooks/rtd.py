# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


import sqlalchemy as sa
import wtforms

try:
    from flask_wtf import FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm
from sqlalchemy.orm import relation
from sqlalchemy.orm import backref

from pagure.hooks import BaseHook, RequiredIf
from pagure.lib.model import BASE, Project
from pagure.utils import get_repo_path


class RtdTable(BASE):
    """ Stores information about the pagure hook deployed on a project.

    Table -- hook_rtd
    """

    __tablename__ = 'hook_rtd'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE', ondelete='CASCADE'),
        nullable=False,
        unique=True,
        index=True)

    active = sa.Column(sa.Boolean, nullable=False, default=False)

    branches = sa.Column(sa.Text, nullable=True)
    api_url = sa.Column(sa.Text, nullable=False)
    api_token = sa.Column(sa.Text, nullable=False)

    project = relation(
        'Project', remote_side=[Project.id],
        backref=backref(
            'rtd_hook', cascade="delete, delete-orphan",
            single_parent=True, uselist=False)
    )


class RtdForm(FlaskForm):
    ''' Form to configure the pagure hook. '''
    api_url = wtforms.TextField(
        'URL endpoint used to trigger the builds',
        [wtforms.validators.Optional()]
    )
    api_token = wtforms.TextField(
        'API token provided by readthedocs',
        [wtforms.validators.Optional()]
    )
    branches = wtforms.TextField(
        'Restrict build to these branches only (comma separated)',
        [wtforms.validators.Optional()]
    )

    active = wtforms.BooleanField(
        'Active',
        [wtforms.validators.Optional()]
    )


DESCRIPTION = '''
Git hook to trigger building documentation on the readthedocs.org service
when a commit is pushed to the repository.

If you specify one or more branches (using commas `,` to separate them) only
pushes made to these branches will trigger a new build of the documentation.

To set up this hook, you will need to login to https://readthedocs.org/
Go to your project's adming settings, and in the ``Integrations`` section
add a new ``Generic API incoming webhook``.

This will give you access to one URL and one API token, both of which you
will have to provide below.

'''


class RtdHook(BaseHook):
    ''' Read The Doc hook. '''

    name = 'Read the Doc'
    description = DESCRIPTION
    form = RtdForm
    db_object = RtdTable
    backref = 'rtd_hook'
    form_fields = ['active', 'api_url', 'api_token', 'branches']

    @classmethod
    def install(cls, project, dbobj):
        ''' Method called to install the hook for a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = [get_repo_path(project)]

        cls.base_install(repopaths, dbobj, 'rtd', 'rtd_hook.py')

    @classmethod
    def remove(cls, project):
        ''' Method called to remove the hook of a project.

        :arg project: a ``pagure.model.Project`` object to which the hook
            should be installed

        '''
        repopaths = [get_repo_path(project)]

        cls.base_remove(repopaths, 'rtd')
