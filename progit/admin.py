#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask

from progit import (APP, SESSION, LOG, cla_required,
                    generate_gitolite_acls, generate_authorized_key_file)



### Application


@APP.route('/admin')
def admin_index():
    """ Front page of the admin section of the application.
    """

    return flask.render_template(
        'admin_index.html',
    )


@APP.route('/admin/gitolite')
def admin_generate_acl():
    """ Regenerate the gitolite ACL file. """
    generate_gitolite_acls()
    flask.flash('Gitolite ACLs updated')
    return flask.redirect(flask.url_for('admin_index'))


@APP.route('/admin/ssh')
def admin_refresh_ssh():
    """ Regenerate the gitolite ACL file. """
    generate_authorized_key_file()
    flask.flash('Authorized file updated')
    return flask.redirect(flask.url_for('admin_index'))
