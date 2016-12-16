# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# These two lines are needed to run on EL6
__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources

__version__ = '2.10.1'
__api_version__ = '0.10'


import datetime
import logging
import os
import re
import subprocess
import urlparse
from logging.handlers import SMTPHandler

import flask
import pygit2
import werkzeug
from functools import wraps
from sqlalchemy.exc import SQLAlchemyError

from pygments import highlight
from pygments.lexers.text import DiffLexer
from pygments.formatters import HtmlFormatter

from flask_multistatic import MultiStaticFlask

from werkzeug.routing import BaseConverter

import pagure.exceptions

# Create the application.
APP = MultiStaticFlask(__name__)
APP.jinja_env.trim_blocks = True
APP.jinja_env.lstrip_blocks = True

# set up FAS
APP.config.from_object('pagure.default_config')

if 'PAGURE_CONFIG' in os.environ:
    APP.config.from_envvar('PAGURE_CONFIG')


if APP.config.get('THEME_TEMPLATE_FOLDER', False):
    # Jinja can be told to look for templates in different folders
    # That's what we do here
    template_folder = APP.config['THEME_TEMPLATE_FOLDER']
    if template_folder[0] != '/':
        template_folder = os.path.join(
            APP.root_path, APP.template_folder, template_folder)
    import jinja2
    # Jinja looks for the template in the order of the folders specified
    templ_loaders = [
        jinja2.FileSystemLoader(template_folder),
        APP.jinja_loader,
    ]
    APP.jinja_loader = jinja2.ChoiceLoader(templ_loaders)


if APP.config.get('THEME_STATIC_FOLDER', False):
    static_folder = APP.config['THEME_STATIC_FOLDER']
    if static_folder[0] != '/':
        static_folder = os.path.join(
            APP.root_path, 'static', static_folder)
    # Unlike templates, to serve static files from multiples folders we
    # need flask-multistatic
    APP.static_folder = [
        static_folder,
        os.path.join(APP.root_path, 'static'),
    ]


import pagure.doc_utils
import pagure.forms
import pagure.lib
import pagure.lib.git
import pagure.login_forms
import pagure.mail_logging
import pagure.proxy

# Only import flask_fas_openid if it is needed
if APP.config.get('PAGURE_AUTH', None) in ['fas', 'openid']:
    from flask_fas_openid import FAS
    FAS = FAS(APP)

    @FAS.postlogin
    def set_user(return_url):
        ''' After login method. '''
        flask.session['_new_user'] = False
        if not pagure.lib.search_user(
                SESSION, username=flask.g.fas_user.username):
            flask.session['_new_user'] = True

        try:
            pagure.lib.set_up_user(
                session=SESSION,
                username=flask.g.fas_user.username,
                fullname=flask.g.fas_user.fullname,
                default_email=flask.g.fas_user.email,
                ssh_key=flask.g.fas_user.get('ssh_key'),
                keydir=APP.config.get('GITOLITE_KEYDIR', None),
            )

            # If groups are managed outside pagure, set up the user at login
            if not APP.config.get('ENABLE_GROUP_MNGT', False):
                user = pagure.lib.search_user(
                    SESSION, username=flask.g.fas_user.username)
                groups = set(user.groups)
                fas_groups = set(flask.g.fas_user.groups)
                # Add the new groups
                for group in fas_groups - groups:
                    group = pagure.lib.search_groups(
                        SESSION, group_name=group)
                    if not group:
                        continue
                    try:
                        pagure.lib.add_user_to_group(
                            session=SESSION,
                            username=flask.g.fas_user.username,
                            group=group,
                            user=flask.g.fas_user.username,
                            is_admin=is_admin(),
                        )
                    except pagure.exceptions.PagureException as err:
                        LOG.debug(err)
                # Remove the old groups
                for group in groups - fas_groups:
                    try:
                        pagure.lib.delete_user_of_group(
                            session=SESSION,
                            username=flask.g.fas_user.username,
                            groupname=group,
                            user=flask.g.fas_user.username,
                            is_admin=is_admin(),
                            force=True,
                        )
                    except pagure.exceptions.PagureException as err:
                        LOG.debug(err)

            SESSION.commit()
        except SQLAlchemyError as err:
            SESSION.rollback()
            LOG.debug(err)
            LOG.exception(err)
            flask.flash(
                'Could not set up you as a user properly, please contact '
                'an admin', 'error')
            # Ensure the user is logged out if we cannot set them up
            # correctly
            logout()
        return flask.redirect(return_url)


SESSION = pagure.lib.create_session(APP.config['DB_URL'])
REDIS = None
if APP.config['EVENTSOURCE_SOURCE'] \
        or APP.config['WEBHOOK'] \
        or APP.config.get('PAGURE_CI_SERVICES'):
    pagure.lib.set_redis(
        host=APP.config['REDIS_HOST'],
        port=APP.config['REDIS_PORT'],
        dbname=APP.config['REDIS_DB']
    )


if APP.config.get('PAGURE_CI_SERVICES'):
    pagure.lib.set_pagure_ci(APP.config['PAGURE_CI_SERVICES'])


if not APP.debug:
    APP.logger.addHandler(pagure.mail_logging.get_mail_handler(
        smtp_server=APP.config.get('SMTP_SERVER', '127.0.0.1'),
        mail_admin=APP.config.get('MAIL_ADMIN', APP.config['EMAIL_ERROR'])
    ))

# Send classic logs into syslog
SHANDLER = logging.StreamHandler()
SHANDLER.setLevel(APP.config.get('LOG_LEVEL', 'INFO'))
APP.logger.addHandler(SHANDLER)

LOG = APP.logger
LOG.setLevel(APP.config.get('LOG_LEVEL', 'INFO'))
pagure.lib.set_log(LOG)

APP.wsgi_app = pagure.proxy.ReverseProxied(APP.wsgi_app)


def authenticated():
    ''' Utility function checking if the current user is logged in or not.
    '''
    return hasattr(flask.g, 'fas_user') and flask.g.fas_user is not None


def logout():
    auth = APP.config.get('PAGURE_AUTH', None)
    if auth in ['fas', 'openid']:
        if hasattr(flask.g, 'fas_user') and flask.g.fas_user is not None:
            FAS.logout()
    elif auth == 'local':
        import pagure.ui.login as login
        login.logout()


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
    login_time = flask.g.fas_user.login_time
    # This is because flask_fas_openid will store this as a posix timestamp
    if not isinstance(login_time, datetime.datetime):
        login_time = datetime.datetime.utcfromtimestamp(login_time)
    if (datetime.datetime.utcnow() - login_time) > \
            APP.config.get('ADMIN_SESSION_LIFETIME',
                           datetime.timedelta(minutes=15)):
        timedout = True
        logout()
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

    admin_users = APP.config.get('PAGURE_ADMIN_USERS', [])
    if not isinstance(admin_users, list):
        admin_users = [admin_users]
    if user.username in admin_users:
        return True

    admins = APP.config['ADMIN_GROUP']
    if isinstance(admins, basestring):
        admins = [admins]
    admins = set(admins or [])
    groups = set(flask.g.fas_user.groups)

    return not groups.isdisjoint(admins)


def is_repo_admin(repo_obj):
    """ Return whether the user is an admin of the provided repo. """
    if not authenticated():
        return False

    user = flask.g.fas_user.username

    admin_users = APP.config.get('PAGURE_ADMIN_USERS', [])
    if not isinstance(admin_users, list):
        admin_users = [admin_users]
    if user in admin_users:
        return True

    usergrps = [
        usr.user
        for grp in repo_obj.groups
        for usr in grp.users]

    return user == repo_obj.user.user or (
        user in [usr.user for usr in repo_obj.users]
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


def login_required(function):
    """ Flask decorator to retrict access to logged in user.
    If the auth system is ``fas`` it will also require that the user sign
    the FPCA.
    """
    auth_method = APP.config.get('PAGURE_AUTH', None)

    @wraps(function)
    def decorated_function(*args, **kwargs):
        """ Decorated function, actually does the work. """
        if flask.session.get('_justloggedout', False):
            return flask.redirect(flask.url_for('.index'))
        elif not authenticated():
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

    justlogedout = flask.session.get('_justloggedout', False)
    if justlogedout:
        flask.session['_justloggedout'] = None

    def is_watching(reponame, username=None, namespace=None):
        watch = False
        if authenticated():
            watch = pagure.lib.is_watching(
                SESSION, flask.g.fas_user,
                reponame,
                repouser=username,
                namespace=namespace)
        return watch

    new_user = False
    if flask.session.get('_new_user'):
        new_user = True
        flask.session['_new_user'] = False

    return dict(
        version=__version__,
        admin=user_admin,
        authenticated=authenticated(),
        forkbuttonform=forkbuttonform,
        is_watching=is_watching,
        new_user=new_user,
    )


@APP.before_request
def set_session():
    """ Set the flask session as permanent. """
    flask.session.permanent = True


@APP.before_request
def set_variables():
    """ This method retrieves the repo and username set in the URLs and
    provides some of the variables that are most often used.
    """

    # The API namespace has its own way of getting repo and username and
    # of handling errors
    if flask.request.blueprint == 'api_ns':
        return

    # Retrieve the variables in the URL
    args = flask.request.view_args or {}
    # Check if there is a `repo` and an `username`
    repo = args.get('repo')
    username = args.get('username')
    namespace = args.get('namespace')

    # If there isn't a `repo` in the URL path, or if there is but the
    # endpoint called is part of the API, just don't do anything
    if repo:
        flask.g.repo = pagure.lib.get_project(
            SESSION, repo, user=username, namespace=namespace)
        if authenticated():
            flask.g.repo_forked = pagure.lib.get_project(
                SESSION, repo, user=flask.g.fas_user.username,
                namespace=namespace)

        if not flask.g.repo \
            and APP.config.get('OLD_VIEW_COMMIT_ENABLED', False) \
            and len(repo) == 40:
            return flask.redirect(flask.url_for(
                'view_commit', repo=namespace, commitid=repo,
                username=username, namespace=None))

        if flask.g.repo is None:
            flask.abort(404, 'Project not found')

        flask.g.reponame = get_repo_path(flask.g.repo)
        flask.g.repo_obj = pygit2.Repository(flask.g.reponame)
        flask.g.repo_admin = is_repo_admin(flask.g.repo)
        flask.g.branches = sorted(flask.g.repo_obj.listall_branches())

    items_per_page = 100
    flask.g.offset = 0
    flask.g.page = 1
    flask.g.limit = items_per_page
    page = flask.request.args.get('page')
    limit = flask.request.args.get('n')
    if limit:
        try:
            limit = int(limit)
        except ValueError:
            limit = 10
        if limit > 500 or limit <= 0:
            limit = items_per_page

        flask.g.limit = limit

    if page:
        try:
            page = abs(int(page))
        except ValueError:
            page = 1
        if page <= 0:
            page = 1

        flask.g.page = page
        flask.g.offset = (page - 1) * flask.g.limit


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
    if isinstance(admins, list):
        admins = set(admins)
    else:  # pragma: no cover
        admins = set([admins])

    if APP.config.get('PAGURE_AUTH', None) in ['fas', 'openid']:
        groups = set()
        if not APP.config.get('ENABLE_GROUP_MNGT', False):
            groups = [
                group.group_name
                for group in pagure.lib.search_groups(
                    SESSION, group_type='user')
            ]
        groups = set(groups).union(admins)
        return FAS.login(return_url=return_point, groups=groups)
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

    logout()
    flask.flash("You have been logged out")
    flask.session['_justloggedout'] = True
    return flask.redirect(return_point)


def __get_file_in_tree(repo_obj, tree, filepath, bail_on_tree=False):
    ''' Retrieve the entry corresponding to the provided filename in a
    given tree.
    '''

    filename = filepath[0]
    if isinstance(tree, pygit2.Blob):
        return
    for entry in tree:
        fname = entry.name.decode('utf-8')
        if fname == filename:
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


ip_middle_octet = u"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5]))"
ip_last_octet = u"(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))"

"""
regex based on https://github.com/kvesteri/validators/blob/master/validators/url.py
LICENSED on Dec 16th 2016 as MIT:

The MIT License (MIT)

Copyright (c) 2013-2014 Konsta Vesterinen

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER
IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
urlregex = re.compile(
    u"^"
    # protocol identifier
    u"(?:(?:https?|ftp)://)"
    # user:pass authentication
    u"(?:\S+(?::\S*)?@)?"
    u"(?:"
    u"(?P<private_ip>"
    # IP address exclusion
    # private & local networks
    u"(?:(?:10|127)" + ip_middle_octet + u"{2}" + ip_last_octet + u")|"
    u"(?:(?:169\.254|192\.168)" + ip_middle_octet + ip_last_octet + u")|"
    u"(?:172\.(?:1[6-9]|2\d|3[0-1])" + ip_middle_octet + ip_last_octet + u"))"
    u"|"
    # IP address dotted notation octets
    # excludes loopback network 0.0.0.0
    # excludes reserved space >= 224.0.0.0
    # excludes network & broadcast addresses
    # (first & last IP address of each class)
    u"(?P<public_ip>"
    u"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
    u"" + ip_middle_octet + u"{2}"
    u"" + ip_last_octet + u")"
    u"|"
    # host name
    u"(?:(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)"
    # domain name
    u"(?:\.(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)*"
    # TLD identifier
    u"(?:\.(?:[a-z\u00a1-\uffff]{2,}))"
    u")"
    # port number
    u"(?::\d{2,5})?"
    # resource path
    u"(?:/\S*)?"
    u"$",
    re.UNICODE | re.IGNORECASE
)
urlpattern = re.compile(urlregex)

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
    APP.before_request_funcs[None].insert(0, login._check_session_cookie)
    APP.after_request(login._send_session_cookie)


# pylint: disable=unused-argument
@APP.teardown_request
def shutdown_session(exception=None):
    """ Remove the DB session at the end of each request. """
    SESSION.remove()
