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
        user = pagure.lib.search_user(pagure.SESSION, username=username)
        if not user:
            flask.flash('No user `%s` found' % username, 'error')
            return flask.redirect(flask.url_for('.view_group', group=group))

        try:
            msg = pagure.lib.add_user_to_group(
                pagure.SESSION, username, group,
                flask.g.fas_user.username)
            pagure.SESSION.commit()
            flask.flash(msg)
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
