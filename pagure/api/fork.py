# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import logging
import os

import flask
import pygit2
from sqlalchemy.exc import SQLAlchemyError

import pagure
import pagure.exceptions
import pagure.lib
import pagure.lib.tasks
from pagure.api import (API, api_method, api_login_required, APIERROR,
                        get_authorized_api_project)
from pagure.config import config as pagure_config
from pagure.utils import is_repo_committer, api_authenticated


_log = logging.getLogger(__name__)


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

    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)

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
            flask.g.session,
            project_id=repo.id,
            status=False,
            assignee=assignee,
            author=author)

    elif str(status).lower() == 'all':
        requests = pagure.lib.search_pull_requests(
            flask.g.session,
            project_id=repo.id,
            status=None,
            assignee=assignee,
            author=author)

    else:
        requests = pagure.lib.search_pull_requests(
            flask.g.session,
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

    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

    request = pagure.lib.search_pull_requests(
        flask.g.session, project_id=repo.id, requestid=requestid)

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

    This is an asynchronous call.

    ::

        POST /api/0/<repo>/pull-request/<request id>/merge
        POST /api/0/<namespace>/<repo>/pull-request/<request id>/merge

    ::

        POST /api/0/fork/<username>/<repo>/pull-request/<request id>/merge
        POST /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>/merge

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        wait=False:
        {
          "message": "Merging queued",
          "taskid": "123-abcd"
        }

        wait=True:
        {
          "message": "Changes merged!"
        }

    """  # noqa
    output = {}

    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

    if flask.g.token.project and repo != flask.g.token.project:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    request = pagure.lib.search_pull_requests(
        flask.g.session, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    if not is_repo_committer(repo):
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
        taskid = pagure.lib.tasks.merge_pull_request.delay(
            repo.name, namespace, username, requestid,
            flask.g.fas_user.username).id
        output = {'message': 'Merging queued',
                  'taskid': taskid}

        if flask.request.form.get('wait', True):
            pagure.lib.tasks.get_result(taskid).get()
            output = {'message': 'Changes merged!'}
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

    """  # noqa
    output = {}

    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

    if repo != flask.g.token.project:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    request = pagure.lib.search_pull_requests(
        flask.g.session, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    if not is_repo_committer(repo):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.ENOPRCLOSE)

    try:
        pagure.lib.close_pull_request(
            flask.g.session, request, flask.g.fas_user.username,
            requestfolder=pagure_config['REQUESTS_FOLDER'],
            merged=False)
        flask.g.session.commit()
        output['message'] = 'Pull-request closed!'
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        _log.exception(err)
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

    """  # noqa
    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)

    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

    if flask.g.token.project and repo != flask.g.token.project:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    request = pagure.lib.search_pull_requests(
        flask.g.session, project_id=repo.id, requestid=requestid)

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
                flask.g.session,
                request=request,
                commit=commit,
                tree_id=tree_id,
                filename=filename,
                row=row,
                comment=comment,
                user=flask.g.fas_user.username,
                requestfolder=pagure_config['REQUESTS_FOLDER'],
            )
            flask.g.session.commit()
            output['message'] = message
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err))
        except SQLAlchemyError as err:  # pragma: no cover
            _log.exception(err)
            flask.g.session.rollback()
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors)

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
    | ``comment``   | string  | Mandatory    | | A short message           |
    |               |         |              |   summarizing the           |
    |               |         |              |   presented results         |
    +---------------+---------+--------------+-----------------------------+
    | ``url``       | string  | Mandatory    | | A URL to the result       |
    |               |         |              |   of this flag              |
    +---------------+---------+--------------+-----------------------------+
    | ``status``    | string  | Optional     | | The status of the task,   |
    |               |         |              |   can be any of:            |
    |               |         |              |   $$FLAG_STATUSES_COMMAS$$  |
    |               |         |              |   If not provided it will   |
    |               |         |              |   be set to                 |
    |               |         |              |   ``$$FLAG_SUCCESS$$`` if   |
    |               |         |              |   percent is higher than 0  |
    |               |         |              |   ``$$FLAG_FAILURE$$`` if   |
    |               |         |              |   it is 0 and               |
    |               |         |              |   ``$$FLAG_PENDING$$``      |
    |               |         |              |   if percent is not         |
    |               |         |              |   specified                 |
    +---------------+---------+--------------+-----------------------------+
    | ``percent``   | int     | Optional     | | A percentage of           |
    |               |         |              |   completion compared to    |
    |               |         |              |   the goal. The percentage  |
    |               |         |              |   also determine the        |
    |               |         |              |   background color of the   |
    |               |         |              |   flag on the pull-request  |
    |               |         |              |   page                      |
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

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "flag": {
            "comment": "Tests failed",
            "date_created": "1510742565",
            "percent": 0,
            "pull_request_uid": "62b49f00d489452994de5010565fab81",
            "status": "error",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "user": {
              "default_email": "bar@pingou.com",
              "emails": ["bar@pingou.com", "foo@pingou.com"],
              "fullname": "PY C",
              "name": "pingou"},
            "username": "Jenkins"},
          "message": u"Flag added",
          "uid": u"jenkins_build_pagure_100+seed"
        }

    ::

        {
          "flag": {
            "comment": "Tests failed",
            "date_created": "1510742565",
            "percent": 0,
            "pull_request_uid": "62b49f00d489452994de5010565fab81",
            "status": "error",
            "url": "http://jenkins.cloud.fedoraproject.org/",
            "user": {
              "default_email": "bar@pingou.com",
              "emails": ["bar@pingou.com", "foo@pingou.com"],
              "fullname": "PY C",
              "name": "pingou"},
            "username": "Jenkins"},
          "message": u"Flag updated",
          "uid": u"jenkins_build_pagure_100+seed"
        }

    """  # noqa
    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)

    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

    if flask.g.token.project and repo != flask.g.token.project:
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.EINVALIDTOK)

    request = pagure.lib.search_pull_requests(
        flask.g.session, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    if 'status' in flask.request.form:
        form = pagure.forms.AddPullRequestFlagForm(csrf_enabled=False)
    else:
        form = pagure.forms.AddPullRequestFlagFormV1(csrf_enabled=False)
    if form.validate_on_submit():
        username = form.username.data
        percent = form.percent.data.strip() or None
        comment = form.comment.data.strip()
        url = form.url.data.strip()
        uid = form.uid.data.strip() if form.uid.data else None
        if 'status' in flask.request.form:
            status = form.status.data.strip()
        else:
            if percent is None:
                status = pagure_config['FLAG_PENDING']
            else:
                status = pagure_config['FLAG_SUCCESS'] if percent != '0' else \
                    pagure_config['FLAG_FAILURE']
        try:
            # New Flag
            message, uid = pagure.lib.add_pull_request_flag(
                flask.g.session,
                request=request,
                username=username,
                status=status,
                percent=percent,
                comment=comment,
                url=url,
                uid=uid,
                user=flask.g.fas_user.username,
                token=flask.g.token.id,
                requestfolder=pagure_config['REQUESTS_FOLDER'],
            )
            flask.g.session.commit()
            pr_flag = pagure.lib.get_pull_request_flag_by_uid(
                flask.g.session, request, uid)
            output['message'] = message
            output['uid'] = uid
            output['flag'] = pr_flag.to_json()
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err))
        except SQLAlchemyError as err:  # pragma: no cover
            _log.exception(err)
            flask.g.session.rollback()
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route(
    '/<repo>/pull-request/<int:requestid>/subscribe',
    methods=['POST'])
@API.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/subscribe',
    methods=['POST'])
@API.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/subscribe',
    methods=['POST'])
@API.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>'
    '/subscribe', methods=['POST'])
@api_login_required(acls=['pull_request_subscribe'])
@api_method
def api_subscribe_pull_request(
        repo, requestid, username=None, namespace=None):
    """
    Subscribe to an pull-request
    ----------------------------
    Allows someone to subscribe to or unsubscribe from the notifications
    related to a pull-request.

    ::

        POST /api/0/<repo>/pull-request/<request id>/subscribe
        POST /api/0/<namespace>/<repo>/pull-request/<request id>/subscribe

    ::

        POST /api/0/fork/<username>/<repo>/pull-request/<request id>/subscribe
        POST /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>/subscribe

    Input
    ^^^^^

    +--------------+----------+---------------+---------------------------+
    | Key          | Type     | Optionality   | Description               |
    +==============+==========+===============+===========================+
    | ``status``   | boolean  | Mandatory     | The intended subscription |
    |              |          |               | status. ``true`` for      |
    |              |          |               | subscribing, ``false``    |
    |              |          |               | for unsubscribing.        |
    +--------------+----------+---------------+---------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "User subscribed"
        }

    """  # noqa

    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)

    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

    if api_authenticated():
        if flask.g.token.project and repo != flask.g.token.project:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK)

    request = pagure.lib.search_pull_requests(
        flask.g.session, project_id=repo.id, requestid=requestid)

    if not request:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    form = pagure.forms.SubscribtionForm(csrf_enabled=False)
    if form.validate_on_submit():
        status = str(form.status.data).strip().lower() in ['1', 'true']
        try:
            # Toggle subscribtion
            message = pagure.lib.set_watch_obj(
                flask.g.session,
                user=flask.g.fas_user.username,
                obj=request,
                watch_status=status
            )
            flask.g.session.commit()
            output['message'] = message
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.logger.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/pull-request/new', methods=['POST'])
@API.route('/<namespace>/<repo>/pull-request/new', methods=['POST'])
@API.route('/fork/<username>/<repo>/pull-request/new', methods=['POST'])
@API.route('/fork/<username>/<namespace>/<repo>/pull-request/new',
           methods=['POST'])
@api_login_required(acls=['pull_request_create'])
@api_method
def api_pull_request_create(repo, username=None, namespace=None):
    """
    Create pull-request
    -------------------
    Open a new pull-request from this project to itself or its parent (if
    this project is a fork).

    ::

        POST /api/0/<repo>/pull-request/new
        POST /api/0/<namespace>/<repo>/pull-request/new

    ::

        POST /api/0/fork/<username>/<repo>/pull-request/new
        POST /api/0/fork/<username>/<namespace>/<repo>/pull-request/new

    Input
    ^^^^^

    +--------------------+----------+---------------+----------------------+
    | Key                | Type     | Optionality   | Description          |
    +====================+==========+===============+======================+
    | ``title``          | string   | Mandatory     | The title to give to |
    |                    |          |               | this pull-request    |
    +--------------------+----------+---------------+----------------------+
    | ``branch_to``      | string   | Mandatory     | The name of the      |
    |                    |          |               | branch the submitted |
    |                    |          |               | changes should be    |
    |                    |          |               | merged into.         |
    +--------------------+----------+---------------+----------------------+
    | ``branch_from``    | string   | Mandatory     | The name of the      |
    |                    |          |               | branch containing    |
    |                    |          |               | the changes to merge |
    +--------------------+----------+---------------+----------------------+
    | ``initial_comment``| string   | Optional      | The intial comment   |
    |                    |          |               | describing what these|
    |                    |          |               | changes are about.   |
    +--------------------+----------+---------------+----------------------+

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

    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    form = pagure.forms.RequestPullForm(csrf_enabled=False)
    if not form.validate_on_submit():
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors)
    branch_to = flask.request.form.get('branch_to')
    if not branch_to:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ,
            errors={u'branch_to': [u'This field is required.']})
    branch_from = flask.request.form.get('branch_from')
    if not branch_from:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ,
            errors={u'branch_from': [u'This field is required.']})

    parent = repo
    if repo.parent:
        parent = repo.parent

    if not parent.settings.get('pull_requests', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED)

    repo_committer = pagure.utils.is_repo_committer(repo)

    if not repo_committer:
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.ENOTHIGHENOUGH)

    repo_obj = pygit2.Repository(
        os.path.join(pagure_config['GIT_FOLDER'], repo.path))
    orig_repo = pygit2.Repository(
        os.path.join(pagure_config['GIT_FOLDER'], parent.path))

    try:
        diff, diff_commits, orig_commit = pagure.lib.git.get_diff_info(
            repo_obj, orig_repo, branch_from, branch_to)
    except pagure.exceptions.PagureException as err:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=str(err))

    if parent.settings.get(
            'Enforce_signed-off_commits_in_pull-request', False):
        for commit in diff_commits:
            if 'signed-off-by' not in commit.message.lower():
                raise pagure.exceptions.APIError(
                    400, error_code=APIERROR.ENOSIGNEDOFF)

    if orig_commit:
        orig_commit = orig_commit.oid.hex

    initial_comment = form.initial_comment.data.strip() or None

    commit_start = commit_stop = None
    if diff_commits:
        commit_stop = diff_commits[0].oid.hex
        commit_start = diff_commits[-1].oid.hex

    request = pagure.lib.new_pull_request(
        flask.g.session,
        repo_to=parent,
        branch_to=branch_to,
        branch_from=branch_from,
        repo_from=repo,
        title=form.title.data,
        initial_comment=initial_comment,
        user=flask.g.fas_user.username,
        requestfolder=pagure_config['REQUESTS_FOLDER'],
        commit_start=commit_start,
        commit_stop=commit_stop,
    )

    try:
        flask.g.session.commit()
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        _log.logger.exception(err)
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    jsonout = flask.jsonify(request.to_json(public=True, api=True))
    return jsonout
