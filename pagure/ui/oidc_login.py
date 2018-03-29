# -*- coding: utf-8 -*-

"""
 (c) 2014-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

import logging

import flask
import munch
from sqlalchemy.exc import SQLAlchemyError

import pagure
from pagure.config import config as pagure_config
from pagure.flask_app import logout
from pagure.utils import is_admin

from flask_oidc import OpenIDConnect
oidc = OpenIDConnect()


_log = logging.getLogger(__name__)


def fas_user_from_oidc():
    if oidc.user_loggedin and 'oidc_logintime' in flask.session:
        email_key, fulln_key, usern_key, ssh_key, groups_key = [
            pagure_config['OIDC_PAGURE_EMAIL'],
            pagure_config['OIDC_PAGURE_FULLNAME'],
            pagure_config['OIDC_PAGURE_USERNAME'],
            pagure_config['OIDC_PAGURE_SSH_KEY'],
            pagure_config['OIDC_PAGURE_GROUPS'],
        ]
        info = oidc.user_getinfo(
            [email_key, fulln_key, usern_key, ssh_key, groups_key]
        )
        username = info.get(usern_key)
        if not username:
            fb = pagure_config['OIDC_PAGURE_USERNAME_FALLBACK']
            if fb == 'email':
                username = info[email_key].split('@')[0]
            elif fb == 'sub':
                username = flask.g.oidc_id_token['sub']
        flask.g.fas_user = munch.Munch(
            username=username,
            fullname=info.get(fulln_key, ''),
            email=info[email_key],
            ssh_key=info.get(ssh_key),
            groups=info.get(groups_key, []),
            login_time=flask.session['oidc_logintime'],
        )


def set_user():
    if flask.g.fas_user.username is None:
        flask.flash(
            'It looks like your Identity Provider did not provide an '
            'username we could retrieve, username being needed we cannot '
            'go further.', 'error')
        logout()
        return

    flask.session['_new_user'] = False
    if not pagure.lib.search_user(
            flask.g.session, username=flask.g.fas_user.username):
        flask.session['_new_user'] = True

    try:
        pagure.lib.set_up_user(
            session=flask.g.session,
            username=flask.g.fas_user.username,
            fullname=flask.g.fas_user.fullname,
            default_email=flask.g.fas_user.email,
            ssh_key=flask.g.fas_user.get('ssh_key'),
            keydir=pagure_config.get('GITOLITE_KEYDIR', None),
        )

        # If groups are managed outside pagure, set up the user at login
        if not pagure_config.get('ENABLE_GROUP_MNGT', False):
            user = pagure.lib.search_user(
                flask.g.session, username=flask.g.fas_user.username)
            old_groups = set(user.groups)
            fas_groups = set(flask.g.fas_user.groups)
            # Add the new groups
            for group in fas_groups - old_groups:
                groupobj = None
                if group:
                    groupobj = pagure.lib.search_groups(
                        flask.g.session, group_name=group)
                if groupobj:
                    try:
                        pagure.lib.add_user_to_group(
                            session=flask.g.session,
                            username=flask.g.fas_user.username,
                            group=groupobj,
                            user=flask.g.fas_user.username,
                            is_admin=is_admin(),
                            from_external=True,
                        )
                    except pagure.exceptions.PagureException as err:
                        _log.error(err)
            # Remove the old groups
            for group in old_groups - fas_groups:
                if group:
                    try:
                        pagure.lib.delete_user_of_group(
                            session=flask.g.session,
                            username=flask.g.fas_user.username,
                            groupname=group,
                            user=flask.g.fas_user.username,
                            is_admin=is_admin(),
                            force=True,
                            from_external=True,
                        )
                    except pagure.exceptions.PagureException as err:
                        _log.error(err)

        flask.g.session.commit()
    except SQLAlchemyError as err:
        flask.g.session.rollback()
        _log.exception(err)
        flask.flash(
            'Could not set up you as a user properly, please contact '
            'an admin', 'error')
        # Ensure the user is logged out if we cannot set them up
        # correctly
        logout()


def oidc_logout():
    flask.g.fas_user = None
    del flask.session['oidc_logintime']
    oidc.logout()
