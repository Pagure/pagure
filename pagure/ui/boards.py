# -*- coding: utf-8 -*-

"""
 (c) 2014-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-branches
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements


from __future__ import unicode_literals, absolute_import

import logging

import flask

from pagure.ui import UI_NS
from pagure.utils import (
    authenticated,
    login_required,
)
from pagure.decorators import (
    is_repo_admin,
    is_admin_sess_timedout,
    has_issue_tracker,
)


_log = logging.getLogger(__name__)


@UI_NS.route("/<repo>/boards/<board_name>/")
@UI_NS.route("/<repo>/boards/<board_name>")
@UI_NS.route("/<namespace>/<repo>/boards/<board_name>/")
@UI_NS.route("/<namespace>/<repo>/boards/<board_name>")
@UI_NS.route("/fork/<username>/<repo>/boards/<board_name>/")
@UI_NS.route("/fork/<username>/<repo>/boards/<board_name>")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/boards/<board_name>/")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/boards/<board_name>")
@has_issue_tracker
def view_board(repo, board_name, username=None, namespace=None):
    """View a board"""

    project = flask.g.repo

    board_out = None
    for board in project.boards:
        if board.name == board_name:
            board_out = board
            break

    if board_out is None:
        flask.abort(404)

    # Hide private tickets
    private = False
    # If user is authenticated, show him/her his/her private tickets
    if authenticated():
        private = flask.g.fas_user.username

    # If user is repo committer, show all tickets including the private ones
    if flask.g.repo_committer:
        private = None

    max_items = 0
    for status in board.statuses:
        max_items = max([max_items, len(status.boards_issues)])

    return flask.render_template(
        "board.html",
        select="boards",
        repo=project,
        username=username,
        board=board_out,
        max_items=max_items,
        private=private,
    )


@UI_NS.route("/<repo>/settings/boards/<board_name>/", methods=("GET", "POST"))
@UI_NS.route("/<repo>/settings/boards/<board_name>", methods=("GET", "POST"))
@UI_NS.route(
    "/<namespace>/<repo>/settings/boards/<board_name>/",
    methods=("GET", "POST"),
)
@UI_NS.route(
    "/<namespace>/<repo>/settings/boards/<board_name>", methods=("GET", "POST")
)
@UI_NS.route(
    "/fork/<username>/<repo>/settings/boards/<board_name>/",
    methods=("GET", "POST"),
)
@UI_NS.route(
    "/fork/<username>/<repo>/settings/boards/<board_name>",
    methods=("GET", "POST"),
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/settings/boards/<board_name>/",
    methods=("GET", "POST"),
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/settings/boards/<board_name>",
    methods=("GET", "POST"),
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def view_board_settings(repo, board_name, username=None, namespace=None):
    """Presents and update the settings of the board"""
    project = flask.g.repo

    if not project.boards:
        flask.abort(404)

    board_out = None
    for board in project.boards:
        if board.name == board_name:
            board_out = board
            break

    if board_out is None:
        flask.abort(404)

    return flask.render_template(
        "settings_board.html",
        select="settings",
        repo=project,
        username=username,
        board=board_out,
    )
