# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import absolute_import, unicode_literals

import logging

import flask
import pygit2
from sqlalchemy.exc import SQLAlchemyError

import pagure
import pagure.exceptions
import pagure.lib.query
import pagure.lib.tasks
from pagure.api import (
    API,
    APIERROR,
    api_login_required,
    api_method,
    get_authorized_api_project,
    get_page,
    get_per_page,
    get_request_data,
)
from pagure.api.utils import (
    _check_private_pull_request_access,
    _check_pull_request,
    _check_pull_request_access,
    _check_token,
    _get_repo,
    _get_request,
)
from pagure.config import config as pagure_config
from pagure.utils import is_repo_committer, is_true

_log = logging.getLogger(__name__)


@API.route("/<repo>/pull-requests")
@API.route("/<namespace>/<repo>/pull-requests")
@API.route("/fork/<username>/<repo>/pull-requests")
@API.route("/fork/<username>/<namespace>/<repo>/pull-requests")
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
    | ``tags``      | string   | Optional     | | A list of tags you       |
    |               |          |              |   wish to filter. If you   |
    |               |          |              |   want to filter for pull  |
    |               |          |              |   requests not having a    |
    |               |          |              |   tag, add an exclamation  |
    |               |          |              |   mark in front of it      |
    +---------------+----------+--------------+----------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "args": {
            "assignee": null,
            "author": null,
            "status": true,
            "tags": null
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

    repo = _get_repo(repo, username, namespace)
    _check_pull_request(repo)

    status = flask.request.args.get("status", True)
    assignee = flask.request.args.get("assignee", None)
    author = flask.request.args.get("author", None)
    tags = flask.request.args.getlist("tags")
    tags = [tag.strip() for tag in tags if tag.strip()]

    status_text = ("%s" % status).lower()
    requests = []
    if status_text in ["0", "false"]:
        requests = pagure.lib.query.search_pull_requests(
            flask.g.session,
            project_id=repo.id,
            status=False,
            assignee=assignee,
            author=author,
            tags=tags,
        )

    elif status_text == "all":
        requests = pagure.lib.query.search_pull_requests(
            flask.g.session,
            project_id=repo.id,
            status=None,
            assignee=assignee,
            author=author,
            tags=tags,
        )

    else:
        requests = pagure.lib.query.search_pull_requests(
            flask.g.session,
            project_id=repo.id,
            assignee=assignee,
            author=author,
            status=status,
            tags=tags,
        )

    page = get_page()
    per_page = get_per_page()

    pagination_metadata = pagure.lib.query.get_pagination_metadata(
        flask.request, page, per_page, len(requests)
    )
    start = (page - 1) * per_page
    if start + per_page > len(requests):
        requests_page = requests[start:]
    else:
        requests_page = requests[start : (start + per_page)]

    jsonout = {
        "total_requests": len(requests),
        "requests": [
            request.to_json(public=True, api=True) for request in requests_page
        ],
        "args": {
            "status": status,
            "assignee": assignee,
            "author": author,
            "tags": tags,
        },
    }
    if pagination_metadata:
        jsonout["args"]["page"] = page
        jsonout["args"]["per_page"] = per_page
        jsonout["pagination"] = pagination_metadata
    return flask.jsonify(jsonout)


@API.route("/pull-requests/<uid>")
@api_method
def api_pull_request_by_uid_view(uid):
    """
    Pull-request by UID information
    -------------------------------
    Retrieve information of a pull request specified by uid.

    ::

        GET /api/0/pull-requests/<uid>

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

    request = _get_request(requestuid=uid)

    # we don't really need the repo, but we need to make sure
    # that we're allowed to access it
    username = request.project.user.user if request.project.is_fork else None
    repo = get_authorized_api_project(
        flask.g.session,
        request.project.name,
        user=username,
        namespace=request.project.namespace,
    )
    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOREQ)

    if not repo.settings.get("pull_requests", True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED
        )

    jsonout = flask.jsonify(request.to_json(public=True, api=True))
    return jsonout


@API.route("/<repo>/pull-request/<int:requestid>")
@API.route("/<namespace>/<repo>/pull-request/<int:requestid>")
@API.route("/fork/<username>/<repo>/pull-request/<int:requestid>")
@API.route("/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>")
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
    comments = is_true(flask.request.args.get("comments", True))

    repo = _get_repo(repo, username, namespace)
    _check_pull_request(repo)
    request = _get_request(repo, requestid)
    _check_private_pull_request_access(request)

    jsonout = flask.jsonify(
        request.to_json(public=True, api=True, with_comments=comments)
    )
    return jsonout


@API.route("/<repo>/pull-request/<int:requestid>", methods=["POST"])
@API.route(
    "/<namespace>/<repo>/pull-request/<int:requestid>", methods=["POST"]
)
@API.route(
    "/fork/<username>/<repo>/pull-request/<int:requestid>", methods=["POST"]
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>",
    methods=["POST"],
)
@api_login_required(acls=["pull_request_update"])
@api_method
def api_pull_request_update(repo, requestid, username=None, namespace=None):
    """
    Update pull-request information
    -------------------------------
    Update the title and initial comment of an existing pull-request.

    ::

        POST /api/0/<repo>/pull-request/<request id>
        POST /api/0/<namespace>/<repo>/pull-request/<request id>

    ::

        POST /api/0/fork/<username>/<repo>/pull-request/<request id>
        POST /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>


    Input
    ^^^^^

    +---------------------+--------+-------------+-----------------------------+
    | Key                 | Type   | Optionality | Description                 |
    +=====================+========+=============+=============================+
    | ``title``           | string | Mandatory   | | The title to give to the  |
    |                     |        |             |   pull-request              |
    +---------------------+--------+-------------+-----------------------------+
    | ``initial_comment`` | string | Optional    | | The initial comment or    |
    |                     |        |             |   description of the        |
    |                     |        |             |   pull-request              |
    +---------------------+--------+-------------+-----------------------------+

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

    """  # noqa

    repo = _get_repo(repo, username, namespace)

    _check_pull_request(repo)
    _check_token(repo, project_token=False)

    request = _get_request(repo, requestid)
    _check_pull_request_access(request, assignee=True)

    form = pagure.forms.RequestPullForm(meta={'csrf': False})
    if not form.validate_on_submit():
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors
        )
    else:
        request.title = form.title.data.strip()
        request.initial_comment = ""
        # This value is optional, check first if it's filled
        if form.initial_comment.data:
            request.initial_comment = form.initial_comment.data.strip()
        flask.g.session.add(request)
        if not request.private and not request.project.private:
            pagure.lib.notify.log(
                request.project,
                topic="pull-request.initial_comment.edited",
                msg={
                    "pullrequest": request.to_json(
                        public=True, with_comments=False
                    ),
                    "project": request.project.to_json(public=True),
                    "agent": flask.g.fas_user.username,
                },
            )
        try:
            # Link the PR to issue(s) if there is such link
            pagure.lib.query.link_pr_to_issue_on_description(
                flask.g.session, request
            )
            flask.g.session.commit()
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    request = _get_request(repo, requestid)
    jsonout = flask.jsonify(request.to_json(public=True, api=True))
    return jsonout


@API.route("/<repo>/pull-request/<int:requestid>/merge", methods=["POST"])
@API.route(
    "/<namespace>/<repo>/pull-request/<int:requestid>/merge", methods=["POST"]
)
@API.route(
    "/fork/<username>/<repo>/pull-request/<int:requestid>/merge",
    methods=["POST"],
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/merge",
    methods=["POST"],
)
@api_login_required(acls=["pull_request_merge"])
@api_method
def api_pull_request_merge(repo, requestid, username=None, namespace=None):
    """
    Merge a pull-request
    --------------------
    Instruct Pagure to merge a pull request.

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

    repo = _get_repo(repo, username, namespace)
    _check_pull_request(repo)
    _check_token(repo, project_token=False)
    request = _get_request(repo, requestid)

    if not is_repo_committer(repo):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.ENOPRCLOSE)

    if repo.settings.get("Only_assignee_can_merge_pull-request", False):
        if not request.assignee:
            raise pagure.exceptions.APIError(
                403, error_code=APIERROR.ENOTASSIGNED
            )

        if request.assignee.username != flask.g.fas_user.username:
            raise pagure.exceptions.APIError(
                403, error_code=APIERROR.ENOTASSIGNEE
            )

    threshold = repo.settings.get("Minimum_score_to_merge_pull-request", -1)
    if threshold > 0 and int(request.score) < int(threshold):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.EPRSCORE)

    task = pagure.lib.tasks.merge_pull_request.delay(
        repo.name, namespace, username, requestid, flask.g.fas_user.username
    )
    output = {"message": "Merging queued", "taskid": task.id}

    if get_request_data().get("wait", True):
        try:
            task.get()
            output = {"message": "Changes merged!"}
        except pagure.exceptions.PagureException:
            raise pagure.exceptions.APIError(
                409, error_code=APIERROR.EPRCONFLICTS
            )

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/pull-request/<int:requestid>/rebase", methods=["POST"])
@API.route(
    "/<namespace>/<repo>/pull-request/<int:requestid>/rebase", methods=["POST"]
)
@API.route(
    "/fork/<username>/<repo>/pull-request/<int:requestid>/rebase",
    methods=["POST"],
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/rebase",
    methods=["POST"],
)
@api_login_required(acls=["pull_request_rebase"])
@api_method
def api_pull_request_rebase(repo, requestid, username=None, namespace=None):
    """
    Rebase a pull-request
    ---------------------
    Instruct Pagure to rebase a pull request.

    This is an asynchronous call.

    ::

        POST /api/0/<repo>/pull-request/<request id>/rebase
        POST /api/0/<namespace>/<repo>/pull-request/<request id>/rebase

    ::

        POST /api/0/fork/<username>/<repo>/pull-request/<request id>/rebase
        POST /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>/rebase

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        wait=False:
        {
          "message": "Rebasing queued",
          "taskid": "123-abcd"
        }

        wait=True:
        {
          "message": "Pull-request rebased"
        }

    """  # noqa
    output = {}

    repo = _get_repo(repo, username, namespace)
    _check_pull_request(repo)
    _check_token(repo, project_token=False)
    request = _get_request(repo, requestid)

    can_rebase = (
        not request.remote_git
        and request.project_from
        and is_repo_committer(request.project_from)
    )

    if not ((is_repo_committer(repo) and request.allow_rebase) or can_rebase):
        raise pagure.exceptions.APIError(
            403,
            error_code=APIERROR.EREBASENOTALLOWED
            if not request.allow_rebase
            else APIERROR.ENOPRCLOSE,
        )

    task = pagure.lib.tasks.rebase_pull_request.delay(
        repo.name,
        namespace,
        username,
        requestid,
        user_rebaser=flask.g.fas_user.username,
    )
    output = {"message": "Rebasing queued", "taskid": task.id}

    if get_request_data().get("wait", True):
        try:
            task.get()
            output = {"message": "Pull-request rebased"}
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err)
            )

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/pull-request/<int:requestid>/close", methods=["POST"])
@API.route(
    "/<namespace>/<repo>/pull-request/<int:requestid>/close", methods=["POST"]
)
@API.route(
    "/fork/<username>/<repo>/pull-request/<int:requestid>/close",
    methods=["POST"],
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/close",
    methods=["POST"],
)
@api_login_required(acls=["pull_request_close"])
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

    repo = _get_repo(repo, username, namespace)
    _check_pull_request(repo)
    _check_token(repo, project_token=False)
    request = _get_request(repo, requestid)

    if (
        not is_repo_committer(repo)
        and not flask.g.fas_user.username == request.user.username
    ):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.ENOPRCLOSE)

    try:
        pagure.lib.query.close_pull_request(
            flask.g.session, request, flask.g.fas_user.username, merged=False
        )
        flask.g.session.commit()
        output["message"] = "Pull-request closed!"
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        _log.exception(err)
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/pull-request/<int:requestid>/reopen", methods=["POST"])
@API.route(
    "/<namespace>/<repo>/pull-request/<int:requestid>/reopen", methods=["POST"]
)
@API.route(
    "/fork/<username>/<repo>/pull-request/<int:requestid>/reopen",
    methods=["POST"],
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/reopen",
    methods=["POST"],
)
@api_login_required(acls=["pull_request_close", "pull_request_update"])
@api_method
def api_pull_request_reopen(repo, requestid, username=None, namespace=None):
    """
    Reopen a pull-request
    --------------------
    Instruct Pagure to reopen a pull request.

    ::

        POST /api/0/<repo>/pull-request/<request id>/reopen
        POST /api/0/<namespace>/<repo>/pull-request/<request id>/reopen

    ::

        POST /api/0/fork/<username>/<repo>/pull-request/<request id>/reopen
        POST /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>/reopen

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "Pull-request reopened!"
        }

    """  # noqa
    output = {}

    repo = _get_repo(repo, username, namespace)
    _check_pull_request(repo)
    _check_token(repo, project_token=False)
    request = _get_request(repo, requestid)

    if (
        not is_repo_committer(repo)
        and not flask.g.fas_user.username == request.user.username
    ):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.ENOPRCLOSE)

    try:
        pagure.lib.query.reopen_pull_request(
            flask.g.session, request, flask.g.fas_user.username
        )
        flask.g.session.commit()
        output["message"] = "Pull-request reopened!"
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        _log.exception(err)
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/pull-request/<int:requestid>/comment", methods=["POST"])
@API.route(
    "/<namespace>/<repo>/pull-request/<int:requestid>/comment",
    methods=["POST"],
)
@API.route(
    "/fork/<username>/<repo>/pull-request/<int:requestid>/comment",
    methods=["POST"],
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/comment",
    methods=["POST"],
)
@api_login_required(acls=["pull_request_comment"])
@api_method
def api_pull_request_add_comment(
    repo, requestid, username=None, namespace=None
):
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

    output = {}

    repo = _get_repo(repo, username, namespace)
    _check_pull_request(repo)
    _check_token(repo, project_token=False)
    request = _get_request(repo, requestid)

    form = pagure.forms.AddPullRequestCommentForm(meta={'csrf': False})
    if form.validate_on_submit():
        comment = form.comment.data
        commit = form.commit.data or None
        filename = form.filename.data or None
        tree_id = form.tree_id.data or None
        row = form.row.data or None
        try:
            # New comment
            message = pagure.lib.query.add_pull_request_comment(
                flask.g.session,
                request=request,
                commit=commit,
                tree_id=tree_id,
                filename=filename,
                row=row,
                comment=comment,
                user=flask.g.fas_user.username,
            )
            flask.g.session.commit()
            output["message"] = message
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err)
            )
        except SQLAlchemyError as err:  # pragma: no cover
            _log.exception(err)
            flask.g.session.rollback()
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors
        )

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/pull-request/<int:requestid>/flag", methods=["POST"])
@API.route(
    "/<namespace>/<repo>/pull-request/<int:requestid>/flag", methods=["POST"]
)
@API.route(
    "/fork/<username>/<repo>/pull-request/<int:requestid>/flag",
    methods=["POST"],
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/flag",
    methods=["POST"],
)
@api_login_required(acls=["pull_request_flag"])
@api_method
def api_pull_request_add_flag(repo, requestid, username=None, namespace=None):
    """
    Flag a pull-request
    -------------------
    Add or edit flags on a pull-request.

    This is an utility method which add a flag to the latest commit of the
    specified pull-request.

    Note that using it has a risk of race-condition if the pull-request changes
    at the time the flag is being added. Using the commit flag endpoint prevents
    this risk of race-condition.

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

    output = {}

    repo = _get_repo(repo, username, namespace)
    _check_pull_request(repo)
    _check_token(repo, project_token=False)
    request = _get_request(repo, requestid)

    if "status" in get_request_data():
        form = pagure.forms.AddPullRequestFlagForm(meta={'csrf': False})
    else:
        form = pagure.forms.AddPullRequestFlagFormV1(meta={'csrf': False})
    if form.validate_on_submit():
        username = form.username.data
        percent = form.percent.data.strip() if form.percent.data else None
        comment = form.comment.data.strip()
        url = form.url.data.strip()
        uid = form.uid.data.strip() if form.uid.data else None
        if "status" in get_request_data():
            status = form.status.data.strip()
        else:
            if percent is None:
                status = pagure_config["FLAG_PENDING"]
            else:
                status = (
                    pagure_config["FLAG_SUCCESS"]
                    if percent != "0"
                    else pagure_config["FLAG_FAILURE"]
                )
        try:
            if not request.commit_stop:
                repopath = None
                parentpath = pagure.utils.get_repo_path(request.project)
                if request.remote:
                    repopath = pagure.utils.get_remote_repo_path(
                        request.remote_git, request.branch_from
                    )
                elif request.project_from:
                    repopath = pagure.utils.get_repo_path(request.project_from)

                repo_obj = None
                if repopath:
                    repo_obj = pygit2.Repository(repopath)
                orig_repo = pygit2.Repository(parentpath)
                pagure.lib.git.diff_pull_request(
                    flask.g.session, request, repo_obj, orig_repo
                )

            # New Flag
            message, uid = pagure.lib.query.add_pull_request_flag(
                session=flask.g.session,
                request=request,
                username=username,
                status=status,
                percent=percent,
                comment=comment,
                url=url,
                uid=uid,
                user=flask.g.fas_user.username,
                token=flask.g.token.id,
            )
            flask.g.session.commit()
            pr_flag = pagure.lib.query.get_commit_flag_by_uid(
                flask.g.session, request.commit_stop, uid
            )
            output["message"] = message
            output["uid"] = uid
            output["flag"] = pr_flag.to_json()
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err)
            )
        except SQLAlchemyError as err:  # pragma: no cover
            _log.exception(err)
            flask.g.session.rollback()
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors
        )

    output["avatar_url"] = pagure.lib.query.avatar_url_from_email(
        flask.g.fas_user.default_email, size=30
    )

    output["user"] = flask.g.fas_user.username

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/pull-request/<int:requestid>/flag", methods=["GET"])
@API.route(
    "/<namespace>/<repo>/pull-request/<int:requestid>/flag", methods=["GET"]
)
@API.route(
    "/fork/<username>/<repo>/pull-request/<int:requestid>/flag",
    methods=["GET"],
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/flag",
    methods=["GET"],
)
@api_method
def api_pull_request_get_flag(repo, requestid, username=None, namespace=None):
    """
    Get flag(s) of a pull-request
    -----------------------------
    Retrieve the flags on a pull-request.

    ::

        GET /api/0/<repo>/pull-request/<request id>/flag
        GET /api/0/<namespace>/<repo>/pull-request/<request id>/flag

    ::

        GET /api/0/fork/<username>/<repo>/pull-request/<request id>/flag
        GET /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>/flag


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "flags": [
            {
              "comment": "Tests are running in the AtomicCI pipeline",
              "date_created": "1537560168",
              "percent": null,
              "pull_request_uid": "4fb1f8db8f114baeb943b6f10c5de015",
              "status": "failure",
              "url": "https://jenkins-continuous-infra.apps.ci.centos.org/job/continuous-infra-ci-pipeline-f26/...",
              "user": {
                "fullname": "Pierre-YvesChibon",
                "name": "pingou"
              },
              "username": "AtomicCI"
            },
            {
              "comment": "Built successfully",
              "date_created": "1517565878",
              "percent": 100,
              "pull_request_uid": "4fb1f8db8f114baeb943b6f10c5de015",
              "status": "success",
              "url": "https://koji.fedoraproject.org/koji/...",
              "user": {
                "fullname": "Pierre-YvesChibon",
                "name": "pingou"
              },
              "username": "simple-koji-ci"
            }
          ]
        }

    """  # noqa

    output = {}

    repo = _get_repo(repo, username, namespace)
    _check_pull_request(repo)
    request = _get_request(repo, requestid)

    if not request.commit_stop:
        repopath = None
        parentpath = pagure.utils.get_repo_path(request.project)
        if request.remote:
            repopath = pagure.utils.get_remote_repo_path(
                request.remote_git, request.branch_from
            )
        elif request.project_from:
            repopath = pagure.utils.get_repo_path(request.project_from)

        repo_obj = None
        if repopath:
            repo_obj = pygit2.Repository(repopath)
        orig_repo = pygit2.Repository(parentpath)
        pagure.lib.git.diff_pull_request(
            flask.g.session, request, repo_obj, orig_repo
        )

    output = {"flags": []}

    flags = pagure.lib.query.get_commit_flag(
        flask.g.session, request.project, request.commit_stop
    )

    for flag in flags:
        output["flags"].append(flag.to_json(public=True))

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/pull-request/<int:requestid>/subscribe", methods=["POST"])
@API.route(
    "/<namespace>/<repo>/pull-request/<int:requestid>/subscribe",
    methods=["POST"],
)
@API.route(
    "/fork/<username>/<repo>/pull-request/<int:requestid>/subscribe",
    methods=["POST"],
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>"
    "/subscribe",
    methods=["POST"],
)
@api_login_required(acls=["pull_request_subscribe"])
@api_method
def api_subscribe_pull_request(repo, requestid, username=None, namespace=None):
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
          "message": "User subscribed",
          "avatar_url": "https://image.png",
          "user": "pingou"
        }

    """  # noqa

    output = {}

    repo = _get_repo(repo, username, namespace)
    _check_pull_request(repo)
    _check_token(repo)
    request = _get_request(repo, requestid)

    form = pagure.forms.SubscribtionForm(meta={'csrf': False})
    if form.validate_on_submit():
        status = is_true(form.status.data)
        try:
            # Toggle subscribtion
            message = pagure.lib.query.set_watch_obj(
                flask.g.session,
                user=flask.g.fas_user.username,
                obj=request,
                watch_status=status,
            )
            flask.g.session.commit()
            output["message"] = message
            user_obj = pagure.lib.query.get_user(
                flask.g.session, flask.g.fas_user.username
            )
            output["avatar_url"] = pagure.lib.query.avatar_url_from_email(
                user_obj.default_email, size=30
            )
            output["user"] = flask.g.fas_user.username
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.logger.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/pull-request/new", methods=["POST"])
@API.route("/<namespace>/<repo>/pull-request/new", methods=["POST"])
@API.route("/fork/<username>/<repo>/pull-request/new", methods=["POST"])
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/new", methods=["POST"]
)
@api_login_required(acls=["pull_request_create"])
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

    +-----------------------+----------+-------------+------------------------+
    | Key                   | Type     | Optionality | Description            |
    +=======================+==========+=============+========================+
    | ``title``             | string   | Mandatory   | The title to give to   |
    |                       |          |             | this pull-request      |
    +-----------------------+----------+-------------+------------------------+
    | ``branch_to``         | string   | Mandatory   | The name of the branch |
    |                       |          |             | the submitted changes  |
    |                       |          |             | should be merged into. |
    +-----------------------+----------+-------------+------------------------+
    | ``branch_from``       | string   | Mandatory   | The name of the branch |
    |                       |          |             | containing the changes |
    |                       |          |             | to merge               |
    +-----------------------+----------+-------------+------------------------+
    | ``repo_from``         | string   | Optional    | The name of the project|
    |                       |          |             | the changes originate  |
    |                       |          |             | from.                  |
    |                       |          |             | If not specified the   |
    |                       |          |             | repo_from is assumed   |
    |                       |          |             | to be the repo_to.     |
    +-----------------------+----------+-------------+------------------------+
    | ``repo_from_username``| string   | Optional    | The username of the    |
    |                       |          |             | project the changes    |
    |                       |          |             | originate from.        |
    |                       |          |             | If not specified the   |
    |                       |          |             | repo_from is assumed   |
    |                       |          |             | to be the repo_to.     |
    +-----------------------+----------+-------------+------------------------+
    |``repo_from_namespace``| string   | Optional    | The namespace of the   |
    |                       |          |             | project the changes    |
    |                       |          |             | originate from.        |
    |                       |          |             | If not specified the   |
    |                       |          |             | repo_from is assumed   |
    |                       |          |             | to be the repo_to.     |
    +-----------------------+----------+-------------+------------------------+
    | ``initial_comment``   | string   | Optional    | The intial comment     |
    |                       |          |             | describing what these  |
    |                       |          |             | changes are about.     |
    +-----------------------+----------+-------------+------------------------+

    Note: If f the repo you're opening the PR against is not the same as the
    repo from which the changes originates, you must provide the ``repo_from``
    and ``repo_from_username`` (and potentially ``repo_from_namespace``)
    corresponding to the fork.

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

    """  # noqa

    repo_to = _get_repo(repo, username, namespace)

    req_data = get_request_data()
    repo_from = req_data.get("repo_from")
    repo_from_username = req_data.get("repo_from_username")
    repo_from_namespace = req_data.get("repo_from_namespace")

    if repo_from:
        repo_from = _get_repo(
            repo_from,
            username=repo_from_username,
            namespace=repo_from_namespace,
        )
    else:
        repo_from = repo_to

    _check_pull_request(repo_to)
    _check_token(repo_from, project_token=False)

    form = pagure.forms.RequestPullForm(meta={'csrf': False})
    if not form.validate_on_submit():
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors
        )
    branch_to = get_request_data().get("branch_to")
    if not branch_to:
        raise pagure.exceptions.APIError(
            400,
            error_code=APIERROR.EINVALIDREQ,
            errors={"branch_to": ["This field is required."]},
        )
    branch_from = get_request_data().get("branch_from")
    if not branch_from:
        raise pagure.exceptions.APIError(
            400,
            error_code=APIERROR.EINVALIDREQ,
            errors={"branch_from": ["This field is required."]},
        )

    if not repo_to.settings.get("pull_requests", True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EPULLREQUESTSDISABLED
        )

    repo_committer = pagure.utils.is_repo_committer(repo_from)

    if not repo_committer:
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.ENOTHIGHENOUGH
        )

    git_repo_from = pygit2.Repository(repo_from.repopath("main"))
    git_repo_to = pygit2.Repository(repo_to.repopath("main"))

    try:
        diff, diff_commits, orig_commit = pagure.lib.git.get_diff_info(
            git_repo_from, git_repo_to, branch_from, branch_to
        )
    except pagure.exceptions.PagureException as err:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=str(err)
        )

    if repo_to.settings.get(
        "Enforce_signed-off_commits_in_pull-request", False
    ):
        for commit in diff_commits:
            if "signed-off-by" not in commit.message.lower():
                raise pagure.exceptions.APIError(
                    400, error_code=APIERROR.ENOSIGNEDOFF
                )

    if orig_commit:
        orig_commit = orig_commit.oid.hex

    initial_comment = None
    # This value is optional, check first if it's filled
    if form.initial_comment.data:
        initial_comment = form.initial_comment.data.strip()

    commit_start = commit_stop = None
    if diff_commits:
        commit_stop = diff_commits[0].oid.hex
        commit_start = diff_commits[-1].oid.hex

    request = pagure.lib.query.new_pull_request(
        flask.g.session,
        repo_to=repo_to,
        branch_to=branch_to,
        branch_from=branch_from,
        repo_from=repo_from,
        title=form.title.data,
        initial_comment=initial_comment,
        user=flask.g.fas_user.username,
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


@API.route("/<repo>/pull-request/<int:requestid>/diffstats")
@API.route("/<namespace>/<repo>/pull-request/<int:requestid>/diffstats")
@API.route("/fork/<username>/<repo>/pull-request/<int:requestid>/diffstats")
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/"
    "diffstats"
)
@api_method
def api_pull_request_diffstats(repo, requestid, username=None, namespace=None):
    """
    Pull-request diff statistics
    ----------------------------
    Retrieve the statistics about the diff of a specific pull request.

    ::

        GET /api/0/<repo>/pull-request/<request id>/diffstats
        GET /api/0/<namespace>/<repo>/pull-request/<request id>/diffstats

    ::

        GET /api/0/fork/<username>/<repo>/pull-request/<request id>/diffstats
        GET /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>/diffstats

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "README.rst": {
            "lines_added": 1,
            "lines_removed": 1,
            "old_path": "README.rst",
            "status": "M"
          },
          "blame_file.txt": {
            "lines_added": 0,
            "lines_removed": 0,
            "old_path": "blame_file",
            "status": "R"
          },
          "test": {
            "lines_added": 0,
            "lines_removed": 8,
            "old_path": "test",
            "status": "D"
          },
          "test3": {
            "lines_added": 3,
            "lines_removed": 0,
            "old_path": "test3",
            "status": "A"
          }
        }



    """  # noqa

    repo = _get_repo(repo, username, namespace)
    _check_pull_request(repo)
    request = _get_request(repo, requestid)

    repopath = None
    parentpath = pagure.utils.get_repo_path(request.project)
    if request.remote:
        repopath = pagure.utils.get_remote_repo_path(
            request.remote_git, request.branch_from
        )
    elif request.project_from:
        repopath = pagure.utils.get_repo_path(request.project_from)

    repo_obj = None
    if repopath:
        repo_obj = pygit2.Repository(repopath)
    orig_repo = pygit2.Repository(parentpath)

    diff_commits = []
    diff = None
    # Closed pull-request
    if request.status != "Open":
        commitid = request.commit_stop
        try:
            for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_NONE):
                diff_commits.append(commit)
                if commit.oid.hex == request.commit_start:
                    break
        except KeyError:
            # This happens when repo.walk() cannot find commitid
            pass

        if diff_commits:
            # Ensure the first commit in the PR as a parent, otherwise
            # point to it
            start = diff_commits[-1].oid.hex
            if diff_commits[-1].parents:
                start = diff_commits[-1].parents[0].oid.hex

            # If the start and the end commits are the same, it means we are,
            # dealing with one commit that has no parent, so just diff that
            # one commit
            if start == diff_commits[0].oid.hex:
                diff = diff_commits[0].tree.diff_to_tree(swap=True)
            else:
                diff = repo_obj.diff(
                    repo_obj.revparse_single(start),
                    repo_obj.revparse_single(diff_commits[0].oid.hex),
                )
    else:
        try:
            diff_commits, diff = pagure.lib.git.diff_pull_request(
                flask.g.session, request, repo_obj, orig_repo
            )
        except pagure.exceptions.PagureException as err:
            flask.flash("%s" % err, "error")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash(
                "Could not update this pull-request in the database", "error"
            )

    if diff:
        diff.find_similar()

    output = {}
    if diff:
        for patch in diff:
            stats = pagure.lib.git.get_stats_patch(patch)
            new_path = stats["new_path"]
            del stats["new_path"]
            output[new_path] = stats
    else:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.ENOPRSTATS)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/pull-request/<int:requestid>/assign", methods=["POST"])
@API.route(
    "/<namespace>/<repo>/pull-request/<int:requestid>/assign", methods=["POST"]
)
@API.route(
    "/fork/<username>/<repo>/pull-request/<int:requestid>/assign",
    methods=["POST"],
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/assign",
    methods=["POST"],
)
@api_login_required(acls=["pull_request_assign", "pull_request_update"])
@api_method
def api_pull_request_assign(repo, requestid, username=None, namespace=None):
    """
    Assign a pull-request
    ---------------------
    Assign a pull-request to someone.

    ::

        POST /api/0/<repo>/pull-request/<issue id>/assign
        POST /api/0/<namespace>/<repo>/pull-request/<issue id>/assign

    ::

        POST /api/0/fork/<username>/<repo>/pull-request/<issue id>/assign
        POST /api/0/fork/<username>/<namespace>/<repo>/pull-request/<issue id>/assign

    Input
    ^^^^^

    +--------------+----------+---------------+---------------------------+
    | Key          | Type     | Optionality   | Description               |
    +==============+==========+===============+===========================+
    | ``assignee`` | string   | Mandatory     | | The username of the user|
    |              |          |               |   to assign the PR to.    |
    +--------------+----------+---------------+---------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "pull-request assigned"
        }

    """  # noqa
    output = {}
    repo = _get_repo(repo, username, namespace)

    _check_pull_request(repo)
    _check_token(repo)

    request = _get_request(repo, requestid)
    _check_pull_request_access(request, assignee=True)

    form = pagure.forms.AssignIssueForm(meta={'csrf': False})
    if form.validate_on_submit():
        assignee = form.assignee.data or None
        # Create our metadata comment object
        try:
            # New comment
            message = pagure.lib.query.add_pull_request_assignee(
                flask.g.session,
                request=request,
                assignee=assignee,
                user=flask.g.fas_user.username,
            )
            flask.g.session.commit()
            if message:
                pagure.lib.query.add_metadata_update_notif(
                    session=flask.g.session,
                    obj=request,
                    messages=message,
                    user=flask.g.fas_user.username,
                )
                output["message"] = message
            else:
                output["message"] = "Nothing to change"
        except pagure.exceptions.PagureException as err:  # pragma: no cover
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err)
            )
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route(
    "/<repo>/pull-request/<int:requestid>/comment/<int:commentid>",
    methods=["GET"],
)
@API.route(
    "/<namespace>/<repo>/pull-request/<int:requestid>/comment/<int:commentid>",
    methods=["GET"],
)
@API.route(
    "/fork/<username>/<repo>/pull-request/<int:requestid>/comment/"
    "<int:commentid>",
    methods=["GET"],
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/comment/"
    "<int:commentid>",
    methods=["GET"],
)
@api_method
def api_pull_request_get_comment(
    repo, requestid, commentid, username=None, namespace=None
):
    """
    Comment of a pull-request
    -------------------------
    Retrieve a specific comment of a pull-request.

    ::

        GET /api/0/<repo>/pull-request/<request id>/comment/<int:commentid>
        GET /api/0/<namespace>/<repo>/pull-request/<request id>/comment/<int:commentid>

    ::

        GET /api/0/fork/<username>/<repo>/pull-request/<request id>/comment/<int:commentid>
        GET /api/0/fork/<username>/<namespace>/<repo>/pull-request/<request id>/comment/<int:commentid>


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "comment": "Fix indentation.",
          "commit": "f2345d6c164f704d9afb91f8dc2f5bd0cf3202e7",
          "date_created": "1519735412",
          "edited_on": null,
          "editor": null,
          "filename": "pagure/default_config.py",
          "id": 46372,
          "line": 8,
          "notification": false,
          "parent": null,
          "reactions": {},
          "tree": "cc781b3cb8896e85bd9e4b02655ef3af42c0bd11",
          "user": {
            "fullname": "Alice A.",
            "name": "alice"
          }
        }

    """  # noqa

    output = {}

    repo = _get_repo(repo, username, namespace)
    _check_pull_request(repo)
    request = _get_request(repo, requestid)
    _check_private_pull_request_access(request)

    comment = pagure.lib.query.get_request_comment(
        flask.g.session, request.uid, commentid
    )
    if not comment:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOCOMMENT)

    output = comment.to_json(public=True)
    jsonout = flask.jsonify(output)
    return jsonout
