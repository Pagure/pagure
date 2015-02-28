# -*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from functools import wraps

import flask

from progit import (APP, SESSION, LOG, cla_required, authenticated,
                    generate_gitolite_acls, generate_authorized_key_file,
                    is_admin)


def admin_required(function):
    """ Flask decorator to retrict access to admins of progit.
    """
    @wraps(function)
    def decorated_function(*args, **kwargs):
        """ Decorated function, actually does the work. """
        if not authenticated():
            return flask.redirect(
                flask.url_for('auth_login', next=flask.request.url))
        elif not is_admin():
            flask.flash('Access restricted', 'error')
            return flask.redirect(flask.url_for('.index'))
        return function(*args, **kwargs)
    return decorated_function


### Application


@APP.route('/admin')
@admin_required
def admin_index():
    """ Front page of the admin section of the application.
    """

    return flask.render_template(
        'admin_index.html',
    )


@APP.route('/admin/gitolite')
@admin_required
def admin_generate_acl():
    """ Regenerate the gitolite ACL file. """
    generate_gitolite_acls()
    flask.flash('Gitolite ACLs updated')
    return flask.redirect(flask.url_for('admin_index'))


@APP.route('/admin/ssh')
@admin_required
def admin_refresh_ssh():
    """ Regenerate the gitolite ACL file. """
    generate_authorized_key_file()
    flask.flash('Authorized file updated')
    return flask.redirect(flask.url_for('admin_index'))
