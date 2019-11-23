# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

API namespace version 0.

"""

# pylint: disable=invalid-name
# pylint: disable=too-few-public-methods
# pylint: disable=too-many-locals

from __future__ import unicode_literals, absolute_import

import codecs
import functools
import logging
import os

import docutils
import enum
import flask
import markupsafe
from six.moves.urllib_parse import urljoin

API = flask.Blueprint("api_ns", __name__, url_prefix="/api/0")


import pagure.lib.query  # noqa: E402
import pagure.lib.tasks  # noqa: E402
from pagure.config import config as pagure_config  # noqa: E402
from pagure.doc_utils import load_doc, modify_rst, modify_html  # noqa: E402
from pagure.exceptions import APIError  # noqa: E402
from pagure.utils import authenticated, check_api_acls  # noqa: E402


_log = logging.getLogger(__name__)


def preload_docs(endpoint):
    """ Utility to load an RST file and turn it into fancy HTML. """

    here = os.path.dirname(os.path.abspath(__file__))
    fname = os.path.join(here, "..", "doc", endpoint + ".rst")
    with codecs.open(fname, "r", "utf-8") as stream:
        rst = stream.read()

    rst = modify_rst(rst)
    api_docs = docutils.examples.html_body(rst)
    api_docs = modify_html(api_docs)
    api_docs = markupsafe.Markup(api_docs)
    return api_docs


APIDOC = preload_docs("api")


class APIERROR(enum.Enum):
    """ Clast listing as Enum all the possible error thrown by the API.
    """

    ENOCODE = "Variable message describing the issue"
    ENOPROJECT = "Project not found"
    ENOPROJECTS = "No projects found"
    ETRACKERDISABLED = "Issue tracker disabled for this project"
    EDBERROR = (
        "An error occurred at the database level and prevent the "
        + "action from reaching completion"
    )
    EINVALIDREQ = "Invalid or incomplete input submitted"
    EINVALIDTOK = (
        "Invalid or expired token. Please visit %s to get or "
        "renew your API token."
        % urljoin(pagure_config["APP_URL"], "settings#nav-api-tab")
    )
    ENOISSUE = "Issue not found"
    EISSUENOTALLOWED = "You are not allowed to view this issue"
    EPRNOTALLOWED = "You are not allowed to view this pull-request"
    EPULLREQUESTSDISABLED = (
        "Pull-Request have been deactivated for this project"
    )
    ENOREQ = "Pull-Request not found"
    ENOPRCLOSE = (
        "You are not allowed to merge/close pull-request for this project"
    )
    EPRSCORE = (
        "This request does not have the minimum review score "
        "necessary to be merged"
    )
    EPRCONFLICTS = "This pull-request conflicts and thus cannot be merged"
    ENOTASSIGNEE = "Only the assignee can merge this request"
    ENOTASSIGNED = "This request must be assigned to be merged"
    ENOUSER = "No such user found"
    ENOCOMMENT = "Comment not found"
    ENEWPROJECTDISABLED = (
        "Creating project have been disabled for this instance"
    )
    ETIMESTAMP = "Invalid timestamp format"
    EDATETIME = "Invalid datetime format"
    EINVALIDISSUEFIELD = "Invalid custom field submitted"
    EINVALIDISSUEFIELD_LINK = (
        "Invalid custom field submitted, the value is not a link"
    )
    EINVALIDPRIORITY = "Invalid priority submitted"
    ENOGROUP = "Group not found"
    ENOTMAINADMIN = "Only the main admin can set the main admin of a project"
    EMODIFYPROJECTNOTALLOWED = "You are not allowed to modify this project"
    EINVALIDPERPAGEVALUE = "The per_page value must be between 1 and 100"
    EGITERROR = "An error occurred during a git operation"
    ENOCOMMIT = "No such commit found in this repository"
    ENOTHIGHENOUGH = (
        "You do not have sufficient permissions to perform this action"
    )
    ENOSIGNEDOFF = (
        "This repo enforces that all commits are signed off "
        "by their author."
    )
    ETRACKERREADONLY = "The issue tracker of this project is read-only"
    ENOPRSTATS = "No statistics could be computed for this PR"
    EUBLOCKED = "You have been blocked from this project"
    EREBASENOTALLOWED = "You are not authorized to rebase this pull-request"
    ENOPLUGIN = "No such plugin"
    EPLUGINDISABLED = "Plugin disabled"
    EPLUGINCHANGENOTALLOWED = "This plugin cannot be changed"
    EPLUGINNOTINSTALLED = "Project doesn't have this plugin installed"
    ENOTAG = "Tag not found"


def get_authorized_api_project(session, repo, user=None, namespace=None):
    """ Helper function to get an authorized_project with optional lock. """
    repo = pagure.lib.query.get_authorized_project(
        flask.g.session, repo, user=user, namespace=namespace
    )
    flask.g.repo = repo
    return repo


def get_request_data():
    return flask.request.form or flask.request.get_json() or {}


def api_login_required(acls=None):
    """ Decorator used to indicate that authentication is required for some
    API endpoint.
    """

    def decorator(function):
        """ The decorator of the function """

        @functools.wraps(function)
        def decorated_function(*args, **kwargs):
            """ Actually does the job with the arguments provided. """

            response = check_api_acls(acls)
            if response:
                return response

            # Block all POST request from blocked users
            if flask.request.method == "POST":
                # Retrieve the variables in the URL
                url_args = flask.request.view_args or {}
                # Check if there is a `repo` and an `username`
                repo = url_args.get("repo")
                username = url_args.get("username")
                namespace = url_args.get("namespace")

                if repo:
                    flask.g.repo = pagure.lib.query.get_authorized_project(
                        flask.g.session,
                        repo,
                        user=username,
                        namespace=namespace,
                    )

                    if (
                        flask.g.repo
                        and flask.g.fas_user.username
                        in flask.g.repo.block_users
                    ):
                        output = {
                            "error": APIERROR.EUBLOCKED.value,
                            "error_code": APIERROR.EUBLOCKED.name,
                        }
                        response = flask.jsonify(output)
                        response.status_code = 403
                        return response

            return function(*args, **kwargs)

        return decorated_function

    return decorator


def api_login_optional(acls=None):
    """ Decorator used to indicate that authentication is optional for some
    API endpoint.
    """

    def decorator(function):
        """ The decorator of the function """

        @functools.wraps(function)
        def decorated_function(*args, **kwargs):
            """ Actually does the job with the arguments provided. """

            response = check_api_acls(acls, optional=True)
            if response:
                return response
            return function(*args, **kwargs)

        return decorated_function

    return decorator


def api_method(function):
    """ Runs an API endpoint and catch all the APIException thrown. """

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        """ Actually does the job with the arguments provided. """
        try:
            result = function(*args, **kwargs)
        except APIError as err:
            if err.error_code in [APIERROR.EDBERROR]:
                _log.exception(err)

            if err.error_code in [APIERROR.ENOCODE]:
                output = {
                    "error": err.error,
                    "error_code": err.error_code.name,
                }
            else:
                output = {
                    "error": err.error_code.value,
                    "error_code": err.error_code.name,
                }

            if err.errors:
                output["errors"] = err.errors
            response = flask.jsonify(output)
            response.status_code = err.status_code
        else:
            response = result

        return response

    return wrapper


def get_page():
    """ Returns the page value specified in the request.
    Defaults to 1.
    raises APIERROR.EINVALIDREQ if the page provided isn't an integer
    raises APIERROR.EINVALIDREQ if the page provided is lower than 1
    """

    page = flask.request.values.get("page", None)
    if not page:
        page = 1
    else:
        try:
            page = int(page)
        except (TypeError, ValueError):
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EINVALIDREQ
            )

        if page < 1:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EINVALIDREQ
            )

    return page


def get_per_page():
    """ Returns the per_page value specified in the request.
    Defaults to 20.
    raises APIERROR.EINVALIDREQ if the page provided isn't an integer
    raises APIERROR.EINVALIDPERPAGEVALUE if the page provided is lower
        than 1 or greater than 100
    """
    per_page = flask.request.values.get("per_page", None) or 20
    if per_page:
        try:
            per_page = int(per_page)
        except (TypeError, ValueError):
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EINVALIDREQ
            )

        if per_page < 1 or per_page > 100:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EINVALIDPERPAGEVALUE
            )

    return per_page


if pagure_config.get("ENABLE_TICKETS", True):
    from pagure.api import issue  # noqa: E402
from pagure.api import fork  # noqa: E402
from pagure.api import project  # noqa: E402
from pagure.api import user  # noqa: E402
from pagure.api import group  # noqa: E402
from pagure.api import plugins  # noqa: E402

if pagure_config.get("PAGURE_CI_SERVICES", False):
    from pagure.api.ci import jenkins  # noqa: E402


@API.route("/version/")
@API.route("/version")
@API.route("/-/version")
def api_version():
    """
    API Version
    -----------
    Get the current API version.

    ::

        GET /api/0/-/version

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "version": "1"
        }

    """
    return flask.jsonify({"version": pagure.__api_version__})


@API.route("/users/")
@API.route("/users")
def api_users():
    """
    List users
    -----------
    Retrieve users that have logged into the Pagure instance.
    This can then be used as input for autocompletion in some forms/fields.

    ::

        GET /api/0/users

    Parameters
    ^^^^^^^^^^

    +---------------+----------+---------------+------------------------------+
    | Key           | Type     | Optionality   | Description                  |
    +===============+==========+===============+==============================+
    | ``pattern``   | string   | Optional      | | Filters the starting       |
    |               |          |               |   letters of the usernames   |
    +---------------+----------+---------------+------------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "total_users": 2,
          "users": ["user1", "user2"]
        }

    """
    pattern = flask.request.args.get("pattern", None)
    if pattern is not None and not pattern.endswith("*"):
        pattern += "*"

    users = pagure.lib.query.search_user(flask.g.session, pattern=pattern)

    return flask.jsonify(
        {
            "total_users": len(users),
            "users": [usr.username for usr in users],
            "mention": [
                {
                    "username": usr.username,
                    "name": usr.fullname,
                    "image": pagure.lib.query.avatar_url_from_email(
                        usr.default_email, size=16
                    ),
                }
                for usr in users
            ],
        }
    )


@API.route("/-/whoami", methods=["POST"])
@api_login_optional()
def api_whoami():
    """
    Who am I?
    ---------
    This API endpoint will return the username associated with the provided
    API token.

    ::

        POST /api/0/-/whoami


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "username": "user1"
        }

    """

    if authenticated():
        return flask.jsonify({"username": flask.g.fas_user.username})
    else:
        output = {
            "error_code": APIERROR.EINVALIDTOK.name,
            "error": APIERROR.EINVALIDTOK.value,
        }
        jsonout = flask.jsonify(output)
        jsonout.status_code = 401
        return jsonout


@API.route("/task/<taskid>/status")
@API.route("/task/<taskid>/status/")
def api_task_status(taskid):
    """
    Return the status of a async task
    """
    result = pagure.lib.tasks.get_result(taskid)
    if not result.ready():
        output = {"ready": False, "status": result.status}
    else:
        output = {
            "ready": True,
            "successful": result.successful(),
            "status": result.status,
        }

    return flask.jsonify(output)


@API.route("/error_codes/")
@API.route("/error_codes")
@API.route("/-/error_codes")
def api_error_codes():
    """
    Error codes
    ------------
    Get a dictionary (hash) of all error codes.

    ::

        GET /api/0/-/error_codes

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          ENOCODE: 'Variable message describing the issue',
          ENOPROJECT: 'Project not found',
        }

    """
    errors = {
        val.name: val.value for val in APIERROR.__members__.values()
    }  # pylint: disable=no-member

    return flask.jsonify(errors)


@API.route("/")
def api():
    """ Display the api information page. """
    api_project_doc = load_doc(project.api_project)
    api_projects_doc = load_doc(project.api_projects)
    api_project_watchers_doc = load_doc(project.api_project_watchers)
    api_project_tags_doc = load_doc(project.api_project_tags)
    api_project_tags_new_doc = load_doc(project.api_project_tags_new)
    api_git_tags_doc = load_doc(project.api_git_tags)
    api_project_git_urls_doc = load_doc(project.api_project_git_urls)
    api_git_branches_doc = load_doc(project.api_git_branches)
    api_new_project_doc = load_doc(project.api_new_project)
    api_modify_project_doc = load_doc(project.api_modify_project)
    api_fork_project_doc = load_doc(project.api_fork_project)
    api_modify_acls_doc = load_doc(project.api_modify_acls)
    api_generate_acls_doc = load_doc(project.api_generate_acls)
    api_new_branch_doc = load_doc(project.api_new_branch)
    api_commit_flags_doc = load_doc(project.api_commit_flags)
    api_commit_add_flag_doc = load_doc(project.api_commit_add_flag)
    api_update_project_watchers_doc = load_doc(
        project.api_update_project_watchers
    )
    api_get_project_options_doc = load_doc(project.api_get_project_options)
    api_modify_project_options_doc = load_doc(
        project.api_modify_project_options
    )
    api_project_block_user_doc = load_doc(project.api_project_block_user)

    issues = []
    if pagure_config.get("ENABLE_TICKETS", True):
        issues.append(load_doc(issue.api_new_issue))
        issues.append(load_doc(issue.api_view_issues))
        issues.append(load_doc(issue.api_view_issue))
        issues.append(load_doc(issue.api_view_issue_comment))
        issues.append(load_doc(issue.api_comment_issue))
        issues.append(load_doc(issue.api_update_custom_field))
        issues.append(load_doc(issue.api_update_custom_fields))
        issues.append(load_doc(issue.api_change_status_issue))
        issues.append(load_doc(issue.api_change_milestone_issue))
        issues.append(load_doc(issue.api_assign_issue))
        issues.append(load_doc(issue.api_subscribe_issue))
        issues.append(load_doc(user.api_view_user_issues))

    ci_doc = []
    if pagure_config.get("PAGURE_CI_SERVICES", False):
        if "jenkins" in pagure_config["PAGURE_CI_SERVICES"]:
            ci_doc.append(load_doc(jenkins.jenkins_ci_notification))

    api_pull_request_create_doc = load_doc(fork.api_pull_request_create)
    api_pull_request_views_doc = load_doc(fork.api_pull_request_views)
    api_pull_request_view_doc = load_doc(fork.api_pull_request_view)
    api_pull_request_diffstats_doc = load_doc(fork.api_pull_request_diffstats)
    api_pull_request_by_uid_view_doc = load_doc(
        fork.api_pull_request_by_uid_view
    )
    api_pull_request_merge_doc = load_doc(fork.api_pull_request_merge)
    api_pull_request_rebase_doc = load_doc(fork.api_pull_request_rebase)
    api_pull_request_close_doc = load_doc(fork.api_pull_request_close)
    api_pull_request_add_comment_doc = load_doc(
        fork.api_pull_request_add_comment
    )
    api_pull_request_add_flag_doc = load_doc(fork.api_pull_request_add_flag)
    api_pull_request_assign_doc = load_doc(fork.api_pull_request_assign)
    api_pull_request_update_doc = load_doc(fork.api_pull_request_update)

    api_version_doc = load_doc(api_version)
    api_whoami_doc = load_doc(api_whoami)
    api_users_doc = load_doc(api_users)
    api_view_user_doc = load_doc(user.api_view_user)
    api_view_user_activity_stats_doc = load_doc(
        user.api_view_user_activity_stats
    )
    api_view_user_activity_date_doc = load_doc(
        user.api_view_user_activity_date
    )
    api_view_user_requests_filed_doc = load_doc(
        user.api_view_user_requests_filed
    )
    api_view_user_requests_actionable_doc = load_doc(
        user.api_view_user_requests_actionable
    )

    api_view_group_doc = load_doc(group.api_view_group)
    api_groups_doc = load_doc(group.api_groups)

    api_install_plugin_doc = load_doc(plugins.api_install_plugin)
    api_remove_plugin_doc = load_doc(plugins.api_remove_plugin)
    api_view_plugins_project_doc = load_doc(plugins.api_view_plugins_project)
    api_view_plugins_doc = load_doc(plugins.api_view_plugins)

    api_error_codes_doc = load_doc(api_error_codes)

    extras = [api_whoami_doc, api_version_doc, api_error_codes_doc]

    return flask.render_template(
        "api.html",
        version=pagure.__api_version__,
        api_doc=APIDOC,
        projects=[
            api_new_project_doc,
            api_modify_project_doc,
            api_project_doc,
            api_projects_doc,
            api_project_tags_doc,
            api_project_tags_new_doc,
            api_git_tags_doc,
            api_project_git_urls_doc,
            api_project_watchers_doc,
            api_git_branches_doc,
            api_fork_project_doc,
            api_modify_acls_doc,
            api_generate_acls_doc,
            api_new_branch_doc,
            api_commit_flags_doc,
            api_commit_add_flag_doc,
            api_update_project_watchers_doc,
            api_get_project_options_doc,
            api_modify_project_options_doc,
            api_project_block_user_doc,
        ],
        issues=issues,
        requests=[
            api_pull_request_create_doc,
            api_pull_request_views_doc,
            api_pull_request_view_doc,
            api_pull_request_diffstats_doc,
            api_pull_request_by_uid_view_doc,
            api_pull_request_merge_doc,
            api_pull_request_rebase_doc,
            api_pull_request_close_doc,
            api_pull_request_add_comment_doc,
            api_pull_request_add_flag_doc,
            api_pull_request_assign_doc,
            api_pull_request_update_doc,
        ],
        users=[
            api_users_doc,
            api_view_user_doc,
            api_view_user_activity_stats_doc,
            api_view_user_activity_date_doc,
            api_view_user_requests_filed_doc,
            api_view_user_requests_actionable_doc,
        ],
        groups=[api_groups_doc, api_view_group_doc],
        plugins=[
            api_install_plugin_doc,
            api_remove_plugin_doc,
            api_view_plugins_project_doc,
            api_view_plugins_doc,
        ],
        ci=ci_doc,
        extras=extras,
    )
