#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


import hashlib
import datetime
import urlparse

import flask
from sqlalchemy.exc import SQLAlchemyError

import progit.login_forms as forms
import progit.lib
import progit.notify
from progit import APP, SESSION, is_admin
from progit.ui.admin import admin_required
import progit.model as model


@APP.route('/user/new', methods=['GET', 'POST'])
def new_user():
    """ Create a new user.
    """
    form = forms.NewUserForm()
    if form.validate_on_submit():

        username = form.user.data
        if progit.lib.get_user(SESSION, username):
            flask.flash('Username already taken.', 'error')
            return flask.redirect(flask.request.url)

        email = form.email_address.data
        if progit.lib.get_user_by_email(SESSION, email):
            flask.flash('Email address already taken.', 'error')
            return flask.redirect(flask.request.url)

        password = '%s%s' % (
            form.password.data, APP.config.get('PASSWORD_SEED', None))
        form.password.data = hashlib.sha512(password).hexdigest()

        token = progit.lib.id_generator(40)

        user = model.User()
        user.token = token
        form.populate_obj(obj=user)
        SESSION.add(user)
        SESSION.flush()

        emails = [email.email for email in user.emails]
        if form.email_address.data not in emails:
            useremail = model.UserEmail(
                user_id=user.id,
                email=form.email_address.data)
            SESSION.add(useremail)
            SESSION.flush()

        try:
            SESSION.flush()
            send_confirmation_email(user)
            flask.flash(
                'User created, please check your email to activate the '
                'account')
        except SQLAlchemyError as err:
            SESSION.rollback()
            flask.flash('Could not create user.')
            APP.logger.debug('Could not create user.')
            APP.logger.exception(err)

        SESSION.commit()

        return flask.redirect(flask.url_for('auth_login'))

    return flask.render_template(
        'login/user_new.html',
        form=form,
    )


@APP.route('/dologin', methods=['POST'])
def do_login():
    """ Lo the user in user.
    """
    form = forms.LoginForm()
    next_url = flask.request.args.get('next_url')
    if not next_url or next_url == 'None':
        next_url = flask.url_for('index')

    if form.validate_on_submit():
        username = form.username.data
        password = '%s%s' % (
            form.password.data, APP.config.get('PASSWORD_SEED', None))
        password = hashlib.sha512(password).hexdigest()

        user_obj = progit.lib.get_user(SESSION, username)
        if not user_obj or user_obj.password != password:
            flask.flash('Username or password invalid.', 'error')
            return flask.redirect(flask.url_for('auth_login'))
        elif user_obj.token:
            flask.flash(
                'Invalid user, did you confirm the creation with the url '
                'provided by email?', 'error')
            return flask.redirect(flask.url_for('auth_login'))
        else:
            visit_key = progit.lib.id_generator(40)
            expiry = datetime.datetime.now() + APP.config.get(
                'PERMANENT_SESSION_LIFETIME')
            session = model.ProgitUserVisit(
                user_id=user_obj.id,
                user_ip=flask.request.remote_addr,
                visit_key=visit_key,
                expiry=expiry,
            )
            SESSION.add(session)
            try:
                SESSION.commit()
                flask.g.fas_user = user_obj
                flask.g.fas_session_id = visit_key
                flask.flash('Welcome %s' % user_obj.username)
            except SQLAlchemyError, err:  # pragma: no cover
                flask.flash(
                    'Could not set the session in the db, '
                    'please report this error to an admin', 'error')
                APP.logger.exception(err)

        return flask.redirect(next_url)
    else:
        flask.flash('Insufficient information provided', 'error')
    return flask.redirect(flask.url_for('auth_login'))


@APP.route('/confirm/<token>')
def confirm_user(token):
    """ Confirm a user account.
    """
    user_obj = progit.lib.get_user_by_token(SESSION, token)
    if not user_obj:
        flask.flash('No user associated with this token.', 'error')
    else:
        user_obj.token = None
        SESSION.add(user_obj)

        try:
            SESSION.commit()
            flask.flash('Email confirmed, account activated')
            return flask.redirect(flask.url_for('auth_login'))
        except SQLAlchemyError, err:  # pragma: no cover
            flask.flash(
                'Could not set the account as active in the db, '
                'please report this error to an admin', 'error')
            APP.logger.exception(err)

    return flask.redirect(flask.url_for('index'))


@APP.route('/password/lost', methods=['GET', 'POST'])
def lost_password():
    """ Method to allow a user to change his/her password assuming the email
    is not compromised.
    """
    form = forms.LostPasswordForm()
    if form.validate_on_submit():

        username = form.username.data
        user_obj = progit.lib.get_user(SESSION, username)
        if not user_obj:
            flask.flash('Username invalid.', 'error')
            return flask.redirect(flask.url_for('auth_login'))
        elif user_obj.token:
            flask.flash(
                'Invalid user, did you confirm the creation with the url '
                'provided by email? Or did you already ask for a password '
                'change?', 'error')
            return flask.redirect(flask.url_for('auth_login'))

        token = progit.lib.id_generator(40)
        user_obj.token = token
        SESSION.add(user_obj)

        try:
            SESSION.commit()
            send_lostpassword_email(user_obj)
            flask.flash(
                'Check your email to finish changing your password')
        except SQLAlchemyError as err:
            SESSION.rollback()
            flask.flash(
                'Could not set the token allowing changing a password.',
                'error')
            APP.logger.debug('Password lost change - Error setting token.')
            APP.logger.exception(err)

        return flask.redirect(flask.url_for('auth_login'))

    return flask.render_template(
        'login/password_change.html',
        form=form,
    )


@APP.route('/password/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """ Method to allow a user to reset his/her password.
    """
    form = forms.ResetPasswordForm()

    user_obj = progit.lib.get_user_by_token(SESSION, token)
    if not user_obj:
        flask.flash('No user associated with this token.', 'error')
        return flask.redirect(flask.url_for('auth_login'))
    elif not user_obj.token:
        flask.flash(
            'Invalid user, this user never asked for a password change',
            'error')
        return flask.redirect(flask.url_for('auth_login'))

    if form.validate_on_submit():

        password = '%s%s' % (
            form.password.data, APP.config.get('PASSWORD_SEED', None))
        user_obj.password = hashlib.sha512(password).hexdigest()
        user_obj.token = None
        SESSION.add(user_obj)

        try:
            SESSION.commit()
            flask.flash(
                'Password changed')
        except SQLAlchemyError as err:
            SESSION.rollback()
            flask.flash('Could not set the new password.', 'error')
            APP.logger.debug(
                'Password lost change - Error setting password.')
            APP.logger.exception(err)

        return flask.redirect(flask.url_for('auth_login'))

    return flask.render_template(
        'login/password_reset.html',
        form=form,
        token=token,
    )


#
# Admin endpoint specific to local login
#

@APP.route('/admin/groups', methods=['GET', 'POST'])
@admin_required
def admin_groups():
    """ List of the groups present in the system
    """
    # Add new group if asked
    form = forms.NewGroupForm()
    if form.validate_on_submit():

        grp = model.ProgitGroup()
        form.populate_obj(obj=grp)
        SESSION.add(grp)
        try:
            SESSION.flush()
        except SQLAlchemyError as err:
            SESSION.rollback()
            flask.flash('Could not create group.')
            APP.logger.debug('Could not create group.')
            APP.logger.exception(err)

        flask.flash('Group `%s` created.' % grp.group_name)
        SESSION.commit()

    groups = progit.lib.get_groups(SESSION)

    return flask.render_template(
        'login/admin_groups.html',
        groups=groups,
        form=form,
        conf_form=forms.ConfirmationForm(),
    )


@APP.route('/admin/group/<group>', methods=['GET', 'POST'])
@admin_required
def admin_group(group):
    """ List of the users in a certain group
    """
    group_obj = progit.lib.get_group(SESSION, group)

    if not group_obj:
        flask.flash('No group `%s` found' % groupname, 'error')
        return flask.redirect(flask.url_for('.admin_groups'))

    # Add new user to the group if asked
    form = forms.LostPasswordForm()
    if form.validate_on_submit():
        user = progit.lib.get_user(SESSION, form.username.data)
        if not user:
            flask.flash('No user `%s` found' % form.username.data, 'error')
            return flask.redirect(flask.url_for('.admin_group', group=group))

        grp = model.ProgitUserGroup(
            group_id = group_obj.id,
            user_id = user.id
        )
        SESSION.add(grp)
        try:
            SESSION.flush()
        except SQLAlchemyError as err:
            SESSION.rollback()
            flask.flash(
                'Could not add user `%s` to group `%s`.' % (
                    user.user, group_obj.group),
                'error')
            APP.logger.debug(
                'Could not add user `%s` to group `%s`.' % (
                    user.user, group_obj.group))
            APP.logger.exception(err)

        flask.flash('User `%s` added.' % user.user)
        SESSION.commit()

    users = progit.lib.get_users_by_group(SESSION, group)

    return flask.render_template(
        'login/admin_users.html',
        form=form,
        conf_form=forms.ConfirmationForm(),
        group=group_obj,
        users=users,
    )


@APP.route('/admin/group/<group>/<user>/delete', methods=['POST'])
@admin_required
def admin_group_user_delete(user, group):
    """ Delete an user from a certain group
    """
    # Add new user to the group if asked
    form = forms.ConfirmationForm()
    if form.validate_on_submit():
        group_obj = progit.lib.get_group(SESSION, group)

        if not group_obj:
            flask.flash('No group `%s` found' % groupname, 'error')
            return flask.redirect(flask.url_for('.admin_groups'))

        user = progit.lib.get_user(SESSION, user)
        if not user:
            flask.flash('No user `%s` found' % user, 'error')
            return flask.redirect(flask.url_for('.admin_groups'))

        user_grp = progit.lib.get_user_group(SESSION, user.id, group_obj.id)
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
    form = forms.ConfirmationForm()
    if form.validate_on_submit():
        group_obj = progit.lib.get_group(SESSION, group)

        if not group_obj:
            flask.flash('No group `%s` found' % groupname, 'error')
            return flask.redirect(flask.url_for('.admin_groups'))

        SESSION.delete(group_obj)

        SESSION.commit()
        flask.flash(
            'Group `%s` has been deleted' % (group))

    return flask.redirect(flask.url_for('.admin_groups'))


#
# Methods specific to local login.
#


def send_confirmation_email(user):
    """ Sends the confirmation email asking the user to confirm its email
    address.
    """
    if not user.emails:
        return

    url = APP.config.get('APPLICATION_URL', flask.request.url_root)

    url = urlparse.urljoin(
        url or flask.request.url_root,
        flask.url_for('confirm_user', token=user.token),
    )

    message = """ Dear %(username)s,

Thank you for registering on progit at %(url)s.

To finish your registration, please click on the following link or copy/paste
it in your browser:
  %(url)s

You account will not be activated until you finish this step.

Sincerely,
Your progit admin.
""" % (
        {
            'username': user.username,
            'url': url,
        })

    progit.notify.send_email(
        text=message,
        subject='[Progit] Confirm your user account',
        to_mail=user.emails[0].email,
    )


def send_lostpassword_email(user):
    """ Sends the email with the information on how to reset his/her password
    to the user.
    """
    if not user.emails:
        return

    url = APP.config.get('APPLICATION_URL', flask.request.url_root)

    url = urlparse.urljoin(
        url or flask.request.url_root,
        flask.url_for('reset_password', token=user.token),
    )

    message = """ Dear %(username)s,

The IP address %(ip)s has requested a password change for this account.

If you wish to change your password, please click on the following link or
copy/paste it in your browser:
  %(url)s

If you did not request this change, please inform an admin immediately!

Sincerely,
Your progit admin.
""" % (
        {
            'username': user.username,
            'url': url,
            'ip': flask.request.remote_addr,
        })

    progit.notify.send_email(
        text=message,
        subject='[Progit] Confirm your password change',
        to_mail=user.emails[0].email,
    )


def logout():
    """ Log the user out by expiring the user's session.
    """
    flask.g.fas_session_id = None
    flask.g.fas_user = None

    flask.flash('You have been logged out')


def _check_session_cookie():
    """ Set the user into flask.g if the user is logged in.
    """
    cookie_name = APP.config.get('PROGIT_COOKIE_NAME', 'progit')
    session_id = None
    user = None

    if cookie_name and cookie_name in flask.request.cookies:
        sessionid = flask.request.cookies[cookie_name]
        session = progit.lib.get_session_by_visitkey(SESSION, sessionid)
        if session and session.user:
            now = datetime.datetime.now()
            new_expiry = now + APP.config.get('PERMANENT_SESSION_LIFETIME')
            if now > session.expiry:
                flask.flash('Session timed-out', 'error')
            elif APP.config.get('CHECK_SESSION_IP', True) \
                    and session.user_ip != flask.request.remote_addr:
                flask.flash('Session expired', 'error')
            else:
                session_id = session.visit_key
                user = session.user

                session.expiry = new_expiry
                SESSION.add(session)
                try:
                    SESSION.commit()
                except SQLAlchemyError, err:  # pragma: no cover
                    flask.flash(
                        'Could not prolong the session in the db, '
                        'please report this error to an admin', 'error')
                    APP.logger.exception(err)

    flask.g.fas_session_id = session_id
    flask.g.fas_user = user


def _send_session_cookie(response):
    """ Set the session cookie if the user is authenticated. """
    cookie_name = APP.config.get('PROGIT_COOKIE_NAME', 'progit')
    secure = APP.config.get('PROGIT_COOKIE_REQUIRES_HTTPS', True)

    response.set_cookie(
        key=cookie_name,
        value=flask.g.fas_session_id or '',
        secure=secure,
        httponly=True,
    )
    return response
