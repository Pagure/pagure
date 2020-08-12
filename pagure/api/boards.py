# -*- coding: utf-8 -*-

"""
 (c) 2020 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import logging

import flask
from sqlalchemy.exc import SQLAlchemyError
import werkzeug.datastructures

import pagure
import pagure.exceptions
import pagure.lib.query
import pagure.lib.tasks
from pagure.forms import TAGS_REGEX, TAGS_REGEX_RE
from pagure.api import (
    API,
    api_method,
    api_login_required,
    APIERROR,
    get_request_data,
)
from pagure.api.utils import (
    _get_repo,
    _check_token,
    _check_issue_tracker,
)


_log = logging.getLogger(__name__)


@API.route("/<repo>/boards")
@API.route("/<namespace>/<repo>/boards")
@API.route("/fork/<username>/<repo>/boards")
@API.route("/fork/<username>/<namespace>/<repo>/boards")
@api_method
def api_boards_view(repo, username=None, namespace=None):
    """
    List a project's boards
    -----------------------
    Retrieve the list of boards a project has.

    ::

        GET /api/0/<repo>/boards
        GET /api/0/<namespace>/<repo>/boards

    ::

        GET /api/0/fork/<username>/<repo>/boards
        GET /api/0/fork/<username>/<namespace>/<repo>/boards

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "total_boards": 3,
          "boards": [
            {"name": "infrastructure", "active": true},
            {"name": "releng", "active": true},
            {"name": "initiatives", "active": true},
          ]
        }

    """

    repo = _get_repo(repo, username, namespace)
    _check_issue_tracker(repo)

    boards = repo.boards

    jsonout = {
        "total_requests": len(boards),
        "boards": [board.to_json() for board in boards],
    }
    return flask.jsonify(jsonout)


@API.route("/<repo>/boards", methods=["POST"])
@API.route("/<namespace>/<repo>/boards", methods=["POST"])
@API.route("/fork/<username>/<repo>/boards", methods=["POST"])
@API.route(
    "/fork/<username>/<namespace>/<repo>/boards", methods=["POST"],
)
@api_login_required(acls=["modify_project"])
@api_method
def api_board_create(repo, username=None, namespace=None):
    """
    Create a board
    --------------
    Create a new board on a project

    ::

        POST /api/0/<repo>/boards
        POST /api/0/<namespace>/<repo>/boards

    ::

        POST /api/0/fork/<username>/<repo>/boards
        POST /api/0/fork/<username>/<namespace>/<repo>/boards


    Input
    ^^^^^

        {
            "board_name": {
                "active": <boolean>,
                "tag": <string>
            },
            "Infrastructure": {
                "active": true,
                "tag": "backlog"
            }
        }

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            "boards": [
                {
                    "active": True,
                    "name": "dev",
                    "status": [],
                    "tag": {
                        "tag": "dev",
                        "tag_color": "DeepBlueSky",
                        "tag_description": "",
                    },
                },
                {
                    "active": True,
                    "name": "infra",
                    "status": [],
                    "tag": {
                        "tag": "infra",
                        "tag_color": "DeepGreen",
                        "tag_description": "",
                    },
                },
            ]
        }

    """  # noqa

    repo = _get_repo(repo, username, namespace)

    _check_issue_tracker(repo)
    _check_token(repo, project_token=False)

    data = flask.request.get_json() or {}
    if not data:
        raise pagure.exceptions.APIError(
            400,
            error_code=APIERROR.EINVALIDREQ,
            errors="No (JSON) data provided",
        )
    for key in data:
        if not isinstance(data[key], bool) and "tag" not in data[key]:
            raise pagure.exceptions.APIError(
                400,
                error_code=APIERROR.EINVALIDREQ,
                errors="No tag associated with at least one of the boards",
            )

    names = list(data.keys())

    existing_board_names = set(board.name for board in repo.boards)
    removing_names = set(existing_board_names) - set(names)

    for name in data:
        if name not in existing_board_names:
            try:
                pagure.lib.query.create_board(
                    flask.g.session,
                    project=repo,
                    name=name,
                    active=data[name].get("active", False),
                    tag=data[name]["tag"],
                )
                flask.g.session.commit()
            except pagure.exceptions.PagureException as err:
                raise pagure.exceptions.APIError(
                    400, error_code=APIERROR.ENOCODE, error=str(err)
                )
            except SQLAlchemyError as err:  # pragma: no cover
                flask.g.session.rollback()
                _log.exception(err)
                raise pagure.exceptions.APIError(
                    400, error_code=APIERROR.EDBERROR
                )
        else:
            try:
                pagure.lib.query.edit_board(
                    flask.g.session,
                    project=repo,
                    name=name,
                    active=data[name].get("active", False),
                    tag=data[name]["tag"],
                )
                flask.g.session.commit()
            except pagure.exceptions.PagureException as err:
                raise pagure.exceptions.APIError(
                    400, error_code=APIERROR.ENOCODE, error=str(err)
                )
            except SQLAlchemyError as err:  # pragma: no cover
                flask.g.session.rollback()
                _log.exception(err)
                raise pagure.exceptions.APIError(
                    400, error_code=APIERROR.EDBERROR
                )

    if removing_names:
        try:
            pagure.lib.query.delete_board(
                flask.g.session, project=repo, names=removing_names,
            )
            flask.g.session.commit()
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    return flask.jsonify(
        {"boards": [board.to_json() for board in repo.boards]}
    )


@API.route("/<repo>/boards/delete", methods=["POST"])
@API.route("/<namespace>/<repo>/boards/delete", methods=["POST"])
@API.route("/fork/<username>/<repo>/boards/delete", methods=["POST"])
@API.route(
    "/fork/<username>/<namespace>/<repo>/boards/delete", methods=["POST"],
)
@api_login_required(acls=["modify_project"])
@api_method
def api_board_delete(repo, username=None, namespace=None):
    """
    Delete a board
    ---------------
    Delet a board of a project

    ::

        POST /api/0/<repo>/boards/delete
        POST /api/0/<namespace>/<repo>/boards/delete

    ::

        POST /api/0/fork/<username>/<repo>/boards/delete
        POST /api/0/fork/<username>/<namespace>/<repo>/boards/delete


    Input
    ^^^^^

    +---------------------+---------+-------------+-----------------------------+
    | Key                 | Type    | Optionality | Description                 |
    +=====================+=========+=============+=============================+
    | ``name``            | string  | Mandatory   | | The name of the board to  |
    |                     |         |             |   delete.                   |
    +---------------------+---------+-------------+-----------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
        }

    """  # noqa

    repo = _get_repo(repo, username, namespace)

    _check_issue_tracker(repo)
    _check_token(repo, project_token=False)

    fields = get_request_data()
    if not isinstance(fields, werkzeug.datastructures.ImmutableMultiDict):
        names_in = fields.get("name") or []
    else:
        names_in = fields.getlist("name")

    names = []
    for idx, name in enumerate(names_in):
        if name.strip():
            names.append(name)

    if not names:
        raise pagure.exceptions.APIError(
            400,
            error_code=APIERROR.EINVALIDREQ,
            errors={"name": ["This field is required"]},
        )

    try:
        pagure.lib.query.delete_board(
            flask.g.session, project=repo, names=names,
        )
        flask.g.session.commit()
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        _log.exception(err)
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    repo = _get_repo(repo.name, username, namespace)
    return flask.jsonify(
        {"boards": [board.to_json() for board in repo.boards]}
    )


@API.route("/<repo>/boards/<board_name>/status", methods=["POST"])
@API.route("/<namespace>/<repo>/boards/<board_name>/status", methods=["POST"])
@API.route(
    "/fork/<username>/<repo>/boards/<board_name>/status", methods=["POST"]
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/boards/<board_name>/status",
    methods=["POST"],
)
@api_login_required(acls=["modify_project"])
@api_method
def api_board_status(repo, board_name, username=None, namespace=None):
    """
    Update board statuses
    ---------------------
    Set or update the statuses a board has.

    ::

        POST /api/0/<repo>/boards
        POST /api/0/<namespace>/<repo>/boards

    ::

        POST /api/0/fork/<username>/<repo>/boards
        POST /api/0/fork/<username>/<namespace>/<repo>/boards


    Input
    ^^^^^

    Submitted as JSON (Requires setting a
    ``contentType: 'application/json; charset=utf-8'`` header):

    ::

        {
            "Triaged": {
                "close": false,
                "close_status": "",
                "bg_color": "#ca0dcd",
                "default": true,
                "rank": 1
            },
            "In Progress": {
                "close": false,
                "close_status": "",
                "bg_color": "#1780ec",
                "default": false,
                "rank": 2
            },
            "In Review": {
                "close": false,
                "close_status": "",
                "bg_color": "#f28b20",
                "default": false,
                "rank": 3
            },
            "Done": {
                "close": true,
                "close_status": "Fixed",
                "bg_color": "#34d240",
                "default": false,
                "rank": 4
            },
            "Blocked": {
                "close": false,
                "close_status": "",
                "bg_color": "#ff0022",
                "default": false,
                "rank": 5
            }
        }

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            "board": {
                "active": True,
                "name": "dev",
                "status": [
                    {
                        "bg_color": "#FFB300",
                        "close": false,
                        "close_status": None,
                        "name": "Backlog",
                    },
                    {
                        "bg_color": "#ca0eef",
                        "close": false,
                        "close_status": None,
                        "name": "In Progress",
                    },
                    {
                        "name": "Done",
                        "close": true,
                        "close_status": "Fixed",
                        "bg_color": "#34d240",
                    },
                ],
                "tag": {
                    "tag": "dev",
                    "tag_color": "DeepBlueSky",
                    "tag_description": "",
                },
            }
        }

    """  # noqa

    repo = _get_repo(repo, username, namespace)

    _check_issue_tracker(repo)
    _check_token(repo, project_token=False)

    board = None
    for board_obj in repo.boards:
        if board_obj.name == board_name:
            board = board_obj
            break

    if board is None:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EINVALIDREQ, errors="Board not found",
        )

    data = flask.request.get_json() or {}
    if not data:
        raise pagure.exceptions.APIError(
            400,
            error_code=APIERROR.EINVALIDREQ,
            errors="No (JSON) data provided",
        )

    defaults = []
    for key in data:
        if key.strip():
            if not TAGS_REGEX_RE.match(key):
                raise pagure.exceptions.APIError(
                    400,
                    error_code=APIERROR.EINVALIDREQ,
                    errors={
                        "name": [
                            "Invalid status name provided, it "
                            "should match: %s." % TAGS_REGEX
                        ]
                    },
                )
            if (
                len(
                    set(data[key].keys()).intersection(
                        set(["rank", "default"])
                    )
                )
                != 2
            ):
                raise pagure.exceptions.APIError(
                    400,
                    error_code=APIERROR.EINVALIDREQ,
                    errors="The 'rank' and 'default' fields are" " mandatory.",
                )
            if data[key]["default"] is True:
                defaults.append(key)

    if len(defaults) != 1:
        raise pagure.exceptions.APIError(
            400,
            error_code=APIERROR.EINVALIDREQ,
            errors="There must be one and only one default.",
        )

    for status in board.statuses:
        if status.name not in data:
            _log.debug("Removing status: %s", status.name)
            flask.g.session.delete(status)

    for name in data:
        if not name.strip():
            continue

        try:
            close_status = data[name].get("close_status") or None
            close = data[name].get("close") or (
                True if close_status else False
            )
            if close_status not in repo.close_status:
                close_status = None

            pagure.lib.query.update_board_status(
                flask.g.session,
                board=board,
                name=name,
                rank=data[name]["rank"],
                default=data[name]["default"],
                bg_color=data[name].get("bg_color") or None,
                close=close,
                close_status=close_status,
            )
            flask.g.session.commit()
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    return flask.jsonify({"board": board.to_json()})


@API.route("/<repo>/boards/<board_name>/update_issue", methods=["POST"])
@API.route(
    "/<namespace>/<repo>/boards/<board_name>/update_issue", methods=["POST"]
)
@API.route(
    "/fork/<username>/<repo>/boards/<board_name>/update_issue",
    methods=["POST"],
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/boards/<board_name>/update_issue",
    methods=["POST"],
)
@api_login_required(acls=["modify_project"])
@api_method
def api_board_ticket_update_status(
    repo, board_name, username=None, namespace=None
):
    """
    Update a ticket on a board
    --------------------------
    Update a ticket on a board (ie: update its status).

    ::

        POST /api/0/<repo>/boards/update_issue
        POST /api/0/<namespace>/<repo>/boards/update_issue

    ::

        POST /api/0/fork/<username>/<repo>/boards/update_issue
        POST /api/0/fork/<username>/<namespace>/<repo>/boards/update_issue


    Input
    ^^^^^

    Submitted as JSON (Requires setting a
    ``contentType: 'application/json; charset=utf-8'`` header):

    ::

        {
            "ticket_uid": {
                "status": "status_name"
                "rank": 1
            },
            "asdas12e1dasdasd12e12e": {
                "status":  "In Progress"
                "rank": 2
            }
       }

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            {"name": "infrastructure", "active": true},
        }

    """  # noqa

    repo = _get_repo(repo, username, namespace)

    _check_issue_tracker(repo)
    _check_token(repo, project_token=False)

    board = None
    for board_obj in repo.boards:
        if board_obj.name == board_name:
            board = board_obj
            break

    if board is None:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EINVALIDREQ, errors="Board not found",
        )

    data = flask.request.get_json() or {}
    if not data:
        raise pagure.exceptions.APIError(
            400,
            error_code=APIERROR.EINVALIDREQ,
            errors="No (JSON) data provided",
        )

    for key in data:
        if key.strip():
            if (
                len(
                    set(data[key].keys()).intersection(set(["rank", "status"]))
                )
                != 2
            ):
                raise pagure.exceptions.APIError(
                    400,
                    error_code=APIERROR.EINVALIDREQ,
                    errors="The 'rank' and 'status' fields are mandatory.",
                )

    for ticket_uid in data:
        if not ticket_uid.strip():
            continue

        try:
            pagure.lib.query.update_ticket_board_status(
                flask.g.session,
                board=board,
                user=flask.g.fas_user.username,
                ticket_uid=ticket_uid,
                rank=data[ticket_uid]["rank"],
                status_name=data[ticket_uid]["status"],
            )
            flask.g.session.commit()
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err)
            )
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    return flask.jsonify({"board": board_obj.to_json()})


@API.route("/<repo>/boards/<board_name>/add_issue", methods=["POST"])
@API.route(
    "/<namespace>/<repo>/boards/<board_name>/add_issue", methods=["POST"]
)
@API.route(
    "/fork/<username>/<repo>/boards/<board_name>/add_issue", methods=["POST"],
)
@API.route(
    "/fork/<username>/<namespace>/<repo>/boards/<board_name>/add_issue",
    methods=["POST"],
)
@api_login_required(acls=["modify_project"])
@api_method
def api_board_ticket_add_status(
    repo, board_name, username=None, namespace=None
):
    """
    Add a ticket on a board
    --------------------------
    Add a ticket on a board (ie: update its status).

    ::

        POST /api/0/<repo>/boards/update_issue
        POST /api/0/<namespace>/<repo>/boards/update_issue

    ::

        POST /api/0/fork/<username>/<repo>/boards/update_issue
        POST /api/0/fork/<username>/<namespace>/<repo>/boards/update_issue


    Input
    ^^^^^

    Submitted as JSON (Requires setting a
    ``contentType: 'application/json; charset=utf-8'`` header):

    ::

        {
            "ticket_id_in_the_project": {
                "status": "status_name"
                "rank": 1
            },
            "12": {
                "status":  "In Progress"
                "rank": 2
            }
       }

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            {"name": "infrastructure", "active": true},
        }

    """  # noqa

    repo = _get_repo(repo, username, namespace)

    _check_issue_tracker(repo)
    _check_token(repo, project_token=False)

    board = None
    for board_obj in repo.boards:
        if board_obj.name == board_name:
            board = board_obj
            break

    if board is None:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.EINVALIDREQ, errors="Board not found",
        )

    data = flask.request.get_json() or {}
    if not data:
        raise pagure.exceptions.APIError(
            400,
            error_code=APIERROR.EINVALIDREQ,
            errors="No (JSON) data provided",
        )

    for key in data:
        if key.strip():
            if (
                len(
                    set(data[key].keys()).intersection(set(["rank", "status"]))
                )
                != 2
            ):
                raise pagure.exceptions.APIError(
                    400,
                    error_code=APIERROR.EINVALIDREQ,
                    errors="The 'rank' and 'status' fields are mandatory.",
                )

    for ticket_id in data:
        if not ticket_id.strip():
            continue

        try:
            pagure.lib.query.update_ticket_board_status(
                flask.g.session,
                board=board,
                user=flask.g.fas_user.username,
                ticket_id=ticket_id,
                rank=data[ticket_id]["rank"],
                status_name=data[ticket_id]["status"],
            )
            flask.g.session.commit()
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err)
            )
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    return flask.jsonify({"board": board_obj.to_json()})
