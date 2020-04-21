# -*- coding: utf-8 -*-

"""
 (c) 2015-2019 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import flask
import logging

from sqlalchemy.exc import SQLAlchemyError
from six import string_types
from pygit2 import GitError, Repository

try:
    from pygit2 import AlreadyExistsError
except ImportError:
    # Older version of pygit2 do not have the AlreadyExistsError defined
    AlreadyExistsError = ValueError

import pagure
import pagure.forms
import pagure.exceptions
import pagure.lib.git
import pagure.lib.query
import pagure.utils
from pagure.api import (
    API,
    api_method,
    APIERROR,
    api_login_required,
    get_authorized_api_project,
    api_login_optional,
    get_request_data,
    get_page,
    get_per_page,
)
from pagure.api.utils import _get_repo, _check_token, _get_project_tag
from pagure.config import config as pagure_config


_log = logging.getLogger(__name__)


@API.route("/<repo>/tags")
@API.route("/<repo>/tags/")
@API.route("/<namespace>/<repo>/tags")
@API.route("/<namespace>/<repo>/tags/")
@API.route("/fork/<username>/<repo>/tags")
@API.route("/fork/<username>/<repo>/tags/")
@API.route("/fork/<username>/<namespace>/<repo>/tags")
@API.route("/fork/<username>/<namespace>/<repo>/tags/")
@api_method
def api_project_tags(repo, username=None, namespace=None):
    """
    List all the tags of a project
    ------------------------------
    List the tags made on the project's issues.

    ::

        GET /api/0/<repo>/tags
        GET /api/0/<namespace>/<repo>/git/tags

    ::

        GET /api/0/fork/<username>/<repo>/tags
        GET /api/0/fork/<username>/<namespace>/<repo>/tags

    Parameters
    ^^^^^^^^^^

    +---------------+----------+---------------+--------------------------+
    | Key           | Type     | Optionality   | Description              |
    +===============+==========+===============+==========================+
    | ``pattern``   | string   | Optional      | | Filters the starting   |
    |               |          |               |   letters of the tags    |
    +---------------+----------+---------------+--------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "total_tags": 2,
          "tags": ["tag1", "tag2"]
        }

    """

    pattern = flask.request.args.get("pattern", None)
    if pattern is not None and not pattern.endswith("*"):
        pattern += "*"

    project_obj = _get_repo(repo, username, namespace)

    tags = pagure.lib.query.get_tags_of_project(
        flask.g.session, project_obj, pattern=pattern
    )

    return flask.jsonify(
        {"total_tags": len(tags), "tags": [tag.tag for tag in tags]}
    )


@API.route("/<repo>/tag/<tag>", methods=["GET"])
@API.route("/<namespace>/<repo>/tag/<tag>", methods=["GET"])
@API.route("/fork/<username>/<repo>/tag/<tag>", methods=["GET"])
@API.route("/fork/<username>/<namespace>/<repo>/tag/<tag>", methods=["GET"])
@api_method
def api_project_tag_view(repo, tag, username=None, namespace=None):
    """
    View a tag of a project
    -----------------------
    View a tag on project's issues or pull requests.

    ::

        GET /api/0/<repo>/tag/<tag>
        GET /api/0/<repo>/tag/<tag>

    ::
        GET /api/0/fork/<username>/<repo>/tag/<tag>
        GET /api/0/fork/<username>/<namespace>/tag/<tag>

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            "tag": "tag1",
            "tag_color": "DeepBlueSky"
            "tag_description": "Our blue tag"
        }

    """
    repo = _get_repo(repo, username, namespace)
    _check_token(repo, project_token=False)
    tag = _get_project_tag(repo.id, tag)
    output = tag.to_json()

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/tags/new", methods=["POST"])
@API.route("/<namespace>/<repo>/tags/new", methods=["POST"])
@API.route("/fork/<username>/<repo>/tags/new", methods=["POST"])
@API.route("/fork/<username>/<namespace>/<repo>/tags/new", methods=["POST"])
@api_login_required(acls=["modify_project"])
@api_method
def api_project_tags_new(repo, username=None, namespace=None):
    """
    Create a new tag on a project
    ------------------------------

    Create a new tag on the project's issues and pull requests.

    ::

        POST /api/0/<repo>/tags/new
        POST /api/0/<namespace>/<repo>/tags/new

    ::

        POST /api/0/fork/<username>/<repo>/tags/new
        POST /api/0/fork/<username>/<namespace>/<repo>/tags/new

    Input
    ^^^^^

    +-------------------+--------+-------------+---------------------------+
    | Key               | Type   | Optionality | Description               |
    +===================+========+=============+===========================+
    | 'tag'             | string | Mandatory   | The name of the tag       |
    +-------------------+--------+-------------+---------------------------+
    | 'tag_color'       | string | Mandatory   | The color of the tag      |
    +-------------------+--------+-------------+---------------------------+
    | 'tag_description' | string | Optional    | | The description of the  |
    |                   |        |             |   tag                     |
    +-------------------+--------+-------------+---------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            "tag": {
                "tag": "tag1",
                "tag_color": "DeepBlueSky",
                "tag_description": "Our blue tag"
            },
            "message": "Tag created"
        }

    """
    output = {}
    repo = _get_repo(repo, username, namespace)
    _check_token(repo, project_token=False)

    form = pagure.forms.ApiAddIssueTagForm(csrf_enabled=False)
    if form.validate_on_submit():
        tag_name = form.tag.data
        tag_description = form.tag_description.data
        tag_color = form.tag_color.data
        try:
            tag = pagure.lib.query.new_tag(
                flask.g.session, tag_name, tag_description, tag_color, repo.id
            )
            flask.g.session.commit()
            output["message"] = "Tag created"
            output["tag"] = tag.to_json()

        except SQLAlchemyError as err:
            flask.g.session.rollback()
            _log.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors
        )

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/tag/<tag>", methods=["DELETE"])
@API.route("/<namespace>/<repo>/tag/<tag>", methods=["DELETE"])
@API.route("/fork/<username>/<repo>/tag/<tag>", methods=["DELETE"])
@API.route("/fork/<username>/<namespace>/<repo>/tag/<tag>", methods=["DELETE"])
@api_login_required(acls=["modify_project"])
@api_method
def api_project_tag_delete(repo, tag, username=None, namespace=None):
    """
    Delete a tag on a project
    -------------------------

    Delete a tag on project's issues and pull requests.

    ::

        DELETE /api/0/<repo>/tag/<tag>
        DELETE /api/0/<namespace>/<repo>/tag/<tag>

    ::

        DELETE /api/0/fork/<username>/<repo>/tag/<tag>
        DELETE /api/0/fork/<username>/<namespace>/<repo>/tag/<tag>

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            "message": "Tag blue has been deleted"
        }

    """
    output = {}
    repo = _get_repo(repo, username, namespace)
    _check_token(repo)
    tag = _get_project_tag(repo.id, tag)
    tags = tag.tag

    try:
        msgs = pagure.lib.query.remove_tags(
            flask.g.session, repo, tags, user=flask.g.fas_user.username
        )
        flask.g.session.commit()
        output["message"] = msgs[0]
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        _log.exception(err)
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/git/tags")
@API.route("/<namespace>/<repo>/git/tags")
@API.route("/fork/<username>/<repo>/git/tags")
@API.route("/fork/<username>/<namespace>/<repo>/git/tags")
@api_method
def api_git_tags(repo, username=None, namespace=None):
    """
    List git tags
    -------------
    List the tags made on the project Git repository.

    ::

        GET /api/0/<repo>/git/tags
        GET /api/0/<namespace>/<repo>/git/tags

    ::

        GET /api/0/fork/<username>/<repo>/git/tags
        GET /api/0/fork/<username>/<namespace>/<repo>/git/tags

    Parameters
    ^^^^^^^^^^

    +-----------------+----------+---------------+--------------------------+
    | Key             | Type     | Optionality   | Description              |
    +=================+==========+===============+==========================+
    | ``with_commits``| string   | Optional      | | Include the commit hash|
    |                 |          |               |   corresponding to the   |
    |                 |          |               |   tags found in the repo |
    +-----------------+----------+---------------+--------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "total_tags": 2,
          "tags": ["0.0.1", "0.0.2"]
        }


        {
          "total_tags": 2,
          "tags": {
            "0.0.1": "bb8fa2aa199da08d6085e1c9badc3d83d188d38c",
            "0.0.2": "d16fe107eca31a1bdd66fb32c6a5c568e45b627e"
          }
        }

    """
    with_commits = pagure.utils.is_true(
        flask.request.values.get("with_commits", False)
    )

    repo = _get_repo(repo, username, namespace)

    tags = pagure.lib.git.get_git_tags(repo, with_commits=with_commits)

    jsonout = flask.jsonify({"total_tags": len(tags), "tags": tags})
    return jsonout


@API.route("/<repo>/git/tags", methods=["POST"])
@API.route("/<namespace>/<repo>/git/tags", methods=["POST"])
@API.route("/fork/<username>/<repo>/git/tags", methods=["POST"])
@API.route("/fork/<username>/<namespace>/<repo>/git/tags", methods=["POST"])
@api_login_required(acls=["modify_project", "tag_project"])
@api_method
def api_new_git_tags(repo, username=None, namespace=None):
    """
    Create new git tags
    -------------------
    Create a new tag on the project Git repository.
    If the request tried to create a git tag that already existed, the JSON
    returned will include ``"tag_created": false``, otherwise, this field will
    be ``true``.

    ::

        POST /api/0/<repo>/git/tags
        POST /api/0/<namespace>/<repo>/git/tags

    ::

        POST /api/0/fork/<username>/<repo>/git/tags
        POST /api/0/fork/<username>/<namespace>/<repo>/git/tags

    Parameters
    ^^^^^^^^^^

    +-----------------+----------+---------------+--------------------------+
    | Key             | Type     | Optionality   | Description              |
    +=================+==========+===============+==========================+
    | ``tagname``     | string   | Mandatory     | | Name of the tag to     |
    |                 |          |               |   create in the git repo |
    +-----------------+----------+---------------+--------------------------+
    | ``commit_hash`` | string   | Mandatory     | | Hash of the commit/    |
    |                 |          |               |   reference to tag       |
    +-----------------+----------+---------------+--------------------------+
    | ``message``     | string   | Optional      | | Message to include in  |
    |                 |          |               |   the annotation of the  |
    |                 |          |               |   git tag                |
    +-----------------+----------+---------------+--------------------------+
    | ``with_commits``| string   | Optional      | | Include the commit hash|
    |                 |          |               |   corresponding to the   |
    |                 |          |               |   tags found in the repo |
    |                 |          |               |   in the data returned   |
    +-----------------+----------+---------------+--------------------------+
    | ``force``       | boolean  | Optional      | | If a similar git tag   |
    |                 |          |               |   already exists, remove |
    |                 |          |               |   it from the repo and   |
    |                 |          |               |   create the specified   |
    |                 |          |               |   one, thus forcing it   |
    +-----------------+----------+---------------+--------------------------+


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "total_tags": 2,
          "tags": ["0.0.1", "0.0.2"],
          "tag_created": true,
        }


        {
          "total_tags": 2,
          "tags": {
            "0.0.1": "bb8fa2aa199da08d6085e1c9badc3d83d188d38c",
            "0.0.2": "d16fe107eca31a1bdd66fb32c6a5c568e45b627e"
          },
          "tag_created": false,
        }

    """
    repo = _get_repo(repo, username, namespace)
    _check_token(repo, project_token=False)

    with_commits = pagure.utils.is_true(
        flask.request.values.get("with_commits", False)
    )

    form = pagure.forms.AddGitTagForm(csrf_enabled=False)
    created = None
    if form.validate_on_submit():
        user_obj = pagure.lib.query.get_user(
            flask.g.session, flask.g.fas_user.username
        )
        force = form.force.data
        if not pagure_config.get("ALLOW_API_UPDATE_GIT_TAGS", True):
            force = False

        try:
            pagure.lib.git.new_git_tag(
                project=repo,
                tagname=form.tagname.data,
                target=form.commit_hash.data,
                user=user_obj,
                message=form.message.data,
                force=force,
            )
            created = True
        except AlreadyExistsError:
            created = False
        except GitError as err:
            _log.exception(err)
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EGITERROR, error=str(err)
            )

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors
        )

    tags = pagure.lib.git.get_git_tags(repo, with_commits=with_commits)

    jsonout = flask.jsonify(
        {"total_tags": len(tags), "tags": tags, "tag_created": created}
    )
    return jsonout


@API.route("/<repo>/watchers")
@API.route("/<namespace>/<repo>/watchers")
@API.route("/fork/<username>/<repo>/watchers")
@API.route("/fork/<username>/<namespace>/<repo>/watchers")
@api_method
def api_project_watchers(repo, username=None, namespace=None):
    """
    Project watchers
    ----------------
    List the watchers on the project.

    ::

        GET /api/0/<repo>/watchers
        GET /api/0/<namespace>/<repo>/watchers

    ::

        GET /api/0/fork/<username>/<repo>/watchers
        GET /api/0/fork/<username>/<namespace>/<repo>/watchers

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            "total_watchers": 1,
            "watchers": {
                "mprahl": [
                    "issues",
                    "commits"
                ]
            }
        }
    """
    repo = _get_repo(repo, username, namespace)

    implicit_watch_users = set([repo.user.username])
    for access_type in repo.access_users:
        implicit_watch_users = implicit_watch_users.union(
            set([user.username for user in repo.access_users[access_type]])
        )

    watching_users_to_watch_level = {}
    for implicit_watch_user in implicit_watch_users:
        user_watch_level = pagure.lib.query.get_watch_level_on_repo(
            flask.g.session, implicit_watch_user, repo
        )
        watching_users_to_watch_level[implicit_watch_user] = user_watch_level

    for access_type in repo.access_groups.keys():
        group_names = [
            "@" + group.group_name for group in repo.access_groups[access_type]
        ]
        for group_name in group_names:
            if group_name not in watching_users_to_watch_level:
                watching_users_to_watch_level[group_name] = set()
            # By the logic in pagure.lib.query.get_watch_level_on_repo, group
            # members only by default watch issues.  If they want to watch
            # commits they have to explicitly subscribe.
            watching_users_to_watch_level[group_name].add("issues")

    for key in watching_users_to_watch_level:
        watching_users_to_watch_level[key] = list(
            watching_users_to_watch_level[key]
        )

    # Get the explicit watch statuses
    for watcher in repo.watchers:
        if watcher.watch_issues or watcher.watch_commits:
            watching_users_to_watch_level[
                watcher.user.username
            ] = pagure.lib.query.get_watch_level_on_repo(
                flask.g.session, watcher.user.username, repo
            )
        else:
            if watcher.user.username in watching_users_to_watch_level:
                watching_users_to_watch_level.pop(watcher.user.username, None)

    return flask.jsonify(
        {
            "total_watchers": len(watching_users_to_watch_level),
            "watchers": watching_users_to_watch_level,
        }
    )


@API.route("/<repo>/git/urls")
@API.route("/<namespace>/<repo>/git/urls")
@API.route("/fork/<username>/<repo>/git/urls")
@API.route("/fork/<username>/<namespace>/<repo>/git/urls")
@api_login_optional()
@api_method
def api_project_git_urls(repo, username=None, namespace=None):
    """
    Project Git URLs
    ----------------
    List the Git URLS on the project.

    ::

        GET /api/0/<repo>/git/urls
        GET /api/0/<namespace>/<repo>/git/urls

    ::

        GET /api/0/fork/<username>/<repo>/git/urls
        GET /api/0/fork/<username>/<namespace>/<repo>/git/urls

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            "total_urls": 2,
            "urls": {
                "ssh": "ssh://git@pagure.io/mprahl-test123.git",
                "git": "https://pagure.io/mprahl-test123.git"
            }
        }
    """
    repo = _get_repo(repo, username, namespace)

    git_urls = {}
    git_url_ssh = pagure_config.get("GIT_URL_SSH")
    if pagure.utils.api_authenticated() and git_url_ssh:
        try:
            git_url_ssh = git_url_ssh.format(
                username=flask.g.fas_user.username
            )
        except (KeyError, IndexError):
            pass

    if git_url_ssh:
        git_urls["ssh"] = "{0}{1}.git".format(git_url_ssh, repo.fullname)
    if pagure_config.get("GIT_URL_GIT"):
        git_urls["git"] = "{0}{1}.git".format(
            pagure_config["GIT_URL_GIT"], repo.fullname
        )

    return flask.jsonify({"total_urls": len(git_urls), "urls": git_urls})


@API.route("/<repo>/git/branches")
@API.route("/<namespace>/<repo>/git/branches")
@API.route("/fork/<username>/<repo>/git/branches")
@API.route("/fork/<username>/<namespace>/<repo>/git/branches")
@api_method
def api_git_branches(repo, username=None, namespace=None):
    """
    List git branches
    -----------------
    List the branches associated with a Pagure git repository

    ::

        GET /api/0/<repo>/git/branches
        GET /api/0/<namespace>/<repo>/git/branches

    ::

        GET /api/0/fork/<username>/<repo>/git/branches
        GET /api/0/fork/<username>/<namespace>/<repo>/git/branches

    Parameters
    ^^^^^^^^^^

    +-----------------+----------+---------------+--------------------------+
    | Key             | Type     | Optionality   | Description              |
    +=================+==========+===============+==========================+
    | ``with_commits``| boolean  | Optional      | | Include the commit hash|
    |                 |          |               |   corresponding to the   |
    |                 |          |               |   HEAD of each branch    |
    +-----------------+----------+---------------+--------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "total_branches": 2,
          "branches": ["master", "dev"]
        }

        {
          "total_branches": 2,
          "branches": {
            "master": "16ae2a4df107658b52750063ae203f978cf02ff7",
            "dev": "8351c460167a41defc393f5b6c1d51fe1b3b82b8"
          }
        }

    """

    with_commits = pagure.utils.is_true(
        flask.request.values.get("with_commits", False)
    )

    repo = _get_repo(repo, username, namespace)

    branches = pagure.lib.git.get_git_branches(repo, with_commits=with_commits)

    return flask.jsonify(
        {"total_branches": len(branches), "branches": branches}
    )


@API.route("/projects")
@api_method
def api_projects():
    """
    List projects
    --------------
    Search projects given the specified criterias.

    ::

        GET /api/0/projects

    ::

        GET /api/0/projects?tags=fedora-infra

    ::

        GET /api/0/projects?page=1&per_page=50

    Parameters
    ^^^^^^^^^^

    +---------------+----------+---------------+--------------------------+
    | Key           | Type     | Optionality   | Description              |
    +===============+==========+===============+==========================+
    | ``tags``      | string   | Optional      | | Filters the projects   |
    |               |          |               |   returned by their tags |
    +---------------+----------+---------------+--------------------------+
    | ``pattern``   | string   | Optional      | | Filters the projects   |
    |               |          |               |   by the pattern string  |
    +---------------+----------+---------------+--------------------------+
    | ``username``  | string   | Optional      | | Filters the projects   |
    |               |          |               |   returned by the users  |
    |               |          |               |   having commit rights   |
    |               |          |               |   to it                  |
    +---------------+----------+---------------+--------------------------+
    | ``owner``     | string   | Optional      | | Filters the projects   |
    |               |          |               |   by ownership.          |
    |               |          |               |   If the argument is of  |
    |               |          |               |   the form <!owner> then |
    |               |          |               |   the project returned   |
    |               |          |               |   are the ones *not*     |
    |               |          |               |   owned by this user.    |
    +---------------+----------+---------------+--------------------------+
    | ``namespace`` | string   | Optional      | | Filters the projects   |
    |               |          |               |   by namespace           |
    +---------------+----------+---------------+--------------------------+
    | ``fork``      | boolean  | Optional      | | Filters the projects   |
    |               |          |               |   returned depending if  |
    |               |          |               |   they are forks or not  |
    +---------------+----------+---------------+--------------------------+
    | ``short``     | boolean  | Optional      | | Whether to return the  |
    |               |          |               |   entrie project JSON    |
    |               |          |               |   or just a sub-set      |
    +---------------+----------+---------------+--------------------------+
    | ``page``      | int      | Optional      | | Specifies which        |
    |               |          |               |   page to return         |
    |               |          |               |   (defaults to: 1)       |
    +---------------+----------+---------------+--------------------------+
    | ``per_page``  | int      | Optional      | | The number of projects |
    |               |          |               |   to return per page.    |
    |               |          |               |   The maximum is 100.    |
    +---------------+----------+---------------+--------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "args": {
            "fork": null,
            "namespace": null,
            "owner": null,
            "page": 1,
            "pattern": null,
            "per_page": 2,
            "short": false,
            "tags": [],
            "username": null
          },
          "pagination": {
            "first": "http://127.0.0.1:5000/api/0/projects?per_page=2&page=1",
            "last": "http://127.0.0.1:5000/api/0/projects?per_page=2&page=500",
            "next": "http://127.0.0.1:5000/api/0/projects?per_page=2&page=2",
            "page": 1,
            "pages": 500,
            "per_page": 2,
            "prev": null
          },
          "projects": [
            {
              "access_groups": {
                "admin": [],
                "commit": [],
                "ticket": []
              },
              "access_users": {
                "admin": [],
                "commit": [],
                "owner": [
                  "mprahl"
                ],
                "ticket": []
              },
              "close_status": [],
              "custom_keys": [],
              "date_created": "1498841289",
              "description": "test1",
              "fullname": "test1",
              "id": 1,
              "milestones": {},
              "name": "test1",
              "namespace": null,
              "parent": null,
              "priorities": {},
              "tags": [],
              "url_path": "test1",
              "user": {
                "fullname": "Matt Prahl",
                "name": "mprahl"
              }
            },
            {
              "access_groups": {
                "admin": [],
                "commit": [],
                "ticket": []
              },
              "access_users": {
                "admin": [],
                "commit": [],
                "owner": [
                  "mprahl"
                ],
                "ticket": []
              },
              "close_status": [],
              "custom_keys": [],
              "date_created": "1499795310",
              "description": "test2",
              "fullname": "test2",
              "id": 2,
              "milestones": {},
              "name": "test2",
              "namespace": null,
              "parent": null,
              "priorities": {},
              "tags": [],
              "url_path": "test2",
              "user": {
                "fullname": "Matt Prahl",
                "name": "mprahl"
              }
            }
          ],
          "total_projects": 1000
        }
    """
    tags = flask.request.values.getlist("tags")
    username = flask.request.values.get("username", None)
    fork = flask.request.values.get("fork", None)
    namespace = flask.request.values.get("namespace", None)
    owner = flask.request.values.get("owner", None)
    pattern = flask.request.values.get("pattern", None)
    short = pagure.utils.is_true(flask.request.values.get("short", False))

    if fork is not None:
        fork = pagure.utils.is_true(fork)

    private = False
    if pagure.utils.authenticated() and username == flask.g.fas_user.username:
        private = flask.g.fas_user.username

    project_count = pagure.lib.query.search_projects(
        flask.g.session,
        username=username,
        fork=fork,
        tags=tags,
        pattern=pattern,
        private=private,
        namespace=namespace,
        owner=owner,
        count=True,
    )

    # Pagination code inspired by Flask-SQLAlchemy
    page = get_page()
    per_page = get_per_page()
    pagination_metadata = pagure.lib.query.get_pagination_metadata(
        flask.request, page, per_page, project_count
    )
    query_start = (page - 1) * per_page
    query_limit = per_page

    projects = pagure.lib.query.search_projects(
        flask.g.session,
        username=username,
        fork=fork,
        tags=tags,
        pattern=pattern,
        private=private,
        namespace=namespace,
        owner=owner,
        limit=query_limit,
        start=query_start,
    )

    # prepare the output json
    jsonout = {
        "total_projects": project_count,
        "projects": projects,
        "args": {
            "tags": tags,
            "username": username,
            "fork": fork,
            "pattern": pattern,
            "namespace": namespace,
            "owner": owner,
            "short": short,
        },
    }

    if not short:
        projects = [p.to_json(api=True, public=True) for p in projects]
    else:
        projects = [
            {
                "name": p.name,
                "namespace": p.namespace,
                "fullname": p.fullname.replace("forks/", "fork/", 1)
                if p.fullname.startswith("forks/")
                else p.fullname,
                "description": p.description,
            }
            for p in projects
        ]

    jsonout["projects"] = projects
    if pagination_metadata:
        jsonout["args"]["page"] = page
        jsonout["args"]["per_page"] = per_page
        jsonout["pagination"] = pagination_metadata
    return flask.jsonify(jsonout)


@API.route("/<repo>")
@API.route("/<namespace>/<repo>")
@API.route("/fork/<username>/<repo>")
@API.route("/fork/<username>/<namespace>/<repo>")
@api_method
def api_project(repo, username=None, namespace=None):
    """
    Project information
    -------------------
    Return information about a specific project

    ::

        GET /api/0/<repo>
        GET /api/0/<namespace>/<repo>

    ::

        GET /api/0/fork/<username>/<repo>
        GET /api/0/fork/<username>/<namespace>/<repo>

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "access_groups": {
            "admin": [],
            "commit": [],
            "ticket": []
          },
          "access_users": {
            "admin": [
              "ryanlerch"
            ],
            "commit": [
              "puiterwijk"
            ],
            "owner": [
              "pingou"
            ],
            "ticket": [
              "vivekanand1101",
              "mprahl",
              "jcline",
              "lslebodn",
              "cverna",
              "farhaan"
            ]
          },
          "close_status": [
            "Invalid",
            "Insufficient data",
            "Fixed",
            "Duplicate"
          ],
          "custom_keys": [],
          "date_created": "1431549490",
          "date_modified": "1431549490",
          "description": "A git centered forge",
          "fullname": "pagure",
          "id": 10,
          "milestones": {},
          "name": "pagure",
          "namespace": null,
          "parent": null,
          "priorities": {},
          "tags": [
            "pagure",
            "fedmsg"
          ],
          "user": {
            "fullname": "Pierre-YvesChibon",
            "name": "pingou"
          }
        }

    """
    repo = _get_repo(repo, username, namespace)

    expand_group = pagure.utils.is_true(
        flask.request.values.get("expand_group", False)
    )

    output = repo.to_json(api=True, public=True)

    if expand_group:
        group_details = {}
        for grp in repo.projects_groups:
            group_details[grp.group.group_name] = [
                user.username for user in grp.group.users
            ]
        output["group_details"] = group_details

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/new/", methods=["POST"])
@API.route("/new", methods=["POST"])
@api_login_required(acls=["create_project"])
@api_method
def api_new_project():
    """
    Create a new project
    --------------------
    Create a new project on this pagure instance.

    This is an asynchronous call.

    ::

        POST /api/0/new


    Input
    ^^^^^

    +----------------------------+---------+--------------+---------------------------+
    | Key                        | Type    | Optionality  | Description               |
    +============================+=========+==============+===========================+
    | ``name``                   | string  | Mandatory    | | The name of the new     |
    |                            |         |              |   project.                |
    +----------------------------+---------+--------------+---------------------------+
    | ``description``            | string  | Mandatory    | | A short description of  |
    |                            |         |              |   the new project.        |
    +----------------------------+---------+--------------+---------------------------+
    | ``namespace``              | string  | Optional     | | The namespace of the    |
    |                            |         |              |   project to fork.        |
    +----------------------------+---------+--------------+---------------------------+
    | ``url``                    | string  | Optional     | | An url providing more   |
    |                            |         |              |   information about the   |
    |                            |         |              |   project.                |
    +----------------------------+---------+--------------+---------------------------+
    | ``avatar_email``           | string  | Optional     | | An email address for the|
    |                            |         |              |   avatar of the project.  |
    +----------------------------+---------+--------------+---------------------------+
    | ``create_readme``          | boolean | Optional     | | A boolean to specify if |
    |                            |         |              |   there should be a readme|
    |                            |         |              |   added to the project on |
    |                            |         |              |   creation.               |
    +----------------------------+---------+--------------+---------------------------+
    | ``private``                | boolean | Optional     | | A boolean to specify if |
    |                            |         |              |   the project to create   |
    |                            |         |              |   is private.             |
    |                            |         |              |   Note: not all pagure    |
    |                            |         |              |   instance support private|
    |                            |         |              |   projects, confirm this  |
    |                            |         |              |   with your administrators|
    +----------------------------+---------+--------------+---------------------------+
    | ``ignore_existing_repos``  | boolean | Optional     | | Only available to admins|
    |                            |         |              |   this option allows them |
    |                            |         |              |   to make project creation|
    |                            |         |              |   pass even if there is   |
    |                            |         |              |   already a coresopnding  |
    |                            |         |              |   git repository on disk  |
    +----------------------------+---------+--------------+---------------------------+
    | ``repospanner_region``     | boolean | Optional     | | Only available to admins|
    |                            |         |              |   this option allows them |
    |                            |         |              |   to override the default |
    |                            |         |              |   respoSpanner region     |
    |                            |         |              |   configured              |
    +----------------------------+---------+--------------+---------------------------+
    | ``wait``                   | boolean | Optional     | | A boolean to specify if |
    |                            |         |              |   this API call should    |
    |                            |         |              |   return a taskid or if it|
    |                            |         |              |   should wait for the task|
    |                            |         |              |   to finish.              |
    +----------------------------+---------+--------------+---------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        wait=False:
        {
          'message': 'Project creation queued',
          'taskid': '123-abcd'
        }

        wait=True:
        {
          'message': 'Project creation queued'
        }

    """  # noqa
    user = pagure.lib.query.search_user(
        flask.g.session, username=flask.g.fas_user.username
    )
    output = {}

    if not pagure_config.get("ENABLE_NEW_PROJECTS", True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENEWPROJECTDISABLED
        )

    namespaces = pagure_config["ALLOWED_PREFIX"][:]
    if user:
        namespaces.extend([grp for grp in user.groups])

    form = pagure.forms.ProjectForm(namespaces=namespaces, csrf_enabled=False)
    if form.validate_on_submit():
        name = form.name.data
        description = form.description.data
        namespace = form.namespace.data
        url = form.url.data
        avatar_email = form.avatar_email.data
        create_readme = form.create_readme.data

        if namespace:
            namespace = namespace.strip()

        private = False
        if pagure_config.get("PRIVATE_PROJECTS", False):
            private = form.private.data
        if form.repospanner_region:
            repospanner_region = form.repospanner_region.data
        else:
            repospanner_region = None
        if form.ignore_existing_repos:
            ignore_existing_repos = form.ignore_existing_repos.data
        else:
            ignore_existing_repos = False

        try:
            task = pagure.lib.query.new_project(
                flask.g.session,
                name=name,
                namespace=namespace,
                repospanner_region=repospanner_region,
                ignore_existing_repo=ignore_existing_repos,
                description=description,
                private=private,
                url=url,
                avatar_email=avatar_email,
                user=flask.g.fas_user.username,
                blacklist=pagure_config["BLACKLISTED_PROJECTS"],
                allowed_prefix=pagure_config["ALLOWED_PREFIX"],
                add_readme=create_readme,
                userobj=user,
                prevent_40_chars=pagure_config.get(
                    "OLD_VIEW_COMMIT_ENABLED", False
                ),
                user_ns=pagure_config.get("USER_NAMESPACE", False),
            )
            flask.g.session.commit()
            output = {"message": "Project creation queued", "taskid": task.id}

            if get_request_data().get("wait", True):
                result = task.get()
                project = pagure.lib.query._get_project(
                    flask.g.session,
                    name=result["repo"],
                    namespace=result["namespace"],
                )
                output = {"message": 'Project "%s" created' % project.fullname}
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


@API.route("/<repo>", methods=["PATCH"])
@API.route("/<namespace>/<repo>", methods=["PATCH"])
@api_login_required(acls=["modify_project"])
@api_method
def api_modify_project(repo, namespace=None):
    """
    Modify a project
    ----------------
    Modify an existing project on this Pagure instance.

    ::

        PATCH /api/0/<repo>


    Input
    ^^^^^

    +------------------+---------+--------------+---------------------------+
    | Key              | Type    | Optionality  | Description               |
    +==================+=========+==============+===========================+
    | ``main_admin``   | string  | Mandatory    | | The new main admin of   |
    |                  |         |              |   the project.            |
    +------------------+---------+--------------+---------------------------+
    | ``retain_access``| string  | Optional     | | The old main admin      |
    |                  |         |              |   retains access on the   |
    |                  |         |              |   project when giving the |
    |                  |         |              |   project. Defaults to    |
    |                  |         |              |   ``False``.              |
    +------------------+---------+--------------+---------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "access_groups": {
            "admin": [],
            "commit": [],
            "ticket": []
          },
          "access_users": {
            "admin": [],
            "commit": [],
            "owner": [
              "testuser1"
            ],
            "ticket": []
          },
          "close_status": [],
          "custom_keys": [],
          "date_created": "1496326387",
          "description": "Test",
          "fullname": "test-project2",
          "id": 2,
          "milestones": {},
          "name": "test-project2",
          "namespace": null,
          "parent": null,
          "priorities": {},
          "tags": [],
          "user": {
            "default_email": "testuser1@domain.local",
            "emails": [],
            "fullname": "Test User1",
            "name": "testuser1"
          }
        }

    """
    project = _get_repo(repo, namespace=namespace)
    _check_token(project, project_token=False)

    is_site_admin = pagure.utils.is_admin()
    admins = [u.username for u in project.get_project_users("admin")]
    # Only allow the main admin, the admins of the project, and Pagure site
    # admins to modify projects, even if the user has the right ACLs on their
    # token
    if (
        flask.g.fas_user.username not in admins
        and flask.g.fas_user.username != project.user.username
        and not is_site_admin
    ):
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.EMODIFYPROJECTNOTALLOWED
        )

    valid_keys = ["main_admin", "retain_access"]
    # Check if it's JSON or form data
    if flask.request.headers.get("Content-Type") == "application/json":
        # Set force to True to ignore the mimetype. Set silent so that None is
        # returned if it's invalid JSON.
        args = flask.request.get_json(force=True, silent=True) or {}
        retain_access = args.get("retain_access", False)
    else:
        args = get_request_data()
        retain_access = args.get("retain_access", "").lower() in ["true", "1"]

    if not args:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    # Check to make sure there aren't parameters we don't support
    for key in args.keys():
        if key not in valid_keys:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EINVALIDREQ
            )

    if "main_admin" in args:
        if (
            flask.g.fas_user.username != project.user.username
            and not is_site_admin
        ):
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.ENOTMAINADMIN
            )
        # If the main_admin is already set correctly, don't do anything
        if flask.g.fas_user.username == project.user:
            return flask.jsonify(project.to_json(public=False, api=True))

        try:
            new_main_admin = pagure.lib.query.get_user(
                flask.g.session, args["main_admin"]
            )
        except pagure.exceptions.PagureException:
            raise pagure.exceptions.APIError(400, error_code=APIERROR.ENOUSER)

        old_main_admin = project.user.user
        pagure.lib.query.set_project_owner(
            flask.g.session, project, new_main_admin
        )
        if retain_access and flask.g.fas_user.username == old_main_admin:
            pagure.lib.query.add_user_to_project(
                flask.g.session,
                project,
                new_user=flask.g.fas_user.username,
                user=flask.g.fas_user.username,
            )

    try:
        flask.g.session.commit()
    except SQLAlchemyError:  # pragma: no cover
        flask.g.session.rollback()
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    pagure.lib.git.generate_gitolite_acls(project=project)

    return flask.jsonify(project.to_json(public=False, api=True))


@API.route("/fork/", methods=["POST"])
@API.route("/fork", methods=["POST"])
@api_login_required(acls=["fork_project"])
@api_method
def api_fork_project():
    """
    Fork a project
    --------------------
    Fork a project on this pagure instance.

    This is an asynchronous call.

    ::

        POST /api/0/fork


    Input
    ^^^^^

    +------------------+---------+--------------+---------------------------+
    | Key              | Type    | Optionality  | Description               |
    +==================+=========+==============+===========================+
    | ``repo``         | string  | Mandatory    | | The name of the project |
    |                  |         |              |   to fork.                |
    +------------------+---------+--------------+---------------------------+
    | ``namespace``    | string  | Optional     | | The namespace of the    |
    |                  |         |              |   project to fork.        |
    +------------------+---------+--------------+---------------------------+
    | ``username``     | string  | Optional     | | The username of the user|
    |                  |         |              |   of the fork.            |
    +------------------+---------+--------------+---------------------------+
    | ``wait``         | boolean | Optional     | | A boolean to specify if |
    |                  |         |              |   this API call should    |
    |                  |         |              |   return a taskid or if it|
    |                  |         |              |   should wait for the task|
    |                  |         |              |   to finish.              |
    +------------------+---------+--------------+---------------------------+


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        wait=False:
        {
          "message": "Project forking queued",
          "taskid": "123-abcd"
        }

        wait=True:
        {
          "message": 'Repo "test" cloned to "pingou/test"
        }

    """
    output = {}

    form = pagure.forms.ForkRepoForm(csrf_enabled=False)
    if form.validate_on_submit():
        repo = form.repo.data
        username = form.username.data or None
        namespace = form.namespace.data.strip() or None

        repo = get_authorized_api_project(
            flask.g.session, repo, user=username, namespace=namespace
        )
        if repo is None:
            raise pagure.exceptions.APIError(
                404, error_code=APIERROR.ENOPROJECT
            )

        try:
            task = pagure.lib.query.fork_project(
                flask.g.session, user=flask.g.fas_user.username, repo=repo
            )
            flask.g.session.commit()
            output = {"message": "Project forking queued", "taskid": task.id}

            if get_request_data().get("wait", True):
                task.get()
                output = {
                    "message": 'Repo "%s" cloned to "%s/%s"'
                    % (repo.fullname, flask.g.fas_user.username, repo.fullname)
                }
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


@API.route("/<repo>/git/generateacls", methods=["POST"])
@API.route("/<namespace>/<repo>/git/generateacls", methods=["POST"])
@API.route("/fork/<username>/<repo>/git/generateacls", methods=["POST"])
@API.route(
    "/fork/<username>/<namespace>/<repo>/git/generateacls", methods=["POST"]
)
@api_login_required(acls=["generate_acls_project"])
@api_method
def api_generate_acls(repo, username=None, namespace=None):
    """
    Generate Gitolite ACLs on a project
    -----------------------------------
    Generate Gitolite ACLs on a project. This is restricted to Pagure admins.

    This is an asynchronous call.

    ::

        POST /api/0/rpms/python-requests/git/generateacls


    Input
    ^^^^^

    +------------------+---------+--------------+---------------------------+
    | Key              | Type    | Optionality  | Description               |
    +==================+=========+==============+===========================+
    | ``wait``         | boolean | Optional     | | A boolean to specify if |
    |                  |         |              |   this API call should    |
    |                  |         |              |   return a taskid or if it|
    |                  |         |              |   should wait for the task|
    |                  |         |              |   to finish.              |
    +------------------+---------+--------------+---------------------------+


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        wait=False:
        {
          'message': 'Project ACL generation queued',
          'taskid': '123-abcd'
        }

        wait=True:
        {
          'message': 'Project ACLs generated'
        }

    """
    project = _get_repo(repo, username, namespace)
    _check_token(project, project_token=False)

    # Check if it's JSON or form data
    if flask.request.headers.get("Content-Type") == "application/json":
        # Set force to True to ignore the mimetype. Set silent so that None is
        # returned if it's invalid JSON.
        json = flask.request.get_json(force=True, silent=True) or {}
        wait = json.get("wait", False)
    else:
        wait = pagure.utils.is_true(get_request_data().get("wait"))

    try:
        task = pagure.lib.git.generate_gitolite_acls(project=project)

        if wait:
            task.get()
            output = {"message": "Project ACLs generated"}
        else:
            output = {
                "message": "Project ACL generation queued",
                "taskid": task.id,
            }
    except pagure.exceptions.PagureException as err:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(err)
        )

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/git/branch", methods=["POST"])
@API.route("/<namespace>/<repo>/git/branch", methods=["POST"])
@API.route("/fork/<username>/<repo>/git/branch", methods=["POST"])
@API.route("/fork/<username>/<namespace>/<repo>/git/branch", methods=["POST"])
@api_login_required(acls=["create_branch"])
@api_method
def api_new_branch(repo, username=None, namespace=None):
    """
    Create a new git branch
    -----------------------
    Create a new git branch on a project

    ::

        POST /api/0/rpms/python-requests/git/branch


    Input
    ^^^^^

    +------------------+---------+--------------+---------------------------+
    | Key              | Type    | Optionality  | Description               |
    +==================+=========+==============+===========================+
    | ``branch``       | string  | Mandatory    | | A string of the branch  |
    |                  |         |              |   to create.              |
    +------------------+---------+--------------+---------------------------+
    | ``from_branch``  | string  | Optional     | | A string of the branch  |
    |                  |         |              |   to branch off of. This  |
    |                  |         |              |   defaults to "master".   |
    |                  |         |              |   if ``from_commit``      |
    |                  |         |              |   isn't set.              |
    +------------------+---------+--------------+---------------------------+
    | ``from_commit``  | string  | Optional     | | A string of the commit  |
    |                  |         |              |   to branch off of.       |
    +------------------+---------+--------------+---------------------------+


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          'message': 'Project branch was created'
        }

    """
    project = _get_repo(repo, username, namespace)
    _check_token(project, project_token=False)

    # Check if it's JSON or form data
    if flask.request.headers.get("Content-Type") == "application/json":
        # Set force to True to ignore the mimetype. Set silent so that None is
        # returned if it's invalid JSON.
        args = flask.request.get_json(force=True, silent=True) or {}
    else:
        args = get_request_data()

    branch = args.get("branch")
    from_branch = args.get("from_branch")
    from_commit = args.get("from_commit")

    if from_branch and from_commit:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    if (
        not branch
        or not isinstance(branch, string_types)
        or (from_branch and not isinstance(from_branch, string_types))
        or (from_commit and not isinstance(from_commit, string_types))
    ):
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    try:
        pagure.lib.git.new_git_branch(
            flask.g.fas_user.username,
            project,
            branch,
            from_branch=from_branch,
            from_commit=from_commit,
        )
    except GitError:  # pragma: no cover
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EGITERROR)
    except pagure.exceptions.PagureException as error:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(error)
        )

    output = {"message": "Project branch was created"}
    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/c/<commit_hash>/flag")
@API.route("/<namespace>/<repo>/c/<commit_hash>/flag")
@API.route("/fork/<username>/<repo>/c/<commit_hash>/flag")
@API.route("/fork/<username>/<namespace>/<repo>/c/<commit_hash>/flag")
@api_method
def api_commit_flags(repo, commit_hash, username=None, namespace=None):
    """
    Flags for a commit
    ------------------
    Return all flags for given commit of given project

    ::

        GET /api/0/<repo>/c/<commit_hash>/flag
        GET /api/0/<namespace>/<repo>/c/<commit_hash>/flag

    ::

        GET /api/0/fork/<username>/<repo>/c/<commit_hash>/flag
        GET /api/0/fork/<username>/<namespace>/<repo>/c/<commit_hash>/flag

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "flags": [
            {
              "comment": "flag-comment",
              "commit_hash": "28f1f7fe844301f0e5f7aecacae0a1e5ec50a090",
              "date_created": "1520341983",
              "percent": null,
              "status": "success",
              "url": "https://some.url.com",
              "user": {
                "fullname": "Full name",
                "name": "fname"
              },
              "username": "somename"
            },
            {
              "comment": "different-comment",
              "commit_hash": "28f1f7fe844301f0e5f7aecacae0a1e5ec50a090",
              "date_created": "1520512543",
              "percent": null,
              "status": "pending",
              "url": "https://other.url.com",
              "user": {
                "fullname": "Other Name",
                "name": "oname"
              },
              "username": "differentname"
            }
          ],
          "total_flags": 2
        }

    """
    repo = _get_repo(repo, username, namespace)

    reponame = pagure.utils.get_repo_path(repo)
    repo_obj = Repository(reponame)
    try:
        repo_obj.get(commit_hash)
    except ValueError:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOCOMMIT)

    flags = pagure.lib.query.get_commit_flag(
        flask.g.session, repo, commit_hash
    )
    flags = [f.to_json(public=True) for f in flags]
    return flask.jsonify({"total_flags": len(flags), "flags": flags})


@API.route("/<repo>/c/<commit_hash>/flag", methods=["POST"])
@API.route("/<namespace>/<repo>/c/<commit_hash>/flag", methods=["POST"])
@API.route("/fork/<username>/<repo>/c/<commit_hash>/flag", methods=["POST"])
@API.route(
    "/fork/<username>/<namespace>/<repo>/c/<commit_hash>/flag",
    methods=["POST"],
)
@api_login_required(acls=["commit_flag"])
@api_method
def api_commit_add_flag(repo, commit_hash, username=None, namespace=None):
    """
    Flag a commit
    -------------------
    Add or edit flags on a commit.

    ::

        POST /api/0/<repo>/c/<commit_hash>/flag
        POST /api/0/<namespace>/<repo>/c/<commit_hash>/flag

    ::

        POST /api/0/fork/<username>/<repo>/c/<commit_hash>/flag
        POST /api/0/fork/<username>/<namespace>/<repo>/c/<commit_hash>/flag

    Input
    ^^^^^

    +---------------+---------+--------------+-----------------------------+
    | Key           | Type    | Optionality  | Description                 |
    +===============+=========+==============+=============================+
    | ``username``  | string  | Mandatory    | | The name of the           |
    |               |         |              |   application to be         |
    |               |         |              |   presented to users        |
    |               |         |              |   on the commit pages       |
    +---------------+---------+--------------+-----------------------------+
    | ``comment``   | string  | Mandatory    | | A short message           |
    |               |         |              |   summarizing the           |
    |               |         |              |   presented results         |
    +---------------+---------+--------------+-----------------------------+
    | ``url``       | string  | Mandatory    | | A URL to the result       |
    |               |         |              |   of this flag              |
    +---------------+---------+--------------+-----------------------------+
    | ``status``    | string  | Mandatory    | | The status of the task,   |
    |               |         |              |   can be any of:            |
    |               |         |              |   $$FLAG_STATUSES_COMMAS$$  |
    +---------------+---------+--------------+-----------------------------+
    | ``percent``   | int     | Optional     | | A percentage of           |
    |               |         |              |   completion compared to    |
    |               |         |              |   the goal. The percentage  |
    |               |         |              |   also determine the        |
    |               |         |              |   background color of the   |
    |               |         |              |   flag on the pages         |
    +---------------+---------+--------------+-----------------------------+
    | ``uid``       | string  | Optional     | | A unique identifier used  |
    |               |         |              |   to identify a flag across |
    |               |         |              |   all projects. If the      |
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
              "comment": "Tests passed",
              "commit_hash": "62b49f00d489452994de5010565fab81",
              "date_created": "1510742565",
              "percent": 100,
              "status": "success",
              "url": "http://jenkins.cloud.fedoraproject.org/",
              "user": {
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com", "foo@pingou.com"],
                "fullname": "PY C",
                "name": "pingou"},
              "username": "Jenkins"
            },
            "message": "Flag added",
            "uid": "b1de8f80defd4a81afe2e09f39678087"
        }

    ::

        {
          "flag": {
              "comment": "Tests passed",
              "commit_hash": "62b49f00d489452994de5010565fab81",
              "date_created": "1510742565",
              "percent": 100,
              "status": "success",
              "url": "http://jenkins.cloud.fedoraproject.org/",
              "user": {
                "default_email": "bar@pingou.com",
                "emails": ["bar@pingou.com", "foo@pingou.com"],
                "fullname": "PY C",
                "name": "pingou"},
              "username": "Jenkins"
            },
            "message": "Flag updated",
            "uid": "b1de8f80defd4a81afe2e09f39678087"
        }

    """  # noqa

    repo = _get_repo(repo, username, namespace)
    _check_token(repo, project_token=False)

    output = {}

    reponame = pagure.utils.get_repo_path(repo)
    repo_obj = Repository(reponame)
    try:
        repo_obj.get(commit_hash)
    except ValueError:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOCOMMIT)

    form = pagure.forms.AddPullRequestFlagForm(csrf_enabled=False)
    if form.validate_on_submit():
        username = form.username.data
        percent = form.percent.data.strip() or None
        comment = form.comment.data.strip()
        url = form.url.data.strip()
        uid = form.uid.data.strip() if form.uid.data else None
        status = form.status.data.strip()
        try:
            # New Flag
            message, uid = pagure.lib.query.add_commit_flag(
                session=flask.g.session,
                repo=repo,
                commit_hash=commit_hash,
                username=username,
                percent=percent,
                comment=comment,
                status=status,
                url=url,
                uid=uid,
                user=flask.g.fas_user.username,
                token=flask.g.token.id,
            )
            flask.g.session.commit()
            c_flag = pagure.lib.query.get_commit_flag_by_uid(
                flask.g.session, commit_hash, uid
            )
            output["message"] = message
            output["uid"] = uid
            output["flag"] = c_flag.to_json()
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err)
            )
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)
    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors
        )

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/watchers/update", methods=["POST"])
@API.route("/<namespace>/<repo>/watchers/update", methods=["POST"])
@API.route("/fork/<username>/<repo>/watchers/update", methods=["POST"])
@API.route(
    "/fork/<username>/<namespace>/<repo>/watchers/update", methods=["POST"]
)
@api_login_required(acls=["update_watch_status"])
@api_method
def api_update_project_watchers(repo, username=None, namespace=None):
    """
    Update project watchers
    -----------------------
    Allows anyone to update their own watch status on the project.

    ::

        POST /api/0/<repo>/watchers/update
        POST /api/0/<namespace>/<repo>/watchers/update

    ::

        POST /api/0/fork/<username>/<repo>/watchers/update
        POST /api/0/fork/<username>/<namespace>/<repo>/watchers/update

    Input
    ^^^^^

    +------------------+---------+--------------+---------------------------+
    | Key              | Type    | Optionality  | Description               |
    +==================+=========+==============+===========================+
    | ``repo``         | string  | Mandatory    | | The name of the project |
    |                  |         |              |   to fork.                |
    +------------------+---------+--------------+---------------------------+
    | ``status``       | string  | Mandatory    | | The new watch status to |
    |                  |         |              |   set on that project.    |
    |                  |         |              |   (See options below)     |
    +------------------+---------+--------------+---------------------------+
    | ``watcher``      | string  | Mandatory    | | The name of the user    |
    |                  |         |              |   changing their watch    |
    |                  |         |              |   status.                 |
    +------------------+---------+--------------+---------------------------+
    | ``namespace``    | string  | Optional     | | The namespace of the    |
    |                  |         |              |   project to fork.        |
    +------------------+---------+--------------+---------------------------+
    | ``username``     | string  | Optional     | | The username of the user|
    |                  |         |              |   of the fork.            |
    +------------------+---------+--------------+---------------------------+

    Watch Status
    ^^^^^^^^^^^^

    +------------+----------------------------------------------+
    | Key        | Description                                  |
    +============+==============================================+
    | -1         | Reset the watch status to default            |
    +------------+----------------------------------------------+
    | 0          | Unwatch, don't notify the user of anything   |
    +------------+----------------------------------------------+
    | 1          | Watch issues and pull-requests               |
    +------------+----------------------------------------------+
    | 2          | Watch commits                                |
    +------------+----------------------------------------------+
    | 3          | Watch commits, issues and pull-requests      |
    +------------+----------------------------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            "message": "You are now watching issues and PRs on this project",
            "status": "ok"
        }
    """

    project = _get_repo(repo, username, namespace)
    _check_token(project)

    # Get the input submitted
    data = get_request_data()

    watcher = data.get("watcher")

    if not watcher:
        _log.debug("api_update_project_watchers: Invalid watcher: %s", watcher)
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    is_site_admin = pagure.utils.is_admin()
    # Only allow the main admin, and the user themselves to update their
    # status
    if not is_site_admin and flask.g.fas_user.username != watcher:
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.EMODIFYPROJECTNOTALLOWED
        )

    try:
        pagure.lib.query.get_user(flask.g.session, watcher)
    except pagure.exceptions.PagureException:
        _log.debug(
            "api_update_project_watchers: Invalid user watching: %s", watcher
        )
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    watch_status = data.get("status")

    try:
        msg = pagure.lib.query.update_watch_status(
            session=flask.g.session,
            project=project,
            user=watcher,
            watch=watch_status,
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

    return flask.jsonify({"message": msg, "status": "ok"})


@API.route("/<repo>/git/modifyacls", methods=["POST"])
@API.route("/<namespace>/<repo>/git/modifyacls", methods=["POST"])
@API.route("/fork/<username>/<repo>/git/modifyacls", methods=["POST"])
@API.route(
    "/fork/<username>/<namespace>/<repo>/git/modifyacls", methods=["POST"]
)
@api_login_required(acls=["modify_project"])
@api_method
def api_modify_acls(repo, namespace=None, username=None):
    """
    Modify ACLs on a project
    ------------------------
    Add, remove or update ACLs on a project for a particular user or group.

    This is restricted to project admins.

    ::

        POST /api/0/<repo>/git/modifyacls
        POST /api/0/<namespace>/<repo>/git/modifyacls

    ::

        POST /api/0/fork/<username>/<repo>/git/modifyacls
        POST /api/0/fork/<username>/<namespace>/<repo>/git/modifyacls


    Input
    ^^^^^

    +------------------+---------+---------------+---------------------------+
    | Key              | Type    | Optionality   | Description               |
    +==================+=========+===============+===========================+
    | ``user_type``    | String  | Mandatory     | A string to specify if    |
    |                  |         |               | the ACL should be changed |
    |                  |         |               | for a user or a group.    |
    |                  |         |               | Specifying one of either  |
    |                  |         |               | 'user' or 'group' is      |
    |                  |         |               | mandatory                 |
    |                  |         |               |                           |
    +------------------+---------+---------------+---------------------------+
    | ``name``         | String  | Mandatory     | The name of the user or   |
    |                  |         |               | group whose ACL           |
    |                  |         |               | should be changed.        |
    |                  |         |               |                           |
    +------------------+---------+---------------+---------------------------+
    | ``acl``          | String  | Optional      | Can be either unspecified,|
    |                  |         |               | 'ticket', 'commit',       |
    |                  |         |               | 'admin'. If unspecified,  |
    |                  |         |               | the access will be removed|
    |                  |         |               |                           |
    +------------------+---------+---------------+---------------------------+


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "access_groups": {
            "admin": [],
            "commit": [],
            "ticket": []
          },
          "access_users": {
            "admin": [],
            "commit": [
              "ta2"
            ],
            "owner": [
              "karsten"
            ],
            "ticket": [
              "ta1"
            ]
          },
          "close_status": [],
          "custom_keys": [],
          "date_created": "1531131619",
          "date_modified": "1531302337",
          "description": "pagure local instance",
          "fullname": "pagure",
          "id": 1,
          "milestones": {},
          "name": "pagure",
          "namespace": null,
          "parent": null,
          "priorities": {},
          "tags": [],
          "url_path": "pagure",
          "user": {
            "fullname": "KH",
            "name": "karsten"
          }
        }

    """
    output = {}

    project = _get_repo(repo, username, namespace)
    _check_token(project, project_token=False)

    form = pagure.forms.ModifyACLForm(csrf_enabled=False)
    if form.validate_on_submit():
        acl = form.acl.data
        group = None
        user = None
        if form.user_type.data == "user":
            user = form.name.data
        else:
            group = form.name.data

        is_site_admin = pagure.utils.is_admin()
        admins = [u.username for u in project.get_project_users("admin")]

        if not acl:
            if (
                user
                and flask.g.fas_user.username != user
                and flask.g.fas_user.username not in admins
                and flask.g.fas_user.username != project.user.username
                and not is_site_admin
            ):
                raise pagure.exceptions.APIError(
                    401, error_code=APIERROR.EMODIFYPROJECTNOTALLOWED
                )
        elif (
            flask.g.fas_user.username not in admins
            and flask.g.fas_user.username != project.user.username
            and not is_site_admin
        ):
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EMODIFYPROJECTNOTALLOWED
            )

        if user:
            user_obj = pagure.lib.query.search_user(
                flask.g.session, username=user
            )
            if not user_obj:
                raise pagure.exceptions.APIError(
                    404, error_code=APIERROR.ENOUSER
                )

        elif group:
            group_obj = pagure.lib.query.search_groups(
                flask.g.session, group_name=group
            )
            if not group_obj:
                raise pagure.exceptions.APIError(
                    404, error_code=APIERROR.ENOGROUP
                )

        if acl:
            if (
                user
                and user_obj not in project.access_users[acl]
                and user_obj.user != project.user.user
            ):
                _log.info(
                    "Adding user %s to project: %s", user, project.fullname
                )
                pagure.lib.query.add_user_to_project(
                    session=flask.g.session,
                    project=project,
                    new_user=user,
                    user=flask.g.fas_user.username,
                    access=acl,
                )
            elif group and group_obj not in project.access_groups[acl]:
                _log.info(
                    "Adding group %s to project: %s", group, project.fullname
                )
                pagure.lib.query.add_group_to_project(
                    session=flask.g.session,
                    project=project,
                    new_group=group,
                    user=flask.g.fas_user.username,
                    access=acl,
                    create=pagure_config.get("ENABLE_GROUP_MNGT", False),
                    is_admin=pagure.utils.is_admin(),
                )
        else:
            if user:
                _log.info(
                    "Looking at removing user %s from project %s",
                    user,
                    project.fullname,
                )
                try:
                    pagure.lib.query.remove_user_of_project(
                        flask.g.session,
                        user_obj,
                        project,
                        flask.g.fas_user.username,
                    )
                except pagure.exceptions.PagureException as err:
                    raise pagure.exceptions.APIError(
                        400, error_code=APIERROR.EINVALIDREQ, errors="%s" % err
                    )
            elif group:
                pass

        try:
            flask.g.session.commit()
        except pagure.exceptions.PagureException as msg:
            flask.g.session.rollback()
            _log.debug(msg)
            flask.flash(str(msg), "error")
        except SQLAlchemyError as err:
            _log.exception(err)
            flask.g.session.rollback()
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

        pagure.lib.git.generate_gitolite_acls(project=project)
        output = project.to_json(api=True, public=True)
    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors
        )

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/options", methods=["GET"])
@API.route("/<namespace>/<repo>/options", methods=["GET"])
@API.route("/fork/<username>/<repo>/options", methods=["GET"])
@API.route("/fork/<username>/<namespace>/<repo>/options", methods=["GET"])
@api_login_required(acls=["modify_project"])
@api_method
def api_get_project_options(repo, username=None, namespace=None):
    """
    Get project options
    ----------------------
    Allow project admins to retrieve the current options of a project.

    ::

        GET /api/0/<repo>/options
        GET /api/0/<namespace>/<repo>/options

    ::

        GET /api/0/fork/<username>/<repo>/options
        GET /api/0/fork/<username>/<namespace>/<repo>/options

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "settings": {
            "Enforce_signed-off_commits_in_pull-request": false,
            "Minimum_score_to_merge_pull-request": -1,
            "Only_assignee_can_merge_pull-request": false,
            "Web-hooks": null,
            "always_merge": false,
            "disable_non_fast-forward_merges": false,
            "fedmsg_notifications": true,
            "issue_tracker": true,
            "issue_tracker_read_only": false,
            "issues_default_to_private": false,
            "notify_on_commit_flag": false,
            "notify_on_pull-request_flag": false,
            "open_metadata_access_to_all": false,
            "project_documentation": false,
            "pull_request_access_only": false,
            "pull_requests": true,
            "stomp_notifications": true
          },
          "status": "ok"
        }

    """
    project = _get_repo(repo, username, namespace)
    _check_token(project, project_token=False)

    return flask.jsonify({"settings": project.settings, "status": "ok"})


@API.route("/<repo>/connector", methods=["GET"])
@API.route("/<namespace>/<repo>/connector", methods=["GET"])
@API.route("/fork/<username>/<repo>/connector", methods=["GET"])
@API.route("/fork/<username>/<namespace>/<repo>/connector", methods=["GET"])
@api_login_required(acls=["modify_project"])
@api_method
def api_get_project_connector(repo, username=None, namespace=None):
    """
    Get project connector
    ---------------------
    Allow project owners and admins to retrieve their own connector tokens.
    Connector tokens are the API tokens and the Web Hook token
    of the project. Connector tokens make possible for an external
    application to listen and verify project notifications and act
    on project via the REST API.

    ::

        GET /api/0/<repo>/connector
        GET /api/0/<namespace>/<repo>/connector

    ::

        GET /api/0/fork/<username>/<repo>/connector
        GET /api/0/fork/<username>/<namespace>/<repo>/connector

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "connector": {
              "hook_token": "aaabbbccc",
              "api_token": [
                  {'name': 'foo token',
                   'id': "abcdefoo",
                   'expired': True}
                  {'name': 'bar token',
                   'id': "abcdebar",
                   'expired': False}
              ]
          },
          "status": "ok"
        }

    """
    project = _get_repo(repo, username, namespace)
    _check_token(project, project_token=False)

    authorized_users = [project.user.username]
    authorized_users.extend(
        [user.user for user in project.access_users["admin"]]
    )
    if flask.g.fas_user.user not in authorized_users:
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.ENOTHIGHENOUGH
        )

    user_obj = pagure.lib.query.search_user(
        flask.g.session, username=flask.g.fas_user.user
    )
    user_project_tokens = [
        token for token in user_obj.tokens if token.project_id == project.id
    ]

    connector = {
        "hook_token": project.hook_token,
        "api_tokens": [
            {"description": t.description, "id": t.id, "expired": t.expired}
            for t in user_project_tokens
        ],
    }

    return flask.jsonify({"connector": connector, "status": "ok"})


@API.route("/<repo>/webhook/token", methods=["GET"])
@API.route("/<namespace>/<repo>/webhook/token", methods=["GET"])
@API.route("/fork/<username>/<repo>/webhook/token", methods=["GET"])
@API.route(
    "/fork/<username>/<namespace>/<repo>/webhook/token", methods=["GET"]
)
@api_method
@api_login_required(acls=[], optional=True)
def api_get_project_webhook_token(repo, username=None, namespace=None):
    """
    Get project webhook token
    -------------------------
    Allow project collaborators to retrieve the project webhook token.

    ::

        GET /api/0/<repo>/webhook/token
        GET /api/0/<namespace>/<repo>/webhook/token

    ::

        GET /api/0/fork/<username>/<repo>/webhook/token
        GET /api/0/fork/<username>/<namespace>/<repo>/webhook/token

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "webhook": {
              "token": "aaabbbccc",
          },
          "status": "ok"
        }

    """
    project = _get_repo(repo, username, namespace)
    _check_token(project, project_token=False)

    authorized_users = [project.user.username]
    # All collaborators are authorized to read the token
    for access_type in project.access_users.keys():
        authorized_users.extend(
            [user.user for user in project.access_users[access_type]]
        )
    if flask.g.fas_user.user not in authorized_users:
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.ENOTHIGHENOUGH
        )

    webhook_token = {"token": project.hook_token}

    return flask.jsonify({"webhook": webhook_token, "status": "ok"})


def _check_value(value):
    """ Convert the provided value into a boolean, an int or leave it as it.
    """
    if str(value).lower() in ["true"]:
        value = True
    elif str(value).lower() in ["false"]:
        value = True
    elif str(value).isdigit():
        value = int(value)
    return value


@API.route("/<repo>/options/update", methods=["POST"])
@API.route("/<namespace>/<repo>/options/update", methods=["POST"])
@API.route("/fork/<username>/<repo>/options/update", methods=["POST"])
@API.route(
    "/fork/<username>/<namespace>/<repo>/options/update", methods=["POST"]
)
@api_login_required(acls=["modify_project"])
@api_method
def api_modify_project_options(repo, username=None, namespace=None):
    """
    Update project options
    ----------------------
    Allow project admins to modify the options of a project.

    ::

        POST /api/0/<repo>/options/update
        POST /api/0/<namespace>/<repo>/options/update

    ::

        POST /api/0/fork/<username>/<repo>/options/update
        POST /api/0/fork/<username>/<namespace>/<repo>/options/update

    Input
    ^^^^^

    Simply specify the key/values you would like to set. Beware that if you
    do not specify in the request values that have been changed before they
    will go back to their default value.

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
            'message': 'Edited successfully settings of repo: test',
            'status': 'ok'
        }

    """
    project = _get_repo(repo, username, namespace)
    _check_token(project, project_token=False)

    settings = {}
    for key in flask.request.form:

        settings[key] = _check_value(flask.request.form[key])

    try:
        message = pagure.lib.query.update_project_settings(
            flask.g.session,
            repo=project,
            settings=settings,
            user=flask.g.fas_user.username,
            from_api=True,
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

    return flask.jsonify({"message": message, "status": "ok"})


@API.route("/<repo>/token/new", methods=["POST"])
@API.route("/<namespace>/<repo>/token/new", methods=["POST"])
@API.route("/fork/<username>/<repo>/token/new", methods=["POST"])
@API.route("/fork/<username>/<namespace>/<repo>/token/new", methods=["POST"])
@api_login_required(acls=["modify_project"])
@api_method
def api_project_create_api_token(repo, namespace=None, username=None):
    """
    Create API project Token
    ------------------------
    Create a project token API for the caller user

    This is restricted to project admins.

    ::

        POST /api/0/<repo>/token/new
        POST /api/0/<namespace>/<repo>/token/new

    ::

        POST /api/0/fork/<username>/<repo>/token/new
        POST /api/0/fork/<username>/<namespace>/<repo>/token/new


    Input
    ^^^^^

    +------------------+---------+---------------+---------------------------+
    | Key              | Type    | Optionality   | Description               |
    +==================+=========+===============+===========================+
    | ``description``  | String  | optional      | A string to specify the   |
    |                  |         |               | description of the token  |
    |                  |         |               |                           |
    +------------------+---------+---------------+---------------------------+
    | ``acls``         | List    | Mandatory     | The ACLs                  |
    |                  |         |               |                           |
    +------------------+---------+---------------+---------------------------+


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "token": {
            "description": "My foo token",
            "id": "aaabbbcccfootoken",
          },
        }

    """
    output = {}

    project = _get_repo(repo, username, namespace)
    _check_token(project, project_token=False)

    authorized_users = [project.user.username]
    authorized_users.extend(
        [user.user for user in project.access_users["admin"]]
    )
    if flask.g.fas_user.user not in authorized_users:
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.ENOTHIGHENOUGH
        )

    authorized_acls = pagure_config.get("USER_ACLS", [])
    form = pagure.forms.NewTokenForm(csrf_enabled=False, sacls=authorized_acls)
    if form.validate_on_submit():
        acls = form.acls.data
        description = form.description.data
        expiration_date = form.expiration_date.data
    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors
        )

    token = pagure.lib.query.add_token_to_user(
        flask.g.session,
        project=project,
        acls=acls,
        username=flask.g.fas_user.user,
        description=description,
        expiration_date=expiration_date,
    )
    output = {"token": {"description": token.description, "id": token.id}}

    jsonout = flask.jsonify(output)
    return jsonout


@API.route("/<repo>/blockuser", methods=["POST"])
@API.route("/<namespace>/<repo>/blockuser", methods=["POST"])
@API.route("/fork/<username>/<repo>/blockuser", methods=["POST"])
@API.route("/fork/<username>/<namespace>/<repo>/blockuser", methods=["POST"])
@api_login_required(acls=["modify_project"])
@api_method
def api_project_block_user(repo, namespace=None, username=None):
    """
    Block an user from a project
    ----------------------------
    Block an user from interacting with the project

    This is restricted to project admins.

    ::

        POST /api/0/<repo>/blockuser
        POST /api/0/<namespace>/<repo>/blockuser

    ::

        POST /api/0/fork/<username>/<repo>/blockuser
        POST /api/0/fork/<username>/<namespace>/<repo>/blockuser


    Input
    ^^^^^

    +------------------+---------+---------------+---------------------------+
    | Key              | Type    | Optionality   | Description               |
    +==================+=========+===============+===========================+
    | ``username``     | String  | optional      | The username of the user  |
    |                  |         |               | to block on this project  |
    +------------------+---------+---------------+---------------------------+

    Beware that this API endpoint updates **all** the users blocked in the
    project, so if you are updating this list, do not submit just one username,
    submit the updated list.


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {"message": "User(s) blocked"}

    """
    output = {}

    project = _get_repo(repo, username, namespace)
    _check_token(project)

    authorized_users = [project.user.username]
    authorized_users.extend(
        [user.user for user in project.access_users["admin"]]
    )
    if flask.g.fas_user.username not in authorized_users:
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.ENOTHIGHENOUGH
        )

    usernames = flask.request.form.getlist("username")

    try:
        users = set()
        for user in usernames:
            user = user.strip()
            if user:
                pagure.lib.query.get_user(flask.g.session, user)
                users.add(user)
        project.block_users = list(users)
        flask.g.session.add(project)
        flask.g.session.commit()
        output = {"message": "User(s) blocked"}
    except pagure.exceptions.PagureException as err:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(err)
        )
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        _log.exception(err)
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    jsonout = flask.jsonify(output)
    return jsonout
