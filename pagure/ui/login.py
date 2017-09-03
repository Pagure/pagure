# -*- coding: utf-8 -*-

"""
 (c) 2014-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Farhaan Bukhsh <farhaan.bukhsh@gmail.com>

"""

import datetime
import logging
import urlparse

import flask
from sqlalchemy.exc import SQLAlchemyError

import pagure.login_forms as forms
import pagure.lib
import pagure.lib.login
import pagure.lib.model as model
import pagure.lib.notify
from pagure import APP, SESSION, login_required
from pagure.lib.login import generate_hashed_value, check_password


_log = logging.getLogger(__name__)


@APP.route('/user/new/', methods=['GET', 'POST'])
@APP.route('/user/new', methods=['GET', 'POST'])
def new_user():
    """ Create a new user.
    """
    form = forms.NewUserForm()
    if form.validate_on_submit():

        username = form.user.data
        if pagure.lib.search_user(SESSION, username=username):
            flask.flash('Username already taken.', 'error')
            return flask.redirect(flask.request.url)

        email = form.email_address.data
        if pagure.lib.search_user(SESSION, email=email):
            flask.flash('Email address already taken.', 'error')
            return flask.redirect(flask.request.url)

        form.password.data = generate_hashed_value(form.password.data)

        token = pagure.lib.login.id_generator(40)

        user = model.User()
        user.token = token
        form.populate_obj(obj=user)
        user.default_email = form.email_address.data
        SESSION.add(user)
        SESSION.flush()

        pagure.lib.add_email_to_user(
            SESSION, user, form.email_address.data)

        try:
            SESSION.commit()
            send_confirmation_email(user)
            flask.flash(
                'User created, please check your email to activate the '
                'account')
        except SQLAlchemyError:  # pragma: no cover
            SESSION.rollback()
            flask.flash('Could not create user.')
            _log.exception('Could not create user.')

        return flask.redirect(flask.url_for('auth_login'))

    return flask.render_template(
        'login/user_new.html',
        form=form,
    )


@APP.route('/dologin', methods=['POST'])
def do_login():
    """ Log in the user.
    """
    form = forms.LoginForm()
    next_url = flask.request.form.get('next_url')
    if not next_url or next_url == 'None':
        next_url = flask.url_for('index')

    if form.validate_on_submit():
        username = form.username.data
        user_obj = pagure.lib.search_user(SESSION, username=username)
        if not user_obj:
            flask.flash('Username or password invalid.', 'error')
            return flask.redirect(flask.url_for('auth_login'))

        try:
            password_checks = check_password(
                form.password.data, user_obj.password,
                seed=APP.config.get('PASSWORD_SEED', None))
        except pagure.exceptions.PagureException as err:
            _log.exception(err)
            flask.flash('Username or password of invalid format.', 'error')
            return flask.redirect(flask.url_for('auth_login'))

        if not password_checks:
            flask.flash('Username or password invalid.', 'error')
            return flask.redirect(flask.url_for('auth_login'))

        elif user_obj.token:
            flask.flash(
                'Invalid user, did you confirm the creation with the url '
                'provided by email?', 'error')
            return flask.redirect(flask.url_for('auth_login'))

        else:

            if not user_obj.password.startswith('$2$'):
                user_obj.password = generate_hashed_value(form.password.data)
                SESSION.add(user_obj)

            visit_key = pagure.lib.login.id_generator(40)
            now = datetime.datetime.utcnow()
            expiry = now + datetime.timedelta(days=30)
            session = model.PagureUserVisit(
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
                flask.g.fas_user.login_time = now
                flask.flash('Welcome %s' % user_obj.username)
            except SQLAlchemyError as err:  # pragma: no cover
                flask.flash(
                    'Could not set the session in the db, '
                    'please report this error to an admin', 'error')
                _log.exception(err)

        return flask.redirect(next_url)
    else:
        flask.flash('Insufficient information provided', 'error')
    return flask.redirect(flask.url_for('auth_login'))


@APP.route('/confirm/<token>/')
@APP.route('/confirm/<token>')
def confirm_user(token):
    """ Confirm a user account.
    """
    user_obj = pagure.lib.search_user(SESSION, token=token)
    if not user_obj:
        flask.flash('No user associated with this token.', 'error')
    else:
        user_obj.token = None
        SESSION.add(user_obj)

        try:
            SESSION.commit()
            flask.flash('Email confirmed, account activated')
            return flask.redirect(flask.url_for('auth_login'))
        except SQLAlchemyError as err:  # pragma: no cover
            flask.flash(
                'Could not set the account as active in the db, '
                'please report this error to an admin', 'error')
            _log.exception(err)

    return flask.redirect(flask.url_for('index'))


@APP.route('/password/lost/', methods=['GET', 'POST'])
@APP.route('/password/lost', methods=['GET', 'POST'])
def lost_password():
    """ Method to allow a user to change his/her password assuming the email
    is not compromised.
    """
    form = forms.LostPasswordForm()
    if form.validate_on_submit():

        username = form.username.data
        user_obj = pagure.lib.search_user(SESSION, username=username)
        if not user_obj:
            flask.flash('Username invalid.', 'error')
            return flask.redirect(flask.url_for('auth_login'))
        elif user_obj.token:
            current_time = datetime.datetime.utcnow()
            invalid_period = user_obj.updated_on + \
                datetime.timedelta(minutes=3)
            if current_time < invalid_period:
                flask.flash(
                    'An email was sent to you less than 3 minutes ago, '
                    'did you check your spam folder? Otherwise, '
                    'try again after some time.', 'error')
                return flask.redirect(flask.url_for('auth_login'))

        token = pagure.lib.login.id_generator(40)
        user_obj.token = token
        SESSION.add(user_obj)

        try:
            SESSION.commit()
            send_lostpassword_email(user_obj)
            flask.flash(
                'Check your email to finish changing your password')
        except SQLAlchemyError:  # pragma: no cover
            SESSION.rollback()
            flask.flash(
                'Could not set the token allowing changing a password.',
                'error')
            _log.exception('Password lost change - Error setting token.')

        return flask.redirect(flask.url_for('auth_login'))

    return flask.render_template(
        'login/password_change.html',
        form=form,
    )


@APP.route('/password/reset/<token>/', methods=['GET', 'POST'])
@APP.route('/password/reset/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """ Method to allow a user to reset his/her password.
    """
    form = forms.ResetPasswordForm()

    user_obj = pagure.lib.search_user(SESSION, token=token)
    if not user_obj:
        flask.flash('No user associated with this token.', 'error')
        return flask.redirect(flask.url_for('auth_login'))
    elif not user_obj.token:
        flask.flash(
            'Invalid user, this user never asked for a password change',
            'error')
        return flask.redirect(flask.url_for('auth_login'))

    if form.validate_on_submit():

        user_obj.password = generate_hashed_value(form.password.data)

        user_obj.token = None
        SESSION.add(user_obj)

        try:
            SESSION.commit()
            flask.flash(
                'Password changed')
        except SQLAlchemyError:  # pragma: no cover
            SESSION.rollback()
            flask.flash('Could not set the new password.', 'error')
            _log.exception(
                'Password lost change - Error setting password.')

        return flask.redirect(flask.url_for('auth_login'))

    return flask.render_template(
        'login/password_reset.html',
        form=form,
        token=token,
    )
#
# Methods specific to local login.
#


@APP.route('/password/change/', methods=['GET', 'POST'])
@APP.route('/password/change', methods=['GET', 'POST'])
@login_required
def change_password():
    """ Method to change the password for local auth users.
    """

    form = forms.ChangePasswordForm()
    user_obj = pagure.lib.search_user(
        SESSION, username=flask.g.fas_user.username)

    if not user_obj:
        flask.abort(404, 'User not found')

    if form.validate_on_submit():

        try:
            password_checks = check_password(
                form.old_password.data, user_obj.password,
                seed=APP.config.get('PASSWORD_SEED', None))
        except pagure.exceptions.PagureException as err:
            _log.exception(err)
            flask.flash(
                'Could not update your password, either user or password '
                'could not be checked', 'error')
            return flask.redirect(flask.url_for('auth_login'))

        if password_checks:
            user_obj.password = generate_hashed_value(form.password.data)
            SESSION.add(user_obj)

        else:
            flask.flash(
                'Could not update your password, either user or password '
                'could not be checked', 'error')
            return flask.redirect(flask.url_for('auth_login'))

        try:
            SESSION.commit()
            flask.flash(
                'Password changed')
        except SQLAlchemyError:  # pragma: no cover
            SESSION.rollback()
            flask.flash('Could not set the new password.', 'error')
            _log.exception(
                'Password change  - Error setting new password.')

        return flask.redirect(flask.url_for('auth_login'))

    return flask.render_template(
        'login/password_recover.html',
        form=form,
    )


def send_confirmation_email(user):
    """ Sends the confirmation email asking the user to confirm its email
    address.
    """
    if not user.emails:
        return

    url = APP.config.get('APP_URL', flask.request.url_root)

    url = urlparse.urljoin(
        url or flask.request.url_root,
        flask.url_for('confirm_user', token=user.token),
    )

    message = """ Dear %(username)s,

Thank you for registering on pagure at %(url)s.

To finish your registration, please click on the following link or copy/paste
it in your browser:
  %(url)s

You account will not be activated until you finish this step.

Sincerely,
Your pagure admin.
""" % ({'username': user.username, 'url': url})

    pagure.lib.notify.send_email(
        text=message,
        subject='Confirm your user account',
        to_mail=user.emails[0].email,
    )


def send_lostpassword_email(user):
    """ Sends the email with the information on how to reset his/her password
    to the user.
    """
    if not user.emails:
        return

    url = APP.config.get('APP_URL', flask.request.url_root)

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
Your pagure admin.
""" % ({'username': user.username, 'url': url,
        'ip': flask.request.remote_addr})

    pagure.lib.notify.send_email(
        text=message,
        subject='Confirm your password change',
        to_mail=user.emails[0].email,
    )


def logout():
    """ Log the user out by expiring the user's session.
    """
    flask.g.fas_session_id = None
    flask.g.fas_user = None


def _check_session_cookie():
    """ Set the user into flask.g if the user is logged in.
    """
    cookie_name = APP.config.get('SESSION_COOKIE_NAME', 'pagure')
    cookie_name = '%s_local_cookie' % cookie_name
    session_id = None
    user = None
    login_time = None

    if cookie_name and cookie_name in flask.request.cookies:
        sessionid = flask.request.cookies.get(cookie_name)
        session = pagure.lib.login.get_session_by_visitkey(
            SESSION, sessionid)
        if session and session.user:
            now = datetime.datetime.now()
            if now > session.expiry:
                flask.flash('Session timed-out', 'error')
            elif APP.config.get('CHECK_SESSION_IP', True) \
                    and session.user_ip != flask.request.remote_addr:
                flask.flash('Session expired', 'error')
            else:
                new_expiry = now + datetime.timedelta(days=30)
                session_id = session.visit_key
                user = session.user
                login_time = session.created

                session.expiry = new_expiry
                SESSION.add(session)
                try:
                    SESSION.commit()
                except SQLAlchemyError as err:  # pragma: no cover
                    flask.flash(
                        'Could not prolong the session in the db, '
                        'please report this error to an admin', 'error')
                    _log.exception(err)

    flask.g.fas_session_id = session_id
    flask.g.fas_user = user
    if user:
        flask.g.fas_user.login_time = login_time


def _send_session_cookie(response):
    """ Set the session cookie if the user is authenticated. """
    cookie_name = APP.config.get('SESSION_COOKIE_NAME', 'pagure')
    secure = APP.config.get('SESSION_COOKIE_SECURE', True)

    response.set_cookie(
        key='%s_local_cookie' % cookie_name,
        value=flask.g.get('fas_session_id') or '',
        secure=secure,
        httponly=True,
    )
    return response
