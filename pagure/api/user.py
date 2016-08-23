# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask

import pagure
import pagure.exceptions
import pagure.lib
from pagure import SESSION
from pagure.api import API, api_method, APIERROR


@API.route('/user/<username>')
@api_method
def api_view_user(username):
    """
    User information
    ----------------
    Use this endpoint to retrieve information about a specific user.

    ::

        GET /api/0/user/<username>

    ::

        GET /api/0/user/ralph

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "forks": [],
          "repos": [
            {
              "date_created": "1426595173",
              "description": "",
              "id": 5,
              "name": "pagure",
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
                "fullname": "ralph",
                "name": "ralph"
              }
            }
          ],
          "user": {
            "fullname": "ralph",
            "name": "ralph"
          }
        }

    """
    httpcode = 200
    output = {}

    user = pagure.lib.search_user(SESSION, username=username)
    if not user:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOUSER)

    repopage = flask.request.args.get('repopage', 1)
    try:
        repopage = int(repopage)
    except ValueError:
        repopage = 1

    forkpage = flask.request.args.get('forkpage', 1)
    try:
        forkpage = int(forkpage)
    except ValueError:
        forkpage = 1

    repos = pagure.lib.search_projects(
        SESSION,
        username=username,
        fork=False)

    forks = pagure.lib.search_projects(
        SESSION,
        username=username,
        fork=True)

    output['user'] = user.to_json(public=True)
    output['repos'] = [repo.to_json(public=True) for repo in repos]
    output['forks'] = [repo.to_json(public=True) for repo in forks]

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout
