# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask

import pagure
import pagure.exceptions
import pagure.lib
from pagure import SESSION
from pagure.api import API, api_method, APIERROR


@API.route('/<repo>/git/tags')
@API.route('/fork/<username>/<repo>/git/tags')
@api_method
def api_git_tags(repo, username=None):
    """
    Project git tags
    ----------------
    List the tags made on the project Git repository.

    ::

        GET /api/0/<repo>/git/tags

    ::

        GET /api/0/fork/<username>/<repo>/git/tags

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "total_tags": 2,
          "tags": ["0.0.1", "0.0.2"]
        }

    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    tags = pagure.lib.git.get_git_tags(repo)

    jsonout = flask.jsonify({
        'total_tags': len(tags),
        'tags': tags
    })
    return jsonout


@API.route('/projects')
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

    Parameters
    ^^^^^^^^^^

    +---------------+----------+---------------+--------------------------+
    | Key           | Type     | Optionality   | Description              |
    +===============+==========+===============+==========================+
    | ``tags``      | string   | Optional      | | Filters the projects   |
    |               |          |               |   returned by their tags |
    +---------------+----------+---------------+--------------------------+
    | ``username``  | string   | Optional      | | Filters the projects   |
    |               |          |               |   returned by the users  |
    |               |          |               |   having commit rights   |
    |               |          |               |   to it                  |
    +---------------+----------+---------------+--------------------------+
    | ``fork``      | boolean  | Optional      | | Filters the projects   |
    |               |          |               |   returned depending if  |
    |               |          |               |   they are forks or not  |
    +---------------+----------+---------------+--------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "total_projects": 2,
          "projects": [
            {
              "date_created": "1427441537",
              "description": "A web-based calendar for Fedora",
              "id": 7,
              "name": "fedocal",
              "parent": null,
              "user": {
                "fullname": "Pierre-Yves C",
                "name": "pingou"
              }
            },
            {
              "date_created": "1431666007",
              "description": "An awesome messaging servicefor everyone",
              "id": 12,
              "name": "fedmsg",
              "parent": {
                "date_created": "1433423298",
                "description": "An awesome messaging servicefor everyone",
                "id": 11,
                "name": "fedmsg",
                "parent": null,
                "user": {
                  "fullname": "Ralph B",
                  "name": "ralph"
                }
              },
              "user": {
                "fullname": "Pierre-Yves C",
                "name": "pingou"
              }
            }
          ]
        }

    """
    tags = flask.request.values.getlist('tags')
    username = flask.request.values.get('username', None)
    fork = flask.request.values.get('fork', None)
    pattern = flask.request.values.get('pattern', None)

    if str(fork).lower() in ['1', 'true']:
        fork = True
    elif str(fork).lower() in ['0', 'false']:
        fork = False

    projects = pagure.lib.search_projects(
        SESSION, username=username, fork=fork, tags=tags, pattern=pattern)

    if not projects:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENOPROJECTS)

    jsonout = flask.jsonify({
        'total_projects': len(projects),
        'projects': [p.to_json(api=True, public=True) for p in projects]
    })
    return jsonout
