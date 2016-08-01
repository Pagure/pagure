# -*- coding: utf-8 -*-
import json
import logging

import requests

from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import create_engine

import pagure.exceptions
import pagure.lib
from pagure.lib import model
from pagure.hooks import pagure_ci


BUILD_STATS = {
    'SUCCESS': ('Build successful', 100),
    'FAILURE': ('Build failed', 0),
}


def get_project_by_ci_token(session, ci_token):
    """ Return the project corresponding to the provided ci_token. """
    query = session.query(
        model.Project
    ).filter(
        model.Project.id == pagure_ci.PagureCITable.project_id
    ).filter(
        pagure_ci.PagureCITable.pagure_ci_token == ci_token
    )

    return query.first()


def process_jenkins_build(project, build_id):
    """  Gets the build info from jenkins and flags that particular
    pull-request.
    """
    import jenkins
    jenk = jenkins.Jenkins(project.ci_hook.url)
    jenkins_name = project.ci_hook.url.split('/job/', 1)[1].split('/', 1)[0]
    build_info = jenk.get_build_info(jenkins_name, build_id)
    result = build_info['result']
    url = build_info['url']

    pr_id = None
    for action in build_info['actions']:
        for cause in action.get('causes', []):
            try:
                pr_id = int(cause['note'])
            except (KeyError, ValueError):
                continue

    if not pr_id:
        raise pagure.exceptions.PagureException(
            'No PR found corresponding')

    if result not in BUILD_STATS:
        pagure.exceptions.PagureException(
            'Unknown build status: %s' % result)

    request = pagure.lib.search_pull_requests(
        session, project_id=project.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.PagureException('Request not found')

    comment, percent = BUILD_STATS[result]

    message = pagure.lib.add_pull_request_flag(
        session,
        request=request,
        username=username,
        percent=percent,
        comment=comment,
        url=url,
        uid=None,
        user=repo.user.username,
        requestfolder=APP.config['REQUESTS_FOLDER'],
    )
    SESSION.commit()
