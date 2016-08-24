# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


# # pylint cannot import flask extension correctly
# pylint: disable=E0611,F0401
# # The forms here don't have specific methods, they just inherit them.
# pylint: disable=R0903
# # We apparently use old style super in our __init__
# pylint: disable=E1002
# # Couple of our forms do not even have __init__
# pylint: disable=W0232


import flask_wtf as wtf
import wtforms

from pagure.forms import ConfirmationForm


def same_password(form, field):
    ''' Check if the data in the field is the same as in the password field.
    '''
    if field.data != form.password.data:
        raise wtforms.validators.ValidationError(
            'Both password fields should be equal')


class LostPasswordForm(wtf.Form):
    """ Form to ask for a password change. """
    username = wtforms.TextField(
        'username  <span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class ResetPasswordForm(wtf.Form):
    """ Form to reset one's password in the local database. """
    password = wtforms.PasswordField(
        'Password  <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    confirm_password = wtforms.PasswordField(
        'Confirm password  <span class="error">*</span>',
        [wtforms.validators.Required(), same_password]
    )


class LoginForm(wtf.Form):
    """ Form to login via the local database. """
    username = wtforms.TextField(
        'username  <span class="error">*</span>',
        [wtforms.validators.Required()]
    )
    password = wtforms.PasswordField(
        'Password  <span class="error">*</span>',
        [wtforms.validators.Required()]
    )


class NewUserForm(wtf.Form):
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


class ChangePasswordForm(wtf.Form):
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
