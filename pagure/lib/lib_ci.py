# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Lubomír Sedlář <lubomir.sedlar@gmail.com>
   Farhaan Bukhsh <farhaan.bukhsh@gmail.com>
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals

# pylint: disable=too-many-locals
import logging
import time
import pagure.exceptions
import pagure.lib

# This import is needed as pagure.lib relies on Project.ci_hook to be
# defined and accessible and this happens in pagure.hooks.pagure_ci
from pagure.hooks import pagure_ci  # noqa: E402,F401
from pagure.config import config as pagure_config

_log = logging.getLogger(__name__)

BUILD_STATS = {
    "SUCCESS": ("Build successful", pagure_config["FLAG_SUCCESS"], 100),
    "FAILURE": ("Build failed", pagure_config["FLAG_FAILURE"], 0),
    "ABORTED": ("Build aborted", "error", 0),
    "BUILDING": ("Build in progress", pagure_config["FLAG_PENDING"], 0),
}


def process_jenkins_build(
    session, project, build_id, requestfolder, iteration=0
):
    """  Gets the build info from jenkins and flags that particular
    pull-request.
    """
    import jenkins

    # Jenkins Base URL
    _log.info("Querying jenkins at: %s", project.ci_hook.ci_url)
    jenk = jenkins.Jenkins(project.ci_hook.ci_url)
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
            return process_jenkins_build(
                session,
                project,
                build_id,
                requestfolder,
                iteration=iteration + 1,
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

    request = pagure.lib.search_pull_requests(
        session, project_id=project.id, requestid=pr_id
    )

    if not request:
        raise pagure.exceptions.PagureException("Request not found")

    comment, state, percent = BUILD_STATS[result]
    # Adding build ID to the CI type
    username = "%s #%s" % (project.ci_hook.ci_type, build_id)
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
    pagure.lib.add_pull_request_flag(
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
        requestfolder=requestfolder,
    )
    session.commit()


def trigger_jenkins_build(project_path, url, job, token, branch, cause):
    """ Trigger a build on a jenkins instance."""
    try:
        import jenkins
    except ImportError:
        _log.error("Pagure-CI: Failed to load the jenkins module, bailing")
        return

    _log.info("Jenkins CI")

    repo = "%s/%s" % (pagure_config["GIT_URL_GIT"].rstrip("/"), project_path)

    data = {"cause": cause, "REPO": repo, "BRANCH": branch}

    server = jenkins.Jenkins(url)
    _log.info(
        "Pagure-CI: Triggering at: %s for: %s - data: %s", url, job, data
    )
    try:
        server.build_job(name=job, parameters=data, token=token)
        _log.info("Pagure-CI: Build triggered")
    except Exception as err:
        _log.info("Pagure-CI:An error occured: %s", err)
