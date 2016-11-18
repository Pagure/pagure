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
from pagure import APP, SESSION, is_repo_admin
from pagure.api import API, api_method, api_login_required, APIERROR


@API.route('/<repo>/pull-requests')
@API.route('/<namespace>/<repo>/pull-requests')
@API.route('/fork/<username>/<repo>/pull-requests')
@API.route('/fork/<username>/<namespace>/<repo>/pull-requests')
@api_method
def api_pull_request_views(repo, username=None, namespace=None):
    """
    List project's Pull-Requests
    ----------------------------
    Retrieve pull requests of a project.

    ::

        GET /api/0/<repo>/pull-requests
        GET /api/0/<namespace>/<repo>/pull-requests

    ::

        GET /api/0/fork/<username>/<repo>/pull-requests
        GET /api/0/fork/<username>/<namespace>/<repo>/pull-requests

    Parameters
    ^^^^^^^^^^

    +---------------+----------+--------------+----------------------------+
    | Key           | Type     | Optionality  | Description                |
    +===============+==========+==============+============================+
    | ``status``    | string   | Optional     | | Filter the status of     |
    |               |          |              |   pull requests. Default:  |
    |               |          |              |   ``True`` (opened pull    |
    |               |          |              |   requests), can be ``0``  |
    |               |          |              |   or ``closed`` for closed |
    |               |          |              |   requests or ``Merged``   |
    |               |          |              |   for merged requests.     |
    |               |          |              |   ``All`` returns closed,  |
    |               |          |              |   merged and open requests.|
    +---------------+----------+--------------+----------------------------+
    | ``assignee``  | string   | Optional     | | Filter the assignee of   |
    |               |          |              |   pull requests            |
    +---------------+----------+--------------+----------------------------+
    | ``author``    | string   | Optional     | | Filter the author of     |
    |               |          |              |   pull requests            |
    +---------------+----------+--------------+----------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "args": {
            "assignee": null,
            "author": null,
            "status": true
          },
          "total_requests": 1,
          "requests": [
            {
              "assignee": null,
              "branch": "master",
              "branch_from": "master",
              "closed_at": null,
              "closed_by": null,
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
                "user": {
                  "fullname": "PY C",
                  "name": "pingou"
                }
              },
              "status": "Open",
              "title": "test pull-request",
              "uid": "1431414800",
              "updated_on": "1431414800",
              "user": {
                "fullname": "PY C",
                "name": "pingou"
              }
            }
          ]
        }

    """

    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

    status = flask.request.args.get('status', True)
    assignee = flask.request.args.get('assignee', None)
    author = flask.request.args.get('author', None)

    requests = []
    if str(status).lower() in ['0', 'false', 'closed']:
        requests = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            status=False,
            assignee=assignee,
            author=author)

    elif str(status).lower() == 'all':
        requests = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            status=None,
            assignee=assignee,
            author=author)

    else:
        requests = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            assignee=assignee,
            author=author,
            status=status)

    jsonout = flask.jsonify({
        'total_requests': len(requests),
        'requests': [
            request.to_json(public=True, api=True)
            for request in requests],
        'args': {
            'status': status,
            'assignee': assignee,
            'author': author,
        }
    })
    return jsonout


@API.route('/<repo>/pull-request/<int:requestid>')
@API.route('/<namespace>/<repo>/pull-request/<int:requestid>')
@API.route('/fork/<username>/<repo>/pull-request/<int:requestid>')
@API.route('/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>')
@api_method
def api_pull_request_view(repo, requestid, username=None, namespace=None):
    """
    Pull-request information
    ------------------------
    Retrieve information of a specific pull request.

    ::

        GET /api/0/<repo>/pull-request/<request id>
        GET /api/0/<namespace>/<repo>/pull-request/<request id>

    ::

        GET /api/0/fork/<username>/<repo>/pull-request/<request id>
        GET /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "assignee": null,
          "branch": "master",
          "branch_from": "master",
          "closed_at": null,
          "closed_by": null,
          "comments": [],
          "commit_start": null,
          "commit_stop": null,
          "date_created": "1431414800",
          "id": 1,
          "project": {
            "close_status": [],
            "custom_keys": [],
            "date_created": "1431414800",
            "description": "test project #1",
            "id": 1,
            "name": "test",
            "parent": null,
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
            "user": {
              "fullname": "PY C",
              "name": "pingou"
            }
          },
          "status": "Open",
          "title": "test pull-request",
          "uid": "1431414800",
          "updated_on": "1431414800",
          "user": {
            "fullname": "PY C",
            "name": "pingou"
          }
        }

    """

    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    jsonout = flask.jsonify(request.to_json(public=True, api=True))
    return jsonout


@API.route('/<repo>/pull-request/<int:requestid>/merge', methods=['POST'])
@API.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/merge',
    methods=['POST'])
@API.route('/fork/<username>/<repo>/pull-request/<int:requestid>/merge',
           methods=['POST'])
@API.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/merge',
    methods=['POST'])
@api_login_required(acls=['pull_request_merge'])
@api_method
def api_pull_request_merge(repo, requestid, username=None, namespace=None):
    """
    Merge a pull-request
    --------------------
    Instruct Paugre to merge a pull request.

    ::

        POST /api/0/<repo>/pull-request/<request id>/merge
        POST /api/0/<namespace>/<repo>/pull-request/<request id>/merge

    ::

        POST /api/0/fork/<username>/<repo>/pull-request/<request id>/merge
        POST /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>/merge

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "Changes merged!"
        }

    """
    output = {}

    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

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
            raise pagure.exceptions.APIError(
                403, error_code=APIERROR.ENOTASSIGNED)

        if request.assignee.username != flask.g.fas_user.username:
            raise pagure.exceptions.APIError(
                403, error_code=APIERROR.ENOTASSIGNEE)

    threshold = repo.settings.get('Minimum_score_to_merge_pull-request', -1)
    if threshold > 0 and int(request.score) < int(threshold):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.EPRSCORE)

    try:
        message = pagure.lib.git.merge_pull_request(
            SESSION, request, flask.g.fas_user.username,
            APP.config['REQUESTS_FOLDER'])
        output['message'] = message
    except pagure.exceptions.PagureException as err:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(err))

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/pull-request/<int:requestid>/close', methods=['POST'])
@API.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/close',
    methods=['POST'])
@API.route('/fork/<username>/<repo>/pull-request/<int:requestid>/close',
           methods=['POST'])
@API.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/close',
    methods=['POST'])
@api_login_required(acls=['pull_request_close'])
@api_method
def api_pull_request_close(repo, requestid, username=None, namespace=None):
    """
    Close a pull-request
    --------------------
    Instruct Pagure to close a pull request.

    ::

        POST /api/0/<repo>/pull-request/<request id>/close
        POST /api/0/<namespace>/<repo>/pull-request/<request id>/close

    ::

        POST /api/0/fork/<username>/<repo>/pull-request/<request id>/close
        POST /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>/close

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "Pull-request closed!"
        }

    """
    output = {}

    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

    if repo != flask.g.token.project:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    if not is_repo_admin(repo):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.ENOPRCLOSE)

    try:
        pagure.lib.close_pull_request(
            SESSION, request, flask.g.fas_user.username,
            requestfolder=APP.config['REQUESTS_FOLDER'],
            merged=False)
        SESSION.commit()
        output['message'] = 'Pull-request closed!'
    except SQLAlchemyError as err:  # pragma: no cover
        SESSION.rollback()
        APP.logger.exception(err)
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/pull-request/<int:requestid>/comment',
           methods=['POST'])
@API.route('/<namespace>/<repo>/pull-request/<int:requestid>/comment',
           methods=['POST'])
@API.route('/fork/<username>/<repo>/pull-request/<int:requestid>/comment',
           methods=['POST'])
@API.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/comment',
    methods=['POST'])
@api_login_required(acls=['pull_request_comment'])
@api_method
def api_pull_request_add_comment(
        repo, requestid, username=None, namespace=None):
    """
    Comment on a pull-request
    -------------------------
    Add comment to a pull request.

    ::

        POST /api/0/<repo>/pull-request/<request id>/comment
        POST /api/0/<namespace>/<repo>/pull-request/<request id>/comment

    ::

        POST /api/0/fork/<username>/<repo>/pull-request/<request id>/comment
        POST /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>/comment

    Input
    ^^^^^

    +---------------+---------+--------------+-----------------------------+
    | Key           | Type    | Optionality  | Description                 |
    +===============+=========+==============+=============================+
    | ``comment``   | string  | Mandatory    | | The comment to add        |
    |               |         |              |   to the pull request       |
    +---------------+---------+--------------+-----------------------------+
    | ``commit``    | string  | Optional     | | The hash of the specific  |
    |               |         |              |   commit you wish to        |
    |               |         |              |   comment on                |
    +---------------+---------+--------------+-----------------------------+
    | ``filename``  | string  | Optional     | | The filename of the       |
    |               |         |              |   specific file you wish    |
    |               |         |              |   to comment on             |
    +---------------+---------+--------------+-----------------------------+
    | ``row``       | int     | Optional     | | Used in combination       |
    |               |         |              |   with filename to comment  |
    |               |         |              |   on a specific row         |
    |               |         |              |   of a file                 |
    +---------------+---------+--------------+-----------------------------+
    | ``tree_id``   | string  | Optional     | | The identifier of the     |
    |               |         |              |   git tree as it was when   |
    |               |         |              |   the comment was added     |
    +---------------+---------+--------------+-----------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "Comment added"
        }

    """
    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

    if repo.fullname != flask.g.token.project.fullname:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    form = pagure.forms.AddPullRequestCommentForm(csrf_enabled=False)
    if form.validate_on_submit():
        comment = form.comment.data
        commit = form.commit.data or None
        filename = form.filename.data or None
        tree_id = form.tree_id.data or None
        row = form.row.data or None
        try:
            # New comment
            message = pagure.lib.add_pull_request_comment(
                SESSION,
                request=request,
                commit=commit,
                tree_id=tree_id,
                filename=filename,
                row=row,
                comment=comment,
                user=flask.g.fas_user.username,
                requestfolder=APP.config['REQUESTS_FOLDER'],
            )
            SESSION.commit()
            output['message'] = message
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err))
        except SQLAlchemyError as err:  # pragma: no cover
            APP.logger.exception(err)
            SESSION.rollback()
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/pull-request/<int:requestid>/flag',
           methods=['POST'])
@API.route('/<namespace>/<repo>/pull-request/<int:requestid>/flag',
           methods=['POST'])
@API.route('/fork/<username>/<repo>/pull-request/<int:requestid>/flag',
           methods=['POST'])
@API.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/flag',
    methods=['POST'])
@api_login_required(acls=['pull_request_flag'])
@api_method
def api_pull_request_add_flag(repo, requestid, username=None, namespace=None):
    """
    Flag a pull-request
    -------------------
    Add or edit flags on a pull-request.

    ::

        POST /api/0/<repo>/pull-request/<request id>/flag
        POST /api/0/<namespace>/<repo>/pull-request/<request id>/flag

    ::

        POST /api/0/fork/<username>/<repo>/pull-request/<request id>/flag
        POST /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>/flag

    Input
    ^^^^^

    +---------------+---------+--------------+-----------------------------+
    | Key           | Type    | Optionality  | Description                 |
    +===============+=========+==============+=============================+
    | ``username``  | string  | Mandatory    | | The name of the           |
    |               |         |              |   application to be         |
    |               |         |              |   presented to users        |
    |               |         |              |   on the pull request page  |
    +---------------+---------+--------------+-----------------------------+
    | ``percent``   | int     | Mandatory    | | A percentage of           |
    |               |         |              |   completion compared to    |
    |               |         |              |   the goal. The percentage  |
    |               |         |              |   also determine the        |
    |               |         |              |   background color of the   |
    |               |         |              |   flag on the pull-request  |
    |               |         |              |   page                      |
    +---------------+---------+--------------+-----------------------------+
    | ``comment``   | string  | Mandatory    | | A short message           |
    |               |         |              |   summarizing the           |
    |               |         |              |   presented results         |
    +---------------+---------+--------------+-----------------------------+
    | ``url``       | string  | Mandatory    | | A URL to the result       |
    |               |         |              |   of this flag              |
    +---------------+---------+--------------+-----------------------------+
    | ``uid``       | string  | Optional     | | A unique identifier used  |
    |               |         |              |   to identify a flag on a   |
    |               |         |              |   pull-request. If the      |
    |               |         |              |   provided UID matches an   |
    |               |         |              |   existing one, then the    |
    |               |         |              |   API call will update the  |
    |               |         |              |   existing one rather than  |
    |               |         |              |   create a new one.         |
    |               |         |              |   Maximum Length: 32        |
    |               |         |              |   characters. Default: an   |
    |               |         |              |   auto generated UID        |
    +---------------+---------+--------------+-----------------------------+
    | ``commit``    | string  | Optional     | | The hash of the commit    |
    |               |         |              |   you use                   |
    +---------------+---------+--------------+-----------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "Flag added"
        }

    ::

        {
          "message": "Flag updated"
        }

    """
    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

    if repo.fullname != flask.g.token.project.fullname:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    form = pagure.forms.AddPullRequestFlagForm(csrf_enabled=False)
    if form.validate_on_submit():
        username = form.username.data
        percent = form.percent.data
        comment = form.comment.data.strip()
        url = form.url.data.strip()
        uid = form.uid.data.strip() if form.uid.data else None
        try:
            # New Flag
            message = pagure.lib.add_pull_request_flag(
                SESSION,
                request=request,
                username=username,
                percent=percent,
                comment=comment,
                url=url,
                uid=uid,
                user=flask.g.fas_user.username,
                requestfolder=APP.config['REQUESTS_FOLDER'],
            )
            SESSION.commit()
            output['message'] = message
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err))
        except SQLAlchemyError as err:  # pragma: no cover
            APP.logger.exception(err)
            SESSION.rollback()
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    jsonout = flask.jsonify(output)
    return jsonout
