# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources

__version__ = '0.1.36'
__api_version__ = '0.6'


import datetime
import logging
import os
import subprocess
import urlparse
from logging.handlers import SMTPHandler

import flask
import pygit2
import werkzeug
from flask_fas_openid import FAS
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError

from pygments import highlight
from pygments.lexers.text import DiffLexer
from pygments.formatters import HtmlFormatter

# Create the application.
APP = flask.Flask(__name__)
APP.jinja_env.trim_blocks = True
APP.jinja_env.lstrip_blocks = True

# set up FAS
APP.config.from_object('pagure.default_config')

if 'PAGURE_CONFIG' in os.environ:
    APP.config.from_envvar('PAGURE_CONFIG')


import pagure.lib
import pagure.lib.git
import pagure.mail_logging
import pagure.doc_utils
import pagure.forms
import pagure.login_forms


FAS = FAS(APP)
SESSION = pagure.lib.create_session(APP.config['DB_URL'])
REDIS = None
if APP.config['EVENTSOURCE_SOURCE'] or APP.config['WEBHOOK']:
    pagure.lib.set_redis(
        host=APP.config['REDIS_HOST'],
        port=APP.config['REDIS_PORT'],
        db=APP.config['REDIS_DB']
    )

if not APP.debug:
    APP.logger.addHandler(pagure.mail_logging.get_mail_handler(
        smtp_server=APP.config.get('SMTP_SERVER', '127.0.0.1'),
        mail_admin=APP.config.get('MAIL_ADMIN', APP.config['EMAIL_ERROR'])
    ))

# Send classic logs into syslog
SHANDLER = logging.StreamHandler()
SHANDLER.setLevel(APP.config.get('log_level', 'INFO'))
APP.logger.addHandler(SHANDLER)

LOG = APP.logger


def authenticated():
    ''' Utility function checking if the current user is logged in or not.
    '''
    return hasattr(flask.g, 'fas_user') and flask.g.fas_user is not None


def api_authenticated():
    ''' Utility function checking if the current user is logged in or not
    in the API.
    '''
    return hasattr(flask.g, 'fas_user') \
        and flask.g.fas_user is not None \
        and hasattr(flask.g, 'token') \
        and flask.g.token is not None


def admin_session_timedout():
    ''' Check if the current user has been authenticated for more than what
    is allowed (defaults to 15 minutes).
    If it is the case, the user is logged out and the method returns True,
    otherwise it returns False.
    '''
    timedout = False
    if not authenticated():
        return True
    if (datetime.datetime.utcnow() - flask.g.fas_user.login_time) > \
            APP.config.get('ADMIN_SESSION_LIFETIME',
                           datetime.timedelta(minutes=15)):
        timedout = True
        FAS.logout()
    return timedout


def is_safe_url(target):  # pragma: no cover
    """ Checks that the target url is safe and sending to the current
    website not some other malicious one.
    """
    ref_url = urlparse.urlparse(flask.request.host_url)
    test_url = urlparse.urlparse(
        urlparse.urljoin(flask.request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


def is_admin():
    """ Return whether the user is admin for this application or not. """
    if not authenticated():
        return False

    user = flask.g.fas_user

    auth_method = APP.config.get('PAGURE_AUTH', None)
    if auth_method == 'fas':
        if not user.cla_done or len(user.groups) < 1:
            return False

    admins = APP.config['ADMIN_GROUP']
    if isinstance(admins, basestring):
        admins = [admins]
    admins = set(admins)
    groups = set(flask.g.fas_user.groups)

    return not groups.isdisjoint(admins)


def is_repo_admin(repo_obj):
    """ Return whether the user is an admin of the provided repo. """
    if not authenticated():
        return False

    user = flask.g.fas_user.username

    usergrps = [
        usr.user
        for grp in repo_obj.groups
        for usr in grp.users]

    return user == repo_obj.user.user or (
        user in [user.user for user in repo_obj.users]
    ) or (user in usergrps)


def generate_user_key_files():
    """ Regenerate the key files used by gitolite.
    """
    gitolite_home = APP.config.get('GITOLITE_HOME', None)
    if gitolite_home:
        users = pagure.lib.search_user(SESSION)
        for user in users:
            pagure.lib.update_user_ssh(SESSION, user, user.public_ssh_key,
                                       APP.config.get('GITOLITE_KEYDIR', None))
    pagure.lib.git.generate_gitolite_acls()


def cla_required(function):
    """ Flask decorator to retrict access to CLA signed user.
To use this decorator you need to have a function named 'auth_login'.
Without that function the redirect if the user is not logged in will not
work.
"""
    auth_method = APP.config.get('PAGURE_AUTH', None)

    @wraps(function)
    def decorated_function(*args, **kwargs):
        """ Decorated function, actually does the work. """
        if not authenticated():
            return flask.redirect(
                flask.url_for('auth_login', next=flask.request.url))
        elif auth_method == 'fas' and not flask.g.fas_user.cla_done:
            flask.flash('You must sign the FPCA (Fedora Project Contributor '
                        'Agreement) to use pagure', 'errors')
            return flask.redirect(flask.url_for('.index'))
        return function(*args, **kwargs)
    return decorated_function


@APP.context_processor
def inject_variables():
    """ With this decorator we can set some variables to all templates.
    """
    user_admin = is_admin()

    forkbuttonform = None
    if authenticated():
        forkbuttonform = pagure.forms.ConfirmationForm()

    return dict(
        version=__version__,
        admin=user_admin,
        authenticated=authenticated(),
        forkbuttonform=forkbuttonform,
    )


# pylint: disable=W0613
@APP.before_request
def set_session():
    """ Set the flask session as permanent. """
    flask.session.permanent = True


@FAS.postlogin
def set_user(return_url):
    ''' After login method. '''
    try:

        pagure.lib.set_up_user(
            session=SESSION,
            username=flask.g.fas_user.username,
            fullname=flask.g.fas_user.fullname,
            default_email=flask.g.fas_user.email,
            ssh_key=flask.g.fas_user.get('ssh_key'),
            keydir=APP.config.get('GITOLITE_KEYDIR', None),
        )
        SESSION.commit()
    except SQLAlchemyError as err:
        SESSION.rollback()
        LOG.debug(err)
        LOG.exception(err)
        flask.flash(
            'Could not set up you as a user properly, please contact '
            'an admin', 'error')
    return flask.redirect(return_url)


@APP.errorhandler(404)
def not_found(error):
    """404 Not Found page"""
    return flask.render_template('not_found.html', error=error), 404


@APP.errorhandler(500)
def fatal_error(error):  # pragma: no cover
    """500 Fatal Error page"""
    return flask.render_template('fatal_error.html', error=error), 500


@APP.errorhandler(401)
def unauthorized(error):  # pragma: no cover
    """401 Unauthorized page"""
    return flask.render_template('unauthorized.html', error=error), 401


@APP.route('/login/', methods=('GET', 'POST'))
def auth_login():  # pragma: no cover
    """ Method to log into the application using FAS OpenID. """
    return_point = flask.url_for('index')
    if 'next' in flask.request.args:
        if is_safe_url(flask.request.args['next']):
            return_point = flask.request.args['next']

    if authenticated():
        return flask.redirect(return_point)

    admins = APP.config['ADMIN_GROUP']
    if isinstance(admins, basestring):
        admins = set([admins])
    else:  # pragma: no cover
        admins = set(admins)

    if APP.config.get('PAGURE_AUTH', None) == 'fas':
        return FAS.login(return_url=return_point, groups=admins)
    elif APP.config.get('PAGURE_AUTH', None) == 'local':
        form = pagure.login_forms.LoginForm()
        return flask.render_template(
            'login/login.html',
            next_url=return_point,
            form=form,
        )


@APP.route('/logout/')
def auth_logout():  # pragma: no cover
    """ Method to log out from the application. """
    return_point = flask.url_for('index')
    if 'next' in flask.request.args:
        if is_safe_url(flask.request.args['next']):
            return_point = flask.request.args['next']

    if not authenticated():
        return flask.redirect(return_point)

    if APP.config.get('PAGURE_AUTH', None) == 'fas':
        if hasattr(flask.g, 'fas_user') and flask.g.fas_user is not None:
            FAS.logout()
            flask.flash("You are no longer logged-in")
    elif APP.config.get('PAGURE_AUTH', None) == 'local':
        login.logout()
    return flask.redirect(return_point)


def __get_file_in_tree(repo_obj, tree, filepath, bail_on_tree=False):
    ''' Retrieve the entry corresponding to the provided filename in a
    given tree.
    '''

    filename = filepath[0]
    if isinstance(tree, pygit2.Blob):
        return
    for entry in tree:
        if entry.name == filename:
            if len(filepath) == 1:
                blob = repo_obj.get(entry.id)
                # If we can't get the content (for example: an empty folder)
                if blob is None:
                    return
                # If we get a tree instead of a blob, let's escape
                if isinstance(blob, pygit2.Tree) and bail_on_tree:
                    return blob
                content = blob.data
                # If it's a (sane) symlink, we try a single-level dereference
                if entry.filemode == pygit2.GIT_FILEMODE_LINK \
                        and os.path.normpath(content) == content \
                        and not os.path.isabs(content):
                    try:
                        dereferenced = tree[content]
                    except KeyError:
                        pass
                    else:
                        if dereferenced.filemode == pygit2.GIT_FILEMODE_BLOB:
                            blob = repo_obj[dereferenced.oid]

                return blob
            else:
                nextitem = repo_obj[entry.oid]
                # If we can't get the content (for example: an empty folder)
                if nextitem is None:
                    return
                return __get_file_in_tree(
                    repo_obj, nextitem, filepath[1:],
                    bail_on_tree=bail_on_tree)


def get_repo_path(repo):
    """ Return the path of the git repository corresponding to the provided
    Repository object from the DB.
    """
    if repo.is_fork:
        repopath = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    else:
        repopath = os.path.join(APP.config['GIT_FOLDER'], repo.path)

    if not os.path.exists(repopath):
        flask.abort(404, 'No git repo found')

    return repopath


def get_remote_repo_path(remote_git, branch_from, loop=False):
    """ Return the path of the remote git repository corresponding to the
    provided information.
    """
    repopath = os.path.join(
        APP.config['REMOTE_GIT_FOLDER'],
        werkzeug.secure_filename('%s_%s' % (remote_git, branch_from))
    )

    if not os.path.exists(repopath):
        try:
            pygit2.clone_repository(
                remote_git, repopath, checkout_branch=branch_from)
        except Exception as err:
            LOG.debug(err)
            LOG.exception(err)
            flask.abort(500, 'Could not clone the remote git repository')
    else:
        repo = pagure.lib.repo.PagureRepo(repopath)
        try:
            repo.pull(branch=branch_from, force=True)
        except pagure.exceptions.PagureException as err:
            LOG.debug(err)
            LOG.exception(err)
            flask.abort(500, err.message)

    return repopath


# Import the application
import pagure.ui.app
import pagure.ui.admin
import pagure.ui.fork
import pagure.ui.groups
if APP.config.get('ENABLE_TICKETS', True):
    import pagure.ui.issues
import pagure.ui.plugins
import pagure.ui.repo

from pagure.api import API
APP.register_blueprint(API)

import pagure.internal
APP.register_blueprint(pagure.internal.PV)


# Only import the login controller if the app is set up for local login
if APP.config.get('PAGURE_AUTH', None) == 'local':
    import pagure.ui.login as login
    APP.before_request(login._check_session_cookie)
    APP.after_request(login._send_session_cookie)


# pylint: disable=W0613
@APP.teardown_request
def shutdown_session(exception=None):
    """ Remove the DB session at the end of each request. """
    SESSION.remove()
