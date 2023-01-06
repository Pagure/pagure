# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Matt Prahl <mprahl@redhat.com>

"""

from __future__ import absolute_import, unicode_literals

import flask

import pagure
import pagure.exceptions
import pagure.lib.query
from pagure.api import (
    API,
    APIERROR,
    api_login_optional,
    api_method,
    get_page,
    get_per_page,
)
from pagure.utils import is_true


@API.route("/groups/")
@API.route("/groups")
@api_method
def api_groups():
    """
    List groups
    -----------
    Retrieve groups on this Pagure instance.
    This can then be used as input for autocompletion in some forms/fields.

    ::

        GET /api/0/groups

    Parameters
    ^^^^^^^^^^

    +---------------+----------+---------------+--------------------------+
    | Key           | Type     | Optionality   | Description              |
    +===============+==========+===============+==========================+
    | ``pattern``   | string   | Optional      | | Filters the starting   |
    |               |          |               |   letters of the group   |
    |               |          |               |   names                  |
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
          "total_groups": 2,
          u'pagination': {
            'first': 'http://localhost/api/0/groups?per_page=20&extended=1&page=1',
            'last': 'http://localhost/api/0/groups?per_page=20&extended=1&page=1',
            'next': null,
            'page': 1,
            'pages': 1,
            'per_page': 20,
            'prev': None
          },
          "groups": ["group1", "group2"]
        }

    """  # noqa
    pattern = flask.request.args.get("pattern", None)
    extended = is_true(flask.request.args.get("extended", False))

    if pattern is not None and not pattern.endswith("*"):
        pattern += "*"

    page = get_page()
    per_page = get_per_page()
    group_cnt = pagure.lib.query.search_groups(
        flask.g.session, pattern=pattern, count=True
    )
    pagination_metadata = pagure.lib.query.get_pagination_metadata(
        flask.request, page, per_page, group_cnt
    )
    query_start = (page - 1) * per_page
    query_limit = per_page

    groups = pagure.lib.query.search_groups(
        flask.g.session, pattern=pattern, limit=query_limit, offset=query_start
    )

    if extended:
        groups = [
            {"name": grp.group_name, "description": grp.description}
            for grp in groups
        ]
    else:
        groups = [group.group_name for group in groups]

    return flask.jsonify(
        {
            "total_groups": group_cnt,
            "groups": groups,
            "pagination": pagination_metadata,
        }
    )


@API.route("/group/<group>")
@api_login_optional()
@api_method
def api_view_group(group):
    """
    Group information
    -----------------
    Use this endpoint to retrieve information about a specific group.

    ::

        GET /api/0/group/<group>

    ::

        GET /api/0/group/some_group_name


    ::

        GET /api/0/group/some_group_name?projects=1&acl=commit

    ::

        GET /api/0/group/some_group_name?page=1&per_page=50

    Input
    ^^^^^

    +-----------------------+---------+--------------+-----------------------------+
    | Key                   | Type    | Optionality  | Description                 |
    +=======================+=========+==============+=============================+
    | ``group name``        | str     | Mandatory    | The name of the group to    |
    |                       |         |              | retrieve information about. |
    +-----------------------+---------+--------------+-----------------------------+
    | ``projects``          | bool    | Optional     | Specifies whether to include|
    |                       |         |              | projects in the data        |
    |                       |         |              | returned.                   |
    +-----------------------+---------+--------------+-----------------------------+
    | ``acl``               | str     | Optional     | Filter the project returned |
    |                       |         |              | (if any) to those where the |
    |                       |         |              | has the specified ACL level.|
    |                       |         |              | Can be any of: ``admin``,   |
    |                       |         |              | ``commit`` or ``ticket``.   |
    +-----------------------+---------+--------------+-----------------------------+
    | ``page``              | int     | Optional     | Specifies which page to     |
    |                       |         |              | return (defaults to: 1)     |
    +-----------------------+---------+--------------+-----------------------------+
    | ``per_page``          | int     | Optional     | The number of projects      |
    |                       |         |              | to return per page.         |
    |                       |         |              | The maximum is 100.         |
    +-----------------------+---------+--------------+-----------------------------+


    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "creator": {
            "default_email": "user1@example.com",
            "emails": [
              "user1@example.com"
            ],
            "fullname": "User1",
            "name": "user1"
          },
          "date_created": "1492011511",
          "description": "Some Group",
          "display_name": "Some Group",
          "group_type": "user",
          "pagination": {
            "first": "http://127.0.0.1:5000/api/0/group/some_group_name?per_page=2&page=1",
            "last": "http://127.0.0.1:5000/api/0/group/some_group_name?per_page=2&page=2",
            "next": "http://127.0.0.1:5000/api/0/group/some_group_name?per_page=2&page=2",
            "page": 1,
            "pages": 2,
            "per_page": 2,
            "prev": null
          },
          "members": [
            "user1",
            "user2"
          ],
          "name": "some_group_name"
        }

    ::

        {
          "creator": {
            "default_email": "user1@example.com",
            "emails": [
              "user1@example.com"
            ],
            "fullname": "User1",
            "name": "user1"
          },
          "date_created": "1492011511",
          "description": "Some Group",
          "display_name": "Some Group",
          "group_type": "user",
          "members": [
            "user1",
            "user2"
          ],
          "name": "some_group_name",
          "total_projects": 1000,
          "pagination": {
            "first":
                "http://127.0.0.1:5000/api/0/group/some_group_name?per_page=2&projects=1&page=1",
            "last":
                "http://127.0.0.1:5000/api/0/group/some_group_name?per_page=2&projects=1&page=500",
            "next":
                "http://127.0.0.1:5000/api/0/group/some_group_name?per_page=2&projects=1&page=2",
            "page": 1,
            "pages": 500,
            "per_page": 2,
            "prev": null
          },
          "projects": [],
        }


    """  # noqa
    projects = flask.request.values.get("projects", "").strip().lower() in [
        "1",
        "true",
    ]
    acl = flask.request.values.get("acl", "").strip().lower() or None
    if acl == "ticket":
        acl = ["admin", "commit", "ticket"]
    elif acl == "commit":
        acl = ["commit", "admin"]
    elif acl:
        acl = [acl]

    group = pagure.lib.query.search_groups(flask.g.session, group_name=group)
    if not group:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOGROUP)

    output = group.to_json(public=(not pagure.utils.api_authenticated()))

    if projects:
        # Prepare pagination data for projects
        if not acl:
            group_projects = group.projects
        elif acl:
            group_projects = [
                pg.project for pg in group.projects_groups if pg.access in acl
            ]
        page = get_page()
        per_page = get_per_page()
        projects_cnt = len(group_projects)
        pagination_metadata = pagure.lib.query.get_pagination_metadata(
            flask.request, page, per_page, projects_cnt
        )
        query_start = (page - 1) * per_page
        query_limit = per_page
        page_projects = group_projects[query_start : query_start + query_limit]

        output["total_projects"] = projects_cnt
        output["pagination"] = pagination_metadata

        output["projects"] = [
            project.to_json(public=True) for project in page_projects
        ]
    jsonout = flask.jsonify(output)
    jsonout.status_code = 200
    return jsonout
