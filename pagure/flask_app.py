# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import gc
import logging
import string
import time
import os
import warnings
from six.moves.urllib.parse import urljoin

import flask
import pygit2

from whitenoise import WhiteNoise

import pagure.doc_utils
import pagure.exceptions
import pagure.forms
import pagure.lib.git
import pagure.lib.query
import pagure.login_forms
import pagure.mail_logging
import pagure.proxy
import pagure.utils
from pagure.config import config as pagure_config
from pagure.utils import get_repo_path

if os.environ.get("PAGURE_PERFREPO"):
    import pagure.perfrepo as perfrepo
else:
    perfrepo = None


logger = logging.getLogger(__name__)

REDIS = None
if (
    pagure_config["EVENTSOURCE_SOURCE"]
    or pagure_config["WEBHOOK"]
    or pagure_config.get("PAGURE_CI_SERVICES")
):
    pagure.lib.query.set_redis(
        host=pagure_config.get("REDIS_HOST", None),
        port=pagure_config.get("REDIS_PORT", None),
        socket=pagure_config.get("REDIS_SOCKET", None),
        dbname=pagure_config["REDIS_DB"],
    )


if pagure_config.get("PAGURE_CI_SERVICES"):
    pagure.lib.query.set_pagure_ci(pagure_config["PAGURE_CI_SERVICES"])


def create_app(config=None):
    """ Create the flask application. """
    app = flask.Flask(__name__)
    app.config = pagure_config

    if config:
        app.config.update(config)

    if app.config.get("SESSION_TYPE", None) is not None:
        import flask_session

        flask_session.Session(app)

    pagure.utils.set_up_logging(app=app)

    @app.errorhandler(500)
    def fatal_error(error):  # pragma: no cover
        """500 Fatal Error page"""
        logger.exception("Error while processing request")
        return flask.render_template("fatal_error.html", error=error), 500

    app.jinja_env.trim_blocks = True
    app.jinja_env.lstrip_blocks = True

    if perfrepo:
        # Do this as early as possible.
        # We want the perfrepo before_request to be the very first thing
        # to be run, so that we can properly setup the stats before the
        # request.
        app.before_request(perfrepo.reset_stats)

    auth = pagure_config.get("PAGURE_AUTH", None)
    if auth in ["fas", "openid"]:
        # Only import and set flask_fas_openid if it is needed
        from pagure.ui.fas_login import FAS

        FAS.init_app(app)
    elif auth == "oidc":
        # Only import and set flask_fas_openid if it is needed
        from pagure.ui.oidc_login import oidc, fas_user_from_oidc

        oidc.init_app(app)
        app.before_request(fas_user_from_oidc)
    if auth == "local":
        # Only import the login controller if the app is set up for local login
        import pagure.ui.login as login

        app.before_request(login._check_session_cookie)
        app.after_request(login._send_session_cookie)

    # Support proxy
    app.wsgi_app = pagure.proxy.ReverseProxied(app.wsgi_app)

    # Back port 'equalto' to older version of jinja2
    app.jinja_env.tests.setdefault(
        "equalto", lambda value, other: value == other
    )

    # Import the application

    from pagure.api import API  # noqa: E402

    app.register_blueprint(API)

    from pagure.ui import UI_NS  # noqa: E402

    app.register_blueprint(UI_NS)

    from pagure.internal import PV  # noqa: E402

    app.register_blueprint(PV)

    # Import 3rd party blueprints
    plugin_config = flask.config.Config("")
    if "PAGURE_PLUGIN" in os.environ:
        # Warn the user about deprecated variable (defaults to stderr)
        warnings.warn(
            "The environment variable PAGURE_PLUGIN is deprecated and will be "
            "removed in future releases of Pagure. Please replace it with "
            "PAGURE_PLUGINS_CONFIG instead.",
            FutureWarning,
        )

        # Log usage of deprecated variable
        logger.warning(
            "Using deprecated variable PAGURE_PLUGIN. "
            "You should use PAGURE_PLUGINS_CONFIG instead."
        )

        plugin_config.from_envvar("PAGURE_PLUGIN")

    elif "PAGURE_PLUGINS_CONFIG" in os.environ:
        plugin_config.from_envvar("PAGURE_PLUGINS_CONFIG")

    elif "PAGURE_PLUGINS_CONFIG" in app.config:
        # If the os.environ["PAGURE_PLUGINS_CONFIG"] is not set, we try to load
        # it from the pagure config file.
        plugin_config.from_pyfile(app.config.get("PAGURE_PLUGINS_CONFIG"))

    for blueprint in plugin_config.get("PLUGINS") or []:
        logger.info("Loading blueprint: %s", blueprint.name)
        app.register_blueprint(blueprint)

    themename = pagure_config.get("THEME", "default")
    here = os.path.abspath(
        os.path.join(os.path.dirname(os.path.abspath(__file__)))
    )
    themeblueprint = flask.Blueprint(
        "theme",
        __name__,
        static_url_path="/theme/static",
        static_folder=os.path.join(here, "themes", themename, "static"),
    )
    # Jinja can be told to look for templates in different folders
    # That's what we do here
    template_folders = os.path.join(
        app.root_path,
        app.template_folder,
        os.path.join(here, "themes", themename, "templates"),
    )
    import jinja2

    # Jinja looks for the template in the order of the folders specified
    templ_loaders = [
        jinja2.FileSystemLoader(template_folders),
        app.jinja_loader,
    ]
    app.jinja_loader = jinja2.ChoiceLoader(templ_loaders)
    app.register_blueprint(themeblueprint)

    # Setup WhiteNoise for serving static files
    app.wsgi_app = WhiteNoise(
        app.wsgi_app, root=os.path.join(here, "static"), prefix="/static"
    )

    app.before_request(set_request)
    app.after_request(after_request)
    app.teardown_request(end_request)

    if perfrepo:
        # Do this at the very end, so that this after_request comes last.
        app.after_request(perfrepo.print_stats)

    app.add_url_rule("/login/", view_func=auth_login, methods=["GET", "POST"])
    app.add_url_rule("/logout/", view_func=auth_logout)

    return app


def generate_user_key_files():
    """Regenerate the key files used by gitolite."""
    gitolite_home = pagure_config.get("GITOLITE_HOME", None)
    if gitolite_home:
        users = pagure.lib.query.search_user(flask.g.session)
        for user in users:
            pagure.lib.query.update_user_ssh(
                flask.g.session,
                user,
                None,
                pagure_config.get("GITOLITE_KEYDIR", None),
                update_only=True,
            )
    pagure.lib.git.generate_gitolite_acls(project=None)


def admin_session_timedout():
    """Check if the current user has been authenticated for more than what
    is allowed (defaults to 15 minutes).
    If it is the case, the user is logged out and the method returns True,
    otherwise it returns False.
    """
    timedout = False
    if not pagure.utils.authenticated():
        return True
    login_time = flask.g.fas_user.login_time
    # This is because flask_fas_openid will store this as a posix timestamp
    if not isinstance(login_time, datetime.datetime):
        login_time = datetime.datetime.utcfromtimestamp(login_time)
    if (datetime.datetime.utcnow() - login_time) > pagure_config.get(
        "ADMIN_SESSION_LIFETIME", datetime.timedelta(minutes=15)
    ):
        timedout = True
        logout()
    return timedout


def logout():
    """Log out the user currently logged in in the application"""
    auth = pagure_config.get("PAGURE_AUTH", None)
    if auth in ["fas", "openid"]:
        if hasattr(flask.g, "fas_user") and flask.g.fas_user is not None:
            from pagure.ui.fas_login import FAS

            FAS.logout()
    elif auth == "oidc":
        from pagure.ui.oidc_login import oidc_logout

        oidc_logout()
    elif auth == "local":
        import pagure.ui.login as login

        login.logout()


def set_request():
    """ Prepare every request. """
    flask.session.permanent = True
    if not hasattr(flask.g, "session") or not flask.g.session:
        flask.g.session = pagure.lib.model_base.create_session(
            flask.current_app.config["DB_URL"]
        )

    flask.g.main_app = flask.current_app
    flask.g.version = pagure.__version__
    flask.g.confirmationform = pagure.forms.ConfirmationForm()
    flask.g.nonce = pagure.lib.login.id_generator(
        size=25, chars=string.ascii_letters + string.digits
    )

    flask.g.issues_enabled = pagure_config.get("ENABLE_TICKETS", True)

    # The API namespace has its own way of getting repo and username and
    # of handling errors
    if flask.request.blueprint == "api_ns":
        return

    flask.g.forkbuttonform = None
    if pagure.utils.authenticated():
        flask.g.forkbuttonform = pagure.forms.ConfirmationForm()

        # Force logout if current session started before users'
        # refuse_sessions_before
        login_time = flask.g.fas_user.login_time
        # This is because flask_fas_openid will store this as a posix timestamp
        if not isinstance(login_time, datetime.datetime):
            login_time = datetime.datetime.utcfromtimestamp(login_time)
        user = _get_user(username=flask.g.fas_user.username)
        if (
            user.refuse_sessions_before
            and login_time < user.refuse_sessions_before
        ):
            logout()
            return flask.redirect(flask.url_for("ui_ns.index"))

    flask.g.justlogedout = flask.session.get("_justloggedout", False)
    if flask.g.justlogedout:
        flask.session["_justloggedout"] = None

    flask.g.new_user = False
    if flask.session.get("_new_user"):
        flask.g.new_user = True
        flask.session["_new_user"] = False

    flask.g.authenticated = pagure.utils.authenticated()
    flask.g.admin = pagure.utils.is_admin()

    # Retrieve the variables in the URL
    args = flask.request.view_args or {}
    # Check if there is a `repo` and an `username`
    repo = args.get("repo")
    username = args.get("username")
    namespace = args.get("namespace")

    # If there isn't a `repo` in the URL path, or if there is but the
    # endpoint called is part of the API, just don't do anything
    if repo:
        flask.g.repo = pagure.lib.query.get_authorized_project(
            flask.g.session, repo, user=username, namespace=namespace
        )
        if flask.g.authenticated:
            flask.g.repo_forked = pagure.lib.query.get_authorized_project(
                flask.g.session,
                repo,
                user=flask.g.fas_user.username,
                namespace=namespace,
            )
            flask.g.repo_starred = pagure.lib.query.has_starred(
                flask.g.session, flask.g.repo, user=flask.g.fas_user.username
            )

            # Block all POST request from blocked users
            if flask.g.repo and flask.request.method != "GET":
                if flask.g.fas_user.username in flask.g.repo.block_users:
                    flask.abort(
                        403,
                        description="You have been blocked from this project",
                    )

        if (
            not flask.g.repo
            and namespace
            and pagure_config.get("OLD_VIEW_COMMIT_ENABLED", False)
            and len(repo) == 40
        ):
            return flask.redirect(
                flask.url_for(
                    "ui_ns.view_commit",
                    repo=namespace,
                    commitid=repo,
                    username=username,
                    namespace=None,
                )
            )

        if flask.g.repo is None:
            flask.abort(404, description="Project not found")

        # If issues are not globally enabled, there is no point in continuing
        if flask.g.issues_enabled:

            ticket_namespaces = pagure_config.get("ENABLE_TICKETS_NAMESPACE")

            if ticket_namespaces and flask.g.repo.namespace:
                if flask.g.repo.namespace in (ticket_namespaces or []):
                    # If the namespace is in the allowed list
                    # issues are enabled
                    flask.g.issues_enabled = True
                else:
                    # If the namespace isn't in the list of namespaces
                    # issues are disabled
                    flask.g.issues_enabled = False

            flask.g.issues_project_disabled = False
            if not flask.g.repo.settings.get("issue_tracker", True):
                # If the project specifically disabled its issue tracker,
                # disable issues
                flask.g.issues_project_disabled = True
                flask.g.issues_enabled = False

        flask.g.reponame = get_repo_path(flask.g.repo)
        flask.g.repo_obj = pygit2.Repository(flask.g.reponame)
        flask.g.repo_admin = pagure.utils.is_repo_admin(flask.g.repo)
        flask.g.repo_committer = pagure.utils.is_repo_committer(flask.g.repo)
        if flask.g.authenticated and not flask.g.repo_committer:
            flask.g.repo_committer = flask.g.fas_user.username in [
                u.user.username for u in flask.g.repo.collaborators
            ]

        flask.g.repo_user = pagure.utils.is_repo_user(flask.g.repo)
        flask.g.branches = sorted(flask.g.repo_obj.listall_branches())

        repouser = flask.g.repo.user.user if flask.g.repo.is_fork else None
        fas_user = flask.g.fas_user if pagure.utils.authenticated() else None
        flask.g.repo_watch_levels = pagure.lib.query.get_watch_level_on_repo(
            flask.g.session,
            fas_user,
            flask.g.repo.name,
            repouser=repouser,
            namespace=namespace,
        )

    items_per_page = pagure_config["ITEM_PER_PAGE"]
    flask.g.offset = 0
    flask.g.page = 1
    flask.g.limit = items_per_page
    page = flask.request.args.get("page")
    limit = flask.request.args.get("n")
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


def auth_login():  # pragma: no cover
    """ Method to log into the application using FAS OpenID. """
    return_point = flask.url_for("ui_ns.index")
    if "next" in flask.request.args:
        if pagure.utils.is_safe_url(flask.request.args["next"]):
            return_point = urljoin(
                flask.request.host_url, flask.request.args["next"]
            )

    authenticated = pagure.utils.authenticated()
    auth = pagure_config.get("PAGURE_AUTH", None)

    if not authenticated and auth == "oidc":
        from pagure.ui.oidc_login import oidc, fas_user_from_oidc, set_user

        # If oidc is used and user hits this endpoint, it will redirect
        # to IdP with destination=<pagure>/login?next=<location>
        # After confirming user identity, the IdP will redirect user here
        # again, but this time oidc.user_loggedin will be True and thus
        # execution will go through the else clause, making the Pagure
        # authentication machinery pick the user up
        if not oidc.user_loggedin:
            return oidc.redirect_to_auth_server(flask.request.url)
        else:
            flask.session["oidc_logintime"] = time.time()
            fas_user_from_oidc()
            authenticated = pagure.utils.authenticated()
            set_user()

    if authenticated:
        return flask.redirect(return_point)

    admins = pagure_config["ADMIN_GROUP"]
    if admins:
        if isinstance(admins, list):
            admins = set(admins)
        else:  # pragma: no cover
            admins = set([admins])
    else:
        admins = set()

    if auth in ["fas", "openid"]:
        from pagure.ui.fas_login import FAS

        groups = set()
        if not pagure_config.get("ENABLE_GROUP_MNGT", False):
            groups = [
                group.group_name
                for group in pagure.lib.query.search_groups(
                    flask.g.session, group_type="user"
                )
            ]
        groups = set(groups).union(admins)
        if auth == "fas":
            groups.add("signed_fpca")
        ext_committer = set(pagure_config.get("EXTERNAL_COMMITTER", {}))
        groups = set(groups).union(ext_committer)
        flask.g.unsafe_javascript = True
        return FAS.login(return_url=return_point, groups=groups)
    elif auth == "local":
        form = pagure.login_forms.LoginForm()
        return flask.render_template(
            "login/login.html", next_url=return_point, form=form
        )


def auth_logout():  # pragma: no cover
    """ Method to log out from the application. """
    return_point = flask.url_for("ui_ns.index")
    if "next" in flask.request.args:
        if pagure.utils.is_safe_url(flask.request.args["next"]):
            return_point = urljoin(
                flask.request.host_url, flask.request.args["next"]
            )

    if not pagure.utils.authenticated():
        return flask.redirect(return_point)

    logout()
    flask.flash("You have been logged out")
    flask.session["_justloggedout"] = True
    return flask.redirect(return_point)


# pylint: disable=unused-argument
def end_request(exception=None):
    """This method is called at the end of each request.

    Remove the DB session at the end of each request.
    Runs a garbage collection to get rid of any open pygit2 handles.
        Details: https://pagure.io/pagure/issue/2302

    """
    flask.g.session.remove()
    gc.collect()


def after_request(response):
    """ After request callback, adjust the headers returned """
    if not hasattr(flask.g, "nonce"):
        return response

    csp_headers = pagure_config["CSP_HEADERS"]
    try:
        style_csp = "nonce-" + flask.g.nonce
        script_csp = (
            "unsafe-inline"
            if "unsafe_javascript" in flask.g and flask.g.unsafe_javascript
            else "nonce-" + flask.g.nonce
        )
        csp_headers = csp_headers.format(
            nonce_script=script_csp, nonce_style=style_csp
        )
    except (KeyError, IndexError):
        pass
    response.headers.set(str("Content-Security-Policy"), csp_headers)
    return response


def _get_user(username):
    """Check if user exists or not"""
    try:
        return pagure.lib.query.get_user(flask.g.session, username)
    except pagure.exceptions.PagureException as e:
        flask.abort(404, description="%s" % e)
