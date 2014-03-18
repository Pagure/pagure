#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

## These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

__version__ = '0.1'

import logging
import os
from logging.handlers import SMTPHandler

import arrow
import flask
from flask_fas_openid import FAS
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError

import progit.forms as forms


# Create the application.
APP = flask.Flask(__name__)
APP.jinja_env.trim_blocks = True
APP.jinja_env.lstrip_blocks = True

# set up FAS
APP.config.from_object('progit.default_config')

if 'PROGIT_CONFIG' in os.environ:
    APP.config.from_envvar('PROGIT_CONFIG')


FAS = FAS(APP)
SESSION = None
#SESSION = progit.create_session(APP.config['DB_URL'])

# Set up the logger
## Send emails for big exception
mail_handler = SMTPHandler(
    APP.config.get('SMTP_SERVER', '127.0.0.1'),
    'nobody@fedoraproject.org',
    APP.config.get('MAIL_ADMIN', APP.config['EMAIL_ERROR']),
    'Fedocal error')
mail_handler.setFormatter(logging.Formatter('''
    Message type:       %(levelname)s
    Location:           %(pathname)s:%(lineno)d
    Module:             %(module)s
    Function:           %(funcName)s
    Time:               %(asctime)s

    Message:

    %(message)s
'''))
mail_handler.setLevel(logging.ERROR)
if not APP.debug:
    APP.logger.addHandler(mail_handler)

## Send classic logs into syslog
handler = logging.StreamHandler()
handler.setLevel(APP.config.get('log_level', 'INFO'))
APP.logger.addHandler(handler)

LOG = APP.logger


def authenticated():
    return hasattr(flask.g, 'fas_user') and flask.g.fas_user


def is_admin():
    """ Return whether the user is admin for this application or not. """
    if not authenticated() \
            or not flask.g.fas_user.cla_done \
            or len(flask.g.fas_user.groups) < 1:
        return False

    admins = APP.config['ADMIN_GROUP']
    if isinstance(admins, basestring):
        admins = set([admins])
    else:  # pragma: no cover
        admins = set(admins)
    groups = set(flask.g.fas_user.groups)
    return not groups.isdisjoint(admins)


def cla_required(function):
    """ Flask decorator to retrict access to CLA signed user.
To use this decorator you need to have a function named 'auth_login'.
Without that function the redirect if the user is not logged in will not
work.
"""
    @wraps(function)
    def decorated_function(*args, **kwargs):
        """ Decorated function, actually does the work. """
        if not authenticated():
            return flask.redirect(
                flask.url_for('auth_login', next=flask.request.url))
        elif not flask.g.fas_user.cla_done:
            flask.flash('You must sign the CLA (Contributor License '
                        'Agreement to use fedocal', 'errors')
            return flask.redirect(flask.url_for('.index'))
        return function(*args, **kwargs)
    return decorated_function


@APP.context_processor
def inject_variables():
    """ With this decorator we can set some variables to all templates.
    """
    user_admin = is_admin()

    return dict(
        version=__version__,
        admin=user_admin,
    )


@APP.template_filter('lastcommit_date')
def lastcommit_date_filter(repo):
    """ Template filter returning the last commit date of the provided repo.
    """
    commit = repo[repo.head.target]
    return arrow.get(commit.commit_time).humanize()


@APP.route('/login/', methods=('GET', 'POST'))
def auth_login():
    """ Method to log into the application using FAS OpenID. """

    return_point = flask.url_for('index')
    if 'next' in flask.request.args:
        return_point = flask.request.args['next']

    if authenticated():
        return flask.redirect(return_point)

    return FAS.login(return_url=return_point)


@APP.route('/logout/')
def auth_logout():
    """ Method to log out from the application. """
    if not authenticated():
        return flask.redirect(flask.url_for('index'))
    FAS.logout()
    flask.flash('You have been logged out')
    return flask.redirect(flask.url_for('index'))

## Import the application

import progit.app
