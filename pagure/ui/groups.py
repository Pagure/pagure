# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import os

from sqlalchemy.exc import SQLAlchemyError

import pagure
import pagure.forms
import pagure.lib


# pylint: disable=E1101

# URLs

@pagure.APP.route('/groups')
def group_lists():
    ''' List all the groups associated with all the projects. '''
    groups = pagure.lib.search_groups(pagure.SESSION, grp_type='user')

    return flask.render_template(
        'group_list.html',
        groups=groups,
    )


@pagure.APP.route('/group/<group>', methods=['GET', 'POST'])
def view_group(group):
    ''' Displays information about this group. '''
    group = pagure.lib.search_groups(
        pagure.SESSION, grp_name=group, grp_type='user')

    if not group:
        flask.abort(404, 'Group not found')

    # Add new user to the group if asked
    form = pagure.forms.AddUserForm()
    if pagure.authenticated() and form.validate_on_submit():

        if not group.group_name in flask.g.fas_user.groups:
            flask.flash('Action restricted', 'error')
            return flask.redirect(flask.url_for('.view_group', group=group))

        username = form.user.data

        try:
            msg = pagure.lib.add_user_to_group(
                pagure.SESSION, username, group,
                flask.g.fas_user.username)
            pagure.SESSION.commit()
            flask.flash(msg)
        except pagure.exceptions.PagureException, err:
            SESSION.rollback()
            flask.flash(err.message, 'error')
            return flask.redirect(flask.url_for('.view_group', group=group))
        except SQLAlchemyError as err:
            pagure.SESSION.rollback()
            flask.flash(
                'Could not add user `%s` to group `%s`.' % (
                    user.user, group.group_name),
                'error')
            pagure.APP.logger.debug(
                'Could not add user `%s` to group `%s`.' % (
                    user.user, group.group_name))
            pagure.APP.logger.exception(err)


    return flask.render_template(
        'group_info.html',
        group=group,
        form=form,
    )


@pagure.APP.route('/group/<group>/<user>/delete', methods=['POST'])
@pagure.cla_required
def group_user_delete(user, group):
    """ Delete an user from a certain group
    """
    # Add new user to the group if asked
    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        group_obj = pagure.lib.search_groups(SESSION, grp_name=group)

        if not group_obj:
            flask.flash('No group `%s` found' % group, 'error')
            return flask.redirect(flask.url_for('.view_group', group=group))

        user = pagure.lib.search_user(SESSION, username=user)
        if not user:
            flask.flash('No user `%s` found' % user, 'error')
            return flask.redirect(flask.url_for('.view_group', group=group))

        if user == group_obj.creator:
            flask.flash('The creator of a group cannot be removed', 'error')
            return flask.redirect(flask.url_for('.view_group', group=group))

        user_grp = pagure.lib.get_user_group(
            SESSION, user.id, group_obj.id)
        SESSION.delete(user_grp)

        SESSION.commit()
        flask.flash(
            'User `%s` removed from the group `%s`' % (user.user, group))

    return flask.redirect(flask.url_for('.view_group', group=group))


@pagure.APP.route('/group/<group>/delete', methods=['POST'])
@pagure.cla_required
def group_delete(group):
    """ Delete a certain group
    """
    # Add new user to the group if asked
    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        group_obj = pagure.lib.search_groups(pagure.SESSION, grp_name=group)

        if not group_obj:
            flask.flash('No group `%s` found' % group, 'error')
            return flask.redirect(flask.url_for('.group_lists'))

        pagure.SESSION.delete(group_obj)

        pagure.SESSION.commit()
        flask.flash(
            'Group `%s` has been deleted' % (group))

    return flask.redirect(flask.url_for('.group_lists'))
