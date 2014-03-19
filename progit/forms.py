#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from flask.ext import wtf
import wtforms


class ProjectForm(wtf.Form):
    ''' Form to create or edit project. '''
    name = wtforms.TextField(
        'Project name <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    description = wtforms.TextField(
        'description',
        [wtforms.validators.optional()]
    )
