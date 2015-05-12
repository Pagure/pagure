# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask

from sqlalchemy.exc import SQLAlchemyError

import pagure
import pagure.exceptions
import pagure.lib
from pagure import APP, SESSION, is_repo_admin, authenticated
from pagure.api import (
    API, api_method, api_login_required, api_login_optional, API_ERROR_CODE
)


@API.route('/<repo>/pull-request/<int:requestid>')
@API.route('/fork/<username>/<repo>/pull-request/<int:requestid>')
@api_method
def api_pull_request_view(repo, requestid, username=None):
    """ List all issues associated to a repo
    """

    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=1)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(404, error_code=8)

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=9)

    jsonout = flask.jsonify(request.to_json())
    jsonout.status_code = httpcode
    return jsonout


@API.route('/<repo>/pull-request/<int:requestid>/close', methods=['POST'])
@API.route('/fork/<username>/<repo>/pull-request/<int:requestid>/close',
           methods=['POST'])
@api_login_required(acls=['pull_request_close'])
@api_method
def api_pull_request_close(repo, issueid, username=None):
    """ Close a pull-request without merging it
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=1)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(404, error_code=8)

    if repo != flask.g.token.project:
        raise pagure.exceptions.APIError(401, error_code=5)

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=9)

    if not is_repo_admin(repo):
        raise pagure.exceptions.APIError(403, error_code=10)

    pagure.lib.close_pull_request(
        SESSION, request, flask.g.fas_user.username,
        requestfolder=APP.config['REQUESTS_FOLDER'],
        merged=False)
    try:
        SESSION.commit()
        output['message'] = 'Request pull canceled!'
    except SQLAlchemyError as err:  # pragma: no cover
        SESSION.rollback()
        APP.logger.exception(err)
        raise pagure.exceptions.APIError(400, error_code=3)

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/<repo>/pull-request/<int:requestid>/comment',
           methods=['POST'])
@API.route('/fork/<username>/<repo>/pull-request/<int:requestid>/comment',
           methods=['POST'])
@api_login_required(acls=['pull_request_comment'])
@api_method
def api_pull_request_add_comment(repo, requestid, username=None):
    """ Add a comment to an pull-request
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=1)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(404, error_code=8)

    if repo.fullname != flask.g.token.project.fullname:
        raise pagure.exceptions.APIError(401, error_code=5)

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=9)

    form = pagure.forms.AddPullRequestCommentForm(csrf_enabled=False)
    if form.validate_on_submit():
        comment = form.comment.data
        commit = form.commit.data
        filename = form.filename.data
        row = form.row.data
        try:
            # New comment
            message = pagure.lib.add_pull_request_comment(
                SESSION,
                request=request,
                commit=commit,
                filename=filename,
                row=row,
                comment=comment,
                user=flask.g.fas_user.username,
                requestfolder=APP.config['REQUESTS_FOLDER'],
            )
            SESSION.commit()
            output['message'] = message
        except SQLAlchemyError, err:  # pragma: no cover
            raise pagure.exceptions.APIError(400, error_code=3)

    else:
        raise pagure.exceptions.APIError(400, error_code=4)

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout
