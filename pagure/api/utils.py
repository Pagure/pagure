# -*- coding: utf-8 -*-

"""
 (c) 2015-2019 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import print_function, unicode_literals, absolute_import

import flask
import logging


import pagure.exceptions

from pagure.lib import plugins

from pagure.config import config as pagure_config
from pagure.api import APIERROR, get_authorized_api_project

from pagure.utils import api_authenticated, is_repo_committer, is_repo_user


_log = logging.getLogger(__name__)


def _get_repo(repo_name, username=None, namespace=None):
    """Check if repository exists and get repository name
    :param repo_name: name of repository
    :param username:
    :param namespace:
    :raises pagure.exceptions.APIError: when repository doesn't exist or
        is disabled
    :return: repository name
    """
    repo = get_authorized_api_project(
        flask.g.session, repo_name, user=username, namespace=namespace
    )

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    return repo


def _check_token(repo, project_token=True):
    """Check if token is valid for the repo
    :param repo: repository name
    :param project_token: set True when project token is required,
        otherwise any token can be used
    :raises pagure.exceptions.APIError: when token is not valid for repo
    """
    if api_authenticated():
        # if there is a project associated with the token, check it
        # if there is no project associated, check if it is required
        if (
            flask.g.token.project is not None and repo != flask.g.token.project
        ) or (flask.g.token.project is None and project_token):
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK
            )


def _get_issue(repo, issueid, issueuid=None):
    """Get issue and check permissions
    :param repo: repository name
    :param issueid: issue ID
    :param issueuid: issue Unique ID
    :raises pagure.exceptions.APIError: when issues doesn't exists
    :return: issue
    """
    issue = pagure.lib.query.search_issues(
        flask.g.session, repo, issueid=issueid, issueuid=issueuid
    )

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOISSUE)

    return issue


def _get_request(repo=None, requestid=None, requestuid=None):
    """Get pull-request if it exists
    :param repo: repository name
    :param requestid: pull-request ID
    :param requestuid: pull-request Unique ID
    :raises pagure.exceptions.APIError: when pull-request doesn't exists
    :return: issue
    """
    request = None
    if repo and requestid:
        request = pagure.lib.query.search_pull_requests(
            flask.g.session, project_id=repo.id, requestid=requestid
        )
    elif requestuid:
        request = pagure.lib.query.get_request_by_uid(
            flask.g.session, requestuid
        )

    if not request or (repo and request.project != repo):
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    return request


def _check_issue_tracker(repo):
    """Check if issue tracker is enabled for repository
    :param repo: repository
    :raises pagure.exceptions.APIError: when issue tracker is disabled
    """
    enable_tickets = pagure_config.get("ENABLE_TICKETS")
    ticket_namespaces = pagure_config.get("ENABLE_TICKETS_NAMESPACE")
    if (
        (
            ticket_namespaces
            and repo.namespace
            and repo.namespace not in ticket_namespaces
        )
        or not enable_tickets
        or not repo.settings.get("issue_tracker", True)
    ):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED
        )

    # forbid all POST requests if the issue tracker is made read-only
    if flask.request.method == "POST" and repo.settings.get(
        "issue_tracker_read_only", False
    ):
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.ETRACKERREADONLY
        )


def _check_pull_request(repo):
    """Check if pull-requests are enabled for repository
    :param repo: repository
    :raises pagure.exceptions.APIError: when issue tracker is disabled
    """
    if not repo.settings.get("pull_requests", True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED
        )


def _check_ticket_access(issue, assignee=False, open_access=False):
    """Check if user can access issue. Must be repo committer
    or author to see private issues.
    :param issue: issue object
    :param assignee: a boolean specifying whether to allow the assignee or not
        defaults to False
    :raises pagure.exceptions.APIError: when access denied
    """
    # Private tickets require commit access
    _check_private_issue_access(issue)

    error = False
    if not open_access:
        # Public tickets require ticket access
        error = not is_repo_user(issue.project)

    if assignee:
        if (
            issue.assignee is not None
            and issue.assignee.user == flask.g.fas_user.username
        ):
            error = False

    if error:
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EISSUENOTALLOWED
        )


def _check_private_issue_access(issue):
    """Check if user can access issue. Must be repo committer
    or author to see private issues.
    :param issue: issue object
    :raises pagure.exceptions.APIError: when access denied
    """
    if (
        issue.private
        and not is_repo_committer(issue.project)
        and (
            not api_authenticated()
            or not issue.user.user == flask.g.fas_user.username
        )
    ):
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EISSUENOTALLOWED
        )


def _check_pull_request_access(request, assignee=False, allow_author=False):
    """Check if user can access Pull-Request. Must be repo committer
    or author (if flag is true) to see private pull-requests.
    :param request: PullRequest object
    :param assignee: a boolean specifying whether to allow the assignee or not
        defaults to False
    :param allow_author: a boolean specifying whether the PR author should be
        allowed, defaults to False
    :raises pagure.exceptions.APIError: when access denied
    """
    # Private PRs require commit access
    _check_private_pull_request_access(request)

    error = False
    # Public tickets require ticket access
    error = not is_repo_user(request.project) and not (
        allow_author and request.user.user == flask.g.fas_user.username
    )

    if assignee:
        if (
            request.assignee is not None
            and request.assignee.user == flask.g.fas_user.username
        ):
            error = False

    if error:
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EPRNOTALLOWED
        )


def _check_private_pull_request_access(request):
    """Check if user can access PR. Must be repo committer
    or author to see private PR.
    :param request: PullRequest object
    :raises pagure.exceptions.APIError: when access denied
    """
    if (
        request.private
        and not is_repo_committer(request.project)
        and (
            not api_authenticated()
            or not request.user.user == flask.g.fas_user.username
        )
    ):
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EPRNOTALLOWED
        )


def _check_plugin(repo, plugin):
    """
    Check if plugin exists.

    :param repo: Repository object
    :param plugin: Plugin class
    :return plugin object
    """
    plugin = plugins.get_plugin(plugin)
    if not plugin:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPLUGIN)

    if repo.private and plugin.name == "Pagure CI":
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPLUGINDISABLED
        )

    if plugin.name in pagure.config.config.get("DISABLED_PLUGINS", []):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPLUGINDISABLED
        )

    if plugin.name == "default":
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EPLUGINCHANGENOTALLOWED
        )

    return plugin


def _get_project_tag(project_id, tag_name):
    """Check if tag exists and get tag obj
    : param project_id: id of the project
    : param tag_name: name of the tag
    : raises pagure.exceptions.APIError: when tag_name doesn't exist on
        project with id = project_id
    : return tag object
    """
    tag = pagure.lib.query.get_colored_tag(
        flask.g.session, tag_name, project_id
    )

    if tag is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOTAG)

    return tag
