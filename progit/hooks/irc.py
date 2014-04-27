#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from . import BaseHook

from flask.ext import wtf
import wtforms


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
    form = IrcForm()
    form_fields = [
        'server', 'port', 'room', 'nick', 'nick_pass', 'active', 'join',
        'ssl'
    ]
