# -*- coding: utf-8 -*-

"""
 (c) 2014-2020 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import logging
from base64 import b64decode

import flask
from flask import Markup

from sqlalchemy.exc import SQLAlchemyError

import pagure.lib.query
import pagure.utils
from pagure.flask_app import logout
from pagure.config import config as pagure_config
import flask_fas_openid

FAS = flask_fas_openid.FAS()

_log = logging.getLogger(__name__)


@FAS.postlogin
def set_user(return_url):
    """ After login method. """
    if flask.g.fas_user.username is None:
        flask.flash(
            "It looks like your OpenID provider did not provide an "
            "username we could retrieve, username being needed we cannot "
            "go further.",
            "error",
        )
        logout()
        return flask.redirect(return_url)

    flask.session["_new_user"] = False
    user = pagure.lib.query.search_user(
        flask.g.session, username=flask.g.fas_user.username
    )
    if not user:
        flask.session["_new_user"] = True
    else:
        user_email = pagure.lib.query.search_user(
            flask.g.session, email=flask.g.fas_user.email
        )
        if user_email and user_email.user != user.user:
            flask.flash(
                "This email address seems to already be associated with "
                "another account and thus can not be associated with yours",
                "error",
            )
            logout()
            return flask.redirect(return_url)

    try:
        try:

            ssh_key = flask.g.fas_user.get("ssh_key")
            if ssh_key is not None:
                try:
                    ssh_key = b64decode(ssh_key).decode("ascii")
                except (TypeError, ValueError):
                    pass

            pagure.lib.query.set_up_user(
                session=flask.g.session,
                username=flask.g.fas_user.username,
                fullname=flask.g.fas_user.fullname,
                default_email=flask.g.fas_user.email,
                ssh_key=ssh_key,
                keydir=pagure_config.get("GITOLITE_KEYDIR", None),
            )
        except pagure.exceptions.PagureException as err:
            message = str(err)
            if message == "SSH key invalid.":
                flask.flash(message, "error")
            else:
                raise

        # If groups are managed outside pagure, set up the user at login
        if not pagure_config.get("ENABLE_GROUP_MNGT", False):
            user = pagure.lib.query.search_user(
                flask.g.session, username=flask.g.fas_user.username
            )
            groups = set(user.groups)
            fas_groups = set(flask.g.fas_user.groups)
            # Add the new groups
            for group in fas_groups - groups:
                groupobj = None
                if group:
                    groupobj = pagure.lib.query.search_groups(
                        flask.g.session, group_name=group
                    )
                if groupobj:
                    try:
                        pagure.lib.query.add_user_to_group(
                            session=flask.g.session,
                            username=flask.g.fas_user.username,
                            group=groupobj,
                            user=flask.g.fas_user.username,
                            is_admin=pagure.utils.is_admin(),
                            from_external=True,
                        )
                    except pagure.exceptions.PagureException as err:
                        _log.error(err)
            # Remove the old groups
            for group in groups - fas_groups:
                if group:
                    try:
                        pagure.lib.query.delete_user_of_group(
                            session=flask.g.session,
                            username=flask.g.fas_user.username,
                            groupname=group,
                            user=flask.g.fas_user.username,
                            is_admin=pagure.utils.is_admin(),
                            force=True,
                            from_external=True,
                        )
                    except pagure.exceptions.PagureException as err:
                        _log.error(err)

        flask.g.session.commit()
    except SQLAlchemyError as err:
        flask.g.session.rollback()
        _log.exception(err)
        message = Markup(
            "Could not set up you as a user properly,"
            ' please <a href="/about">contact an administrator</a>'
        )
        flask.flash(message, "error")
        # Ensure the user is logged out if we cannot set them up
        # correctly
        logout()
    except pagure.exceptions.PagureException as err:
        flask.flash(str(err), "error")

    return flask.redirect(return_url)
