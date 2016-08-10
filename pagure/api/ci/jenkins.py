# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask

from cryptography.hazmat.primitives import constant_time
from kitchen.text.converters import to_bytes
from sqlalchemy.exc import SQLAlchemyError

import pagure
import pagure.exceptions
import pagure.lib
import pagure.lib.lib_ci as lib_ci
from pagure import APP, SESSION
from pagure.api import API, APIERROR



@API.route('/ci/jenkins/<repo:repo>/<pagure_ci_token>/build-finished', methods=['POST'])
@API.route('/ci/jenkins/forks/<username>/<repo:repo>/<pagure_ci_token>/build-finished', methods=['POST'])
def jenkins_ci_notification(repo, pagure_ci_token, username=None):
    """
    Jenkins Build Notification
    --------------------------
    At the end of a build on Jenkins, this URL is used (if the project is
    rightly configured) to flag a pull-request with the result of the build.

    ::

        POST /api/0/ci/jenkins/<token>/build-finished

    """

    project = pagure.lib.get_project(SESSION, repo, user=username)
    if repo is None:
        flask.abort(404, 'Project not found')

    if not constant_time.bytes_eq(
          to_bytes(pagure_ci_token),
          to_bytes(project.ci_hook[0].pagure_ci_token)):
        return ('Token mismatch', 401)

    data = flask.request.get_json()
    if not data:
        flask.abort(400, "Bad Request: No JSON retrived")

    build_id = data.get('build', {}).get('number')
    if not build_id:
        flask.abort(400, "Bad Request: No build ID retrived")

    try:
        lib_ci.process_jenkins_build(
            SESSION,
            project,
            build_id,
            requestfolder=APP.config['REQUESTS_FOLDER']
        )
    except pagure.exceptions.PagureException as err:
        APP.logger.error('Error processing jenkins notification', exc_info=err)
        flask.abort(400, "Bad Request: %s" % err)

    APP.logger.info('Successfully proccessed jenkins notification')
    return ('', 204)
