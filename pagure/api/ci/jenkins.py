# -*- coding: utf-8 -*-

"""
 (c) 2016-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import absolute_import, unicode_literals

import logging

import flask
from cryptography.hazmat.primitives import constant_time
from kitchen.text.converters import to_bytes

import pagure
import pagure.exceptions
import pagure.lib.query
from pagure.config import config as pagure_config
import pagure.lib.plugins
import pagure.lib.query
from pagure.api import API, APIERROR, api_method
from pagure.api.ci import BUILD_STATS

import time

_log = logging.getLogger(__name__)


@API.route(
    "/ci/jenkins/<repo>/<pagure_ci_token>/build-finished", methods=["POST"]
)
@API.route(
    "/ci/jenkins/<namespace>/<repo>/<pagure_ci_token>/build-finished",
    methods=["POST"],
)
@API.route(
    "/ci/jenkins/forks/<username>/<repo>/" "<pagure_ci_token>/build-finished",
    methods=["POST"],
)
@API.route(
    "/ci/jenkins/forks/<username>/<namespace>/<repo>/"
    "<pagure_ci_token>/build-finished",
    methods=["POST"],
)
@api_method
# <ci_type>_ci_notification
# convention required to ensure unique names in API namespace
def jenkins_ci_notification(
    repo, pagure_ci_token, username=None, namespace=None
):
    """
    Jenkins Build Notification
    --------------------------
    At the end of a build on Jenkins, this URL is used (if the project is
    rightly configured) to flag a pull-request with the result of the build.

    ::

        POST /api/0/ci/jenkins/<repo>/<token>/build-finished

    """

    project = pagure.lib.query._get_project(
        flask.g.session, repo, user=username, namespace=namespace
    )
    flask.g.repo_locked = True
    flask.g.repo = project
    if not project:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    ci_hook = pagure.lib.plugins.get_plugin("Pagure CI")
    ci_hook.db_object()

    if not constant_time.bytes_eq(
        to_bytes(pagure_ci_token), to_bytes(project.ci_hook.pagure_ci_token)
    ):
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    data = flask.request.get_json()
    if not data:
        _log.debug("Bad Request: No JSON retrieved")
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    build_id = data.get("build", {}).get("number")
    if not build_id:
        _log.debug("Bad Request: No build ID retrieved")
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    build_phase = data.get("build", {}).get("phase")
    if not build_phase:
        _log.debug("Bad Request: No build phase retrieved")
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)
    if build_phase not in ["STARTED", "FINALIZED"]:
        _log.debug(
            "Ignoring phase: %s - not in the list: STARTED, FINALIZED",
            build_phase,
        )
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    try:
        _process_build(flask.g.session, project, build_id)
    except pagure.exceptions.NoCorrespondingPR as err:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(err)
        )
    except pagure.exceptions.PagureException as err:
        _log.error("Error processing jenkins notification", exc_info=err)
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(err)
        )

    _log.info("Successfully proccessed jenkins notification")
    return ("", 204)


def _process_build(session, project, build_id, iteration=0):
    """Gets the build info from jenkins and flags that particular
    pull-request.
    """
    import jenkins

    # This import is needed as pagure.lib relies on Project.ci_hook to be
    # defined and accessible and this happens in pagure.hooks.pagure_ci
    from pagure.hooks import pagure_ci  # noqa: E402,F401

    # Jenkins Base URL
    _log.info("Querying jenkins at: %s", project.ci_hook.ci_url)
    jenk = jenkins.Jenkins(
        project.ci_hook.ci_url,
        username=project.ci_hook.ci_username or None,
        password=project.ci_hook.ci_password or None,
    )
    jenkins_name = project.ci_hook.ci_job
    _log.info(
        "Querying jenkins for project: %s, build: %s", jenkins_name, build_id
    )
    try:
        build_info = jenk.get_build_info(jenkins_name, build_id)
    except jenkins.NotFoundException:
        _log.debug("Could not find build %s at: %s", build_id, jenkins_name)
        raise pagure.exceptions.PagureException(
            "Could not find build %s at: %s" % (build_id, jenkins_name)
        )

    if build_info.get("building") is True:
        if iteration < 5:
            _log.info("Build is still going, let's wait a sec and try again")
            time.sleep(1)
            return _process_build(
                session, project, build_id, iteration=iteration + 1
            )
        _log.info(
            "We've been waiting for 5 seconds and the build is still "
            "not finished, so let's keep going."
        )

    result = build_info.get("result")
    if not result and build_info.get("building") is True:
        result = "BUILDING"

    _log.info("Result from jenkins: %s", result)
    url = build_info["url"]
    _log.info("URL from jenkins: %s", url)

    pr_id = None
    for action in build_info["actions"]:
        for cause in action.get("causes", []):
            try:
                pr_id = int(cause["note"])
            except (KeyError, ValueError):
                continue

    if not pr_id:
        raise pagure.exceptions.NoCorrespondingPR("No corresponding PR found")

    if not result or result not in BUILD_STATS:
        raise pagure.exceptions.PagureException(
            "Unknown build status: %s" % result
        )

    request = pagure.lib.query.search_pull_requests(
        session, project_id=project.id, requestid=pr_id
    )

    if not request:
        raise pagure.exceptions.PagureException("Request not found")

    comment, state, percent = BUILD_STATS[result]
    comment = comment % build_id
    # Adding build ID to the CI type
    username = "%s" % project.ci_hook.ci_type
    if request.commit_stop:
        comment += " (commit: %s)" % (request.commit_stop[:8])

    uid = None
    for flag in request.flags:
        if (
            flag.status == pagure_config["FLAG_PENDING"]
            and flag.username == username
        ):
            uid = flag.uid
            break

    _log.info("Flag's UID: %s", uid)
    pagure.lib.query.add_pull_request_flag(
        session,
        request=request,
        username=username,
        percent=percent,
        comment=comment,
        url=url,
        status=state,
        uid=uid,
        user=project.user.username,
        token=None,
    )
    session.commit()


def trigger_build(
    project_path,
    url,
    job,
    token,
    branch,
    branch_to,
    cause,
    ci_username=None,
    ci_password=None,
):
    """Trigger a build on a jenkins instance."""
    try:
        import jenkins
    except ImportError:
        _log.error("Pagure-CI: Failed to load the jenkins module, bailing")
        return

    _log.info("Jenkins CI")

    repo = "%s/%s" % (pagure_config["GIT_URL_GIT"].rstrip("/"), project_path)

    data = {
        "cause": cause,
        "REPO": repo,
        "BRANCH": branch,
        "BRANCH_TO": branch_to,
    }

    server = jenkins.Jenkins(
        url, username=ci_username or None, password=ci_password or None
    )
    _log.info(
        "Pagure-CI: Triggering at: %s for: %s - data: %s", url, job, data
    )
    try:
        server.build_job(name=job, parameters=data, token=token)
        _log.info("Pagure-CI: Build triggered")
    except Exception as err:
        _log.info("Pagure-CI:An error occured: %s", err)
