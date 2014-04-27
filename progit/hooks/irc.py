#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from flask.ext import wtf
import sqlalchemy as sa
import wtforms

from progit.hooks import BaseHook
from progit.model import BASE
from progit import SESSION


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
        index=True)

    server = sa.Column(sa.Text, nullable=False)
    port = sa.Column(sa.Text, nullable=False)
    room = sa.Column(sa.Text, nullable=False)
    nick = sa.Column(sa.Text, nullable=True, default=None)
    nick_pass = sa.Column(sa.Text, nullable=True, default=None)
    active = sa.Column(sa.Boolean, nullable=False, default=False)
    join = sa.Column(sa.Boolean, nullable=False, default=True)
    ssl = sa.Column(sa.Boolean, nullable=False, default=True)


class IrcForm(wtf.Form):
    ''' Form to configure the irc hook. '''
    server = wtforms.TextField(
        'Server <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    port = wtforms.TextField(
        'Port <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    room = wtforms.TextField(
        'Room <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    nick = wtforms.TextField(
        'Nick <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    nick_pass = wtforms.TextField(
        'Nickserv Password <span class="error">*</span>',
        [wtforms.validators.Required()]
    )

    active = wtforms.BooleanField(
        'Acive',
        [wtforms.validators.Required()]
    )
    join = wtforms.BooleanField(
        'Message Without Join',
        [wtforms.validators.Required()]
    )
    ssl = wtforms.BooleanField(
        'Use SSL',
        [wtforms.validators.Required()]
    )


class Hook(BaseHook):
    ''' IRC hooks. '''

    name = 'IRC'
    form = IrcForm
    form_fields = [
        'server', 'port', 'room', 'nick', 'nick_pass', 'active', 'join',
        'ssl'
    ]
