# -*- coding: utf-8 -*-

"""
 (c) 2016-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import logging

import flask

from cryptography.hazmat.primitives import constant_time
from kitchen.text.converters import to_bytes

import pagure
import pagure.exceptions
import pagure.lib.query
import pagure.lib.plugins
import pagure.lib.lib_ci as lib_ci
from pagure.api import API, APIERROR, api_method


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
        lib_ci.process_jenkins_build(flask.g.session, project, build_id)
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
