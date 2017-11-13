# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import logging

import flask
from sqlalchemy.exc import SQLAlchemyError

import pagure.forms
import pagure.lib
import pagure.lib.git
from pagure.config import config as pagure_config
from pagure.ui import UI_NS
from pagure.utils import login_required


_log = logging.getLogger(__name__)


@UI_NS.route('/groups/')
@UI_NS.route('/groups')
def group_lists():
    ''' List all the groups associated with all the projects. '''

    group_type = 'user'
    if pagure.utils.is_admin():
        group_type = None
    groups = pagure.lib.search_groups(
        flask.g.session, group_type=group_type)

    group_types = ['user']
    if pagure.utils.is_admin():
        group_types = [
            grp.group_type
            for grp in pagure.lib.get_group_types(flask.g.session)
        ]
        # Make sure the admin type is always the last one
        group_types.remove('admin')
        group_types.append('admin')

    form = pagure.forms.NewGroupForm(group_types=group_types)

    return flask.render_template(
        'group_list.html',
        groups=groups,
        form=form,
    )


@UI_NS.route('/group/<group>/', methods=['GET', 'POST'])
@UI_NS.route('/group/<group>', methods=['GET', 'POST'])
def view_group(group):
    ''' Displays information about this group. '''
    if flask.request.method == 'POST' and \
            not pagure_config.get('ENABLE_USER_MNGT', True):
        flask.abort(404)

    group_type = 'user'
    if pagure.utils.is_admin():
        group_type = None
    group = pagure.lib.search_groups(
        flask.g.session, group_name=group, group_type=group_type)

    if not group:
        flask.abort(404, 'Group not found')

    # Add new user to the group if asked
    form = pagure.forms.AddUserToGroupForm()
    if flask.g.authenticated and form.validate_on_submit() \
            and pagure_config.get('ENABLE_GROUP_MNGT', False):

        username = form.user.data

        try:
            msg = pagure.lib.add_user_to_group(
                flask.g.session,
                username=username,
                group=group,
                user=flask.g.fas_user.username,
                is_admin=pagure.utils.is_admin(),
            )
            flask.g.session.commit()
            pagure.lib.git.generate_gitolite_acls(
                project=None, group=group.group_name)
            flask.flash(msg)
        except pagure.exceptions.PagureException as err:
            flask.g.session.rollback()
            flask.flash(err.message, 'error')
            return flask.redirect(
                flask.url_for('ui_ns.view_group', group=group.group_name))
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(
                'Could not add user `%s` to group `%s`.' % (
                    username, group.group_name),
                'error')
            _log.exception(
                'Could not add user `%s` to group `%s`.' % (
                    username, group.group_name))

    member = False
    if flask.g.authenticated:
        member = pagure.lib.is_group_member(
            flask.g.session,
            flask.g.fas_user.username, group.group_name)

    return flask.render_template(
        'group_info.html',
        group=group,
        form=form,
        member=member,
    )


@UI_NS.route('/group/<group>/edit/', methods=['GET', 'POST'])
@UI_NS.route('/group/<group>/edit', methods=['GET', 'POST'])
@login_required
def edit_group(group):
    ''' Allows editing the information about this group. '''
    if not pagure_config.get('ENABLE_USER_MNGT', True):
        flask.abort(404)

    group_type = 'user'
    is_admin = pagure.utils.is_admin()
    if is_admin:
        group_type = None
    group = pagure.lib.search_groups(
        flask.g.session, group_name=group, group_type=group_type)

    if not group:
        flask.abort(404, 'Group not found')

    # Edit group info
    form = pagure.forms.EditGroupForm()
    if form.validate_on_submit():

        try:
            msg = pagure.lib.edit_group_info(
                flask.g.session,
                group=group,
                display_name=form.display_name.data,
                description=form.description.data,
                user=flask.g.fas_user.username,
                is_admin=is_admin,
            )
            flask.g.session.commit()
            flask.flash(msg)
            return flask.redirect(
                flask.url_for('ui_ns.view_group', group=group.group_name))
        except pagure.exceptions.PagureException as err:
            flask.g.session.rollback()
            flask.flash(err.message, 'error')
            return flask.redirect(
                flask.url_for('ui_ns.view_group', group=group.group_name))
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(
                'Could not edit group `%s`.' % (group.group_name),
                'error')
            _log.exception(
                'Could not edit group `%s`.' % (group.group_name))
    elif flask.request.method == 'GET':
        form.display_name.data = group.display_name
        form.description.data = group.description

    return flask.render_template(
        'edit_group.html',
        group=group,
        form=form,
    )


@UI_NS.route('/group/<group>/<user>/delete', methods=['POST'])
@login_required
def group_user_delete(user, group):
    """ Delete an user from a certain group
    """
    if not pagure_config.get('ENABLE_USER_MNGT', True):
        flask.abort(404)

    if not pagure_config.get('ENABLE_GROUP_MNGT', False):
        flask.abort(404)

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():

        try:
            pagure.lib.delete_user_of_group(
                flask.g.session,
                username=user,
                groupname=group,
                user=flask.g.fas_user.username,
                is_admin=pagure.utils.is_admin()
            )
            flask.g.session.commit()
            pagure.lib.git.generate_gitolite_acls(project=None, group=group)
            flask.flash(
                'User `%s` removed from the group `%s`' % (user, group))
        except pagure.exceptions.PagureException as err:
            flask.g.session.rollback()
            flask.flash(err.message, 'error')
            return flask.redirect(
                flask.url_for('ui_ns.view_group', group=group))
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(
                'Could not remove user `%s` from the group `%s`.' % (
                    user.user, group),
                'error')
            _log.exception(
                'Could not remove user `%s` from the group `%s`.' % (
                    user.user, group))

    return flask.redirect(flask.url_for('ui_ns.view_group', group=group))


@UI_NS.route('/group/<group>/delete', methods=['POST'])
@login_required
def group_delete(group):
    """ Delete a certain group
    """
    if not pagure_config.get('ENABLE_USER_MNGT', True):
        flask.abort(404)

    if not pagure_config.get('ENABLE_GROUP_MNGT', False):
        flask.abort(404)

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        group_obj = pagure.lib.search_groups(
            flask.g.session, group_name=group)

        if not group_obj:
            flask.flash('No group `%s` found' % group, 'error')
            return flask.redirect(flask.url_for('ui_ns.group_lists'))

        user = pagure.lib.search_user(
            flask.g.session, username=flask.g.fas_user.username)
        if not user:
            flask.abort(404, 'User not found')

        if group not in user.groups:
            flask.flash(
                'You are not allowed to delete the group %s' % group, 'error')
            return flask.redirect(flask.url_for('ui_ns.group_lists'))

        flask.g.session.delete(group_obj)

        flask.g.session.commit()
        pagure.lib.git.generate_gitolite_acls(project=None)
        flask.flash(
            'Group `%s` has been deleted' % (group))

    return flask.redirect(flask.url_for('ui_ns.group_lists'))


@UI_NS.route('/group/add/', methods=['GET', 'POST'])
@UI_NS.route('/group/add', methods=['GET', 'POST'])
@login_required
def add_group():
    """ Endpoint to create groups
    """
    if not pagure_config.get('ENABLE_USER_MNGT', True):
        flask.abort(404)

    if not pagure_config.get('ENABLE_GROUP_MNGT', False):
        flask.abort(404)

    user = pagure.lib.search_user(
        flask.g.session, username=flask.g.fas_user.username)
    if not user:  # pragma: no cover
        return flask.abort(403)

    group_types = ['user']
    if pagure.utils.is_admin():
        group_types = [
            grp.group_type
            for grp in pagure.lib.get_group_types(flask.g.session)
        ]
        # Make sure the admin type is always the last one
        group_types.remove('admin')
        group_types.append('admin')

    form = pagure.forms.NewGroupForm(group_types=group_types)

    if not pagure.utils.is_admin():
        form.group_type.data = 'user'

    if form.validate_on_submit():

        try:
            group_name = form.group_name.data.strip()
            display_name = form.display_name.data.strip()
            description = form.description.data.strip()

            msg = pagure.lib.add_group(
                session=flask.g.session,
                group_name=group_name,
                display_name=display_name,
                description=description,
                group_type=form.group_type.data,
                user=flask.g.fas_user.username,
                is_admin=pagure.utils.is_admin(),
                blacklist=pagure_config['BLACKLISTED_GROUPS'],
            )
            flask.g.session.commit()
            flask.flash('Group `%s` created.' % group_name)
            flask.flash(msg)
            return flask.redirect(flask.url_for('ui_ns.group_lists'))
        except pagure.exceptions.PagureException as err:
            flask.g.session.rollback()
            flask.flash(err.message, 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash('Could not create group.')
            _log.exception('Could not create group.')

    return flask.render_template(
        'add_group.html',
        form=form,
    )
