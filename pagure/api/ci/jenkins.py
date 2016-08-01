# -*- coding: utf-8 -*-

"""
 (c) 2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask

from sqlalchemy.exc import SQLAlchemyError

import pagure
import pagure.exceptions
import pagure.lib
from pagure import APP, SESSION
from pagure.api import API, APIERROR


@API.route('/ci/jenkins/<pagure_ci_token>/build-finished', methods=['POST'])
def ci_notification(pagure_ci_token):
    """ Flag a pull-request based on the info provided by the CI service.
    """

    try:
        data = flask.request.json()
        cfg = jenkins_hook.get_configs(
            data['name'], jenkins_hook.Service.JENKINS)[0]
        build_id = data['build']['number']

        if not constant_time.bytes_eq(
                  to_bytes(pagure_ci_token), to_bytes(cfg.pagure_ci_token)):
            return ('Token mismatch', 401)

    except (TypeError, ValueError, KeyError, jenkins_hook.ConfigNotFound) as exc:
        APP.logger.error('Error processing jenkins notification', exc_info=exc)
        flask.abort(400, "Bad Request")

    APP.logger.info('Received jenkins notification')
    pagure_ci.process_build(APP.logger, cfg, build_id)
    return ('', 204)
