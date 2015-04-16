# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from functools import wraps

import flask

import pagure.forms
from pagure import (APP, SESSION,
                    generate_gitolite_acls, generate_authorized_key_file,
                    is_admin, admin_session_timedout)

# pylint: disable=E1101


def admin_required(function):
    """ Flask decorator to retrict access to admins of pagure.
    """
    @wraps(function)
    def decorated_function(*args, **kwargs):
        """ Decorated function, actually does the work. """
        if admin_session_timedout():
            return flask.redirect(
                flask.url_for('auth_login', next=flask.request.url))
        elif not is_admin():
            flask.flash('Access restricted', 'error')
            return flask.redirect(flask.url_for('.index'))

        return function(*args, **kwargs)
    return decorated_function


# Application


@APP.route('/admin')
@admin_required
def admin_index():
    """ Front page of the admin section of the application.
    """
    form = pagure.forms.ConfirmationForm()

    return flask.render_template(
        'admin_index.html', form=form,
    )


@APP.route('/admin/gitolite', methods=['POST'])
@admin_required
def admin_generate_acl():
    """ Regenerate the gitolite ACL file. """
    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        generate_gitolite_acls()
        flask.flash('Gitolite ACLs updated')
    return flask.redirect(flask.url_for('admin_index'))


@APP.route('/admin/ssh', methods=['POST'])
@admin_required
def admin_refresh_ssh():
    """ Regenerate the gitolite ACL file. """
    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        generate_authorized_key_file()
        flask.flash('Authorized file updated')
    return flask.redirect(flask.url_for('admin_index'))


@APP.route('/admin/hook_token', methods=['POST'])
@admin_required
def admin_generate_hook_token():
    """ Regenerate the hook_token for each projects in the DB. """
    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        pagure.lib.generate_hook_token(SESSION)
        flask.flash('Hook token all re-generated')
    return flask.redirect(flask.url_for('admin_index'))
