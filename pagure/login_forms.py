# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


# # pylint cannot import flask extension correctly
# pylint: disable=no-name-in-module
# pylint: disable=import-error
# # The forms here don't have specific methods, they just inherit them.
# pylint: disable=too-few-public-methods
# # We apparently use old style super in our __init__
# pylint: disable=super-on-old-class
# # Couple of our forms do not even have __init__
# pylint: disable=no-init


from __future__ import unicode_literals

import wtforms
try:
    from flask_wtf import FlaskForm as FlaskForm
except ImportError:
    from flask_wtf import Form as FlaskForm


def same_password(form, field):
    ''' Check if the data in the field is the same as in the password field.
    '''
    if field.data != form.password.data:
        raise wtforms.validators.ValidationError(
            'Both password fields should be equal')


class LostPasswordForm(FlaskForm):
    """ Form to ask for a password change. """
    username = wtforms.TextField(
        'username  <span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class ResetPasswordForm(FlaskForm):
    """ Form to reset one's password in the local database. """
    password = wtforms.PasswordField(
        'Password  <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    confirm_password = wtforms.PasswordField(
        'Confirm password  <span class="error">*</span>',
        [wtforms.validators.Required(), same_password]
    )


class LoginForm(FlaskForm):
    """ Form to login via the local database. """
    username = wtforms.TextField(
        'username  <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    password = wtforms.PasswordField(
        'Password  <span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class NewUserForm(FlaskForm):
    """ Form to add a new user to the local database. """
    user = wtforms.TextField(
        'username  <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    fullname = wtforms.TextField(
        'Full name',
        [wtforms.validators.Optional()]
    )
    email_address = wtforms.TextField(
        'Email address  <span class="error">*</span>',
        [wtforms.validators.Required(), wtforms.validators.Email()]
    )
    password = wtforms.PasswordField(
        'Password  <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    confirm_password = wtforms.PasswordField(
        'Confirm password  <span class="error">*</span>',
        [wtforms.validators.Required(), same_password]
    )


class ChangePasswordForm(FlaskForm):
    """ Form to reset one's password in the local database. """
    old_password = wtforms.PasswordField(
        'Old Password  <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    password = wtforms.PasswordField(
        'Password  <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    confirm_password = wtforms.PasswordField(
        'Confirm password  <span class="error">*</span>',
        [wtforms.validators.Required(), same_password]
    )
