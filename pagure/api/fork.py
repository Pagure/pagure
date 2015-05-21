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
    API, api_method, api_login_required, api_login_optional, APIERROR
)


@API.route('/<repo>/pull-request/<int:requestid>')
@API.route('/fork/<username>/<repo>/pull-request/<int:requestid>')
@api_method
def api_pull_request_view(repo, requestid, username=None):
    """
    Request a pull-request
    --------------------
    This endpoint can be used to retrieve information about a specific
    pull-request

    ::

        /api/0/<repo>/pull-request/<request id>

        /api/0/fork/<username>/<repo>/pull-request/<request id>

    Accepts GET queries only.

    Sample response:

    ::

        {
          "assignee": null,
          "branch": "master",
          "branch_from": "master",
          "comments": [],
          "commit_start": null,
          "commit_stop": null,
          "date_created": "1431414800",
          "id": 1,
          "project": {
            "date_created": "1431414800",
            "description": "test project #1",
            "id": 1,
            "name": "test",
            "parent": null,
            "settings": {
              "Minimum_score_to_merge_pull-request": -1,
              "Only_assignee_can_merge_pull-request": false,
              "Web-hooks": null,
              "issue_tracker": true,
              "project_documentation": true,
              "pull_requests": true
            },
            "user": {
              "fullname": "PY C",
              "name": "pingou"
            }
          },
          "repo_from": {
            "date_created": "1431414800",
            "description": "test project #1",
            "id": 1,
            "name": "test",
            "parent": null,
            "settings": {
              "Minimum_score_to_merge_pull-request": -1,
              "Only_assignee_can_merge_pull-request": false,
              "Web-hooks": null,
              "issue_tracker": true,
              "project_documentation": true,
              "pull_requests": true
            },
            "user": {
              "fullname": "PY C",
              "name": "pingou"
            }
          },
          "status": true,
          "title": "test pull-request",
          "uid": "1431414800",
          "user": {
            "fullname": "PY C",
            "name": "pingou"
          }
        }

    """

    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPR)

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    jsonout = flask.jsonify(request.to_json(public=True))
    jsonout.status_code = httpcode
    return jsonout


@API.route('/<repo>/pull-request/<int:requestid>/merge', methods=['POST'])
@API.route('/fork/<username>/<repo>/pull-request/<int:requestid>/merge',
           methods=['POST'])
@api_login_required(acls=['pull_request_merge'])
@api_method
def api_pull_request_merge(repo, requestid, username=None):
    """
    Merge a pull-request
    --------------------
    This endpoint can be used to instruct pagure to merge a pull-request

    ::

        /api/0/<repo>/pull-request/<request id>/merge

        /api/0/fork/<username>/<repo>/pull-request/<request id>/merge

    Accepts POST queries only.

    Sample response:

    ::

        {
          "message": "Changes merged!"
        }

    """
    httpcode = 200
    output = {}

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPR)

    if repo != flask.g.token.project:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    if not is_repo_admin(repo):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.ENOPRCLOSE)

    if repo.settings.get('Only_assignee_can_merge_pull-request', False):
        if not request.assignee:
            raise pagure.exceptions.APIError(403, error_code=APIERROR.ENOTASSIG)

        if request.assignee.username != flask.g.fas_user.username:
            raise pagure.exceptions.APIError(403, error_code=APIERROR.ENOASSIG)

    threshold = repo.settings.get('Minimum_score_to_merge_pull-request', -1)
    if threshold > 0 and int(request.score) < int(threshold):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.EPRSCORE)

    try:
        message = pagure.lib.git.merge_pull_request(
            SESSION, repo, request, flask.g.fas_user.username,
            APP.config['REQUESTS_FOLDER'])
        output['message'] = message
    except pagure.exceptions.PagureException as err:
        raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err))

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/<repo>/pull-request/<int:requestid>/close', methods=['POST'])
@API.route('/fork/<username>/<repo>/pull-request/<int:requestid>/close',
           methods=['POST'])
@api_login_required(acls=['pull_request_close'])
@api_method
def api_pull_request_close(repo, requestid, username=None):
    """
    Close a pull-request
    --------------------
    This endpoint can be used to instruct pagure to close a pull-request
    without merging it

    ::

        /api/0/<repo>/pull-request/<request id>/close

        /api/0/fork/<username>/<repo>/pull-request/<request id>/close

    Accepts POST queries only.

    Sample response:

    ::

        {
          "message": "Request pull canceled!"
        }

    """
    httpcode = 200
    output = {}

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPR)

    if repo != flask.g.token.project:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    if not is_repo_admin(repo):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.ENOPRCLOSE)

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
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

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
    """
    Comment on a pull-request
    --------------------
    This endpoint can be used to comment on a pull-request

    ::

        /api/0/<repo>/pull-request/<request id>/comment

        /api/0/fork/<username>/<repo>/pull-request/<request id>/comment

    Accepts POST queries only.

    :arg comment: The comment to add to the pull-request
    :kwarg commit: The hash of the commit you wish to comment on
    :kwarg filename: The name of the file you wish to comment on
    :kwarg row: Used in combination with filename to comment on a specific
        row of a file of the pull-request

    Sample response:

    ::

        {
          "message": "Comment added"
        }

    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPR)

    if repo.fullname != flask.g.token.project.fullname:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

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
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout
