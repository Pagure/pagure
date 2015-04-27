# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from functools import wraps

import flask
from sqlalchemy.exc import SQLAlchemyError

import pagure.forms
import pagure.lib
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



@APP.route('/admin/groups', methods=['GET', 'POST'])
@admin_required
def admin_groups():
    """ List of the groups present in the system
    """
    # Add new group if asked
    group_types = [
        grp.group_type
        for grp in pagure.lib.get_group_types(SESSION)
    ]
    # Make sure the admin type is always the last one
    group_types.remove('admin')
    group_types.append('admin')
    form = pagure.forms.NewGroupForm(group_types=group_types)
    user = pagure.lib.search_user(SESSION, username=flask.g.fas_user.username)
    if not user:
        return flask.abort(403)

    if form.validate_on_submit():
        grp = pagure.lib.model.PagureGroup()
        form.populate_obj(obj=grp)
        grp.user_id = user.id
        SESSION.add(grp)
        try:
            SESSION.flush()
            flask.flash('Group `%s` created.' % grp.group_name)
        except SQLAlchemyError as err:
            SESSION.rollback()
            flask.flash('Could not create group.')
            APP.logger.debug('Could not create group.')
            APP.logger.exception(err)

        SESSION.commit()

    groups = pagure.lib.search_groups(SESSION)

    return flask.render_template(
        'login/admin_groups.html',
        groups=groups,
        form=form,
        conf_form=pagure.forms.ConfirmationForm(),
    )


@APP.route('/admin/group/<group>', methods=['GET', 'POST'])
@admin_required
def admin_group(group):
    """ List of the users in a certain group
    """
    group_obj = pagure.lib.search_groups(SESSION, group_name=group)

    if not group_obj:
        flask.flash('No group `%s` found' % group, 'error')
        return flask.redirect(flask.url_for('.admin_groups'))

    # Add new user to the group if asked
    form = pagure.forms.AddUserForm()
    if form.validate_on_submit():
        user = pagure.lib.search_user(SESSION, username=form.user.data)
        if not user:
            flask.flash('No user `%s` found' % form.user.data, 'error')
            return flask.redirect(flask.url_for('.admin_group', group=group))

        grp = pagure.lib.model.PagureUserGroup(
            group_id=group_obj.id,
            user_id=user.id
        )
        SESSION.add(grp)
        try:
            SESSION.flush()
        except SQLAlchemyError as err:
            SESSION.rollback()
            flask.flash(
                'Could not add user `%s` to group `%s`.' % (
                    user.user, group_obj.group_name),
                'error')
            APP.logger.debug(
                'Could not add user `%s` to group `%s`.' % (
                    user.user, group_obj.group_name))
            APP.logger.exception(err)

        flask.flash('User `%s` added.' % user.user)
        SESSION.commit()

    return flask.render_template(
        'login/admin_users.html',
        form=form,
        conf_form=pagure.forms.ConfirmationForm(),
        group=group_obj,
    )


@APP.route('/admin/group/<group>/<user>/delete', methods=['POST'])
@admin_required
def admin_group_user_delete(user, group):
    """ Delete an user from a certain group
    """
    # Add new user to the group if asked
    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        group_obj = pagure.lib.search_groups(SESSION, group_name=group)

        if not group_obj:
            flask.flash('No group `%s` found' % group, 'error')
            return flask.redirect(flask.url_for('.admin_groups'))

        user = pagure.lib.search_user(SESSION, username=user)
        if not user:
            flask.flash('No user `%s` found' % user, 'error')
            return flask.redirect(flask.url_for('.admin_groups'))

        user_grp = pagure.lib.get_user_group(
            SESSION, user.id, group_obj.id)
        SESSION.delete(user_grp)

        SESSION.commit()
        flask.flash(
            'User `%s` removed from the group `%s`' % (user.user, group))

    return flask.redirect(flask.url_for('.admin_group', group=group))


@APP.route('/admin/group/<group>/delete', methods=['POST'])
@admin_required
def admin_group_delete(group):
    """ Delete a certain group
    """
    # Add new user to the group if asked
    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        group_obj = pagure.lib.search_groups(SESSION, group_name=group)

        if not group_obj:
            flask.flash('No group `%s` found' % group, 'error')
            return flask.redirect(flask.url_for('.admin_groups'))

        SESSION.delete(group_obj)

        SESSION.commit()
        flask.flash(
            'Group `%s` has been deleted' % (group))

    return flask.redirect(flask.url_for('.admin_groups'))
