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
          "tags": ["0.0.1", "0.0.2"]
        }

    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    tags = pagure.lib.git.get_git_tags(repo)

    jsonout = flask.jsonify({'tags': tags})
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
          "projects": [
            "https://pagure.org/fedmsg",
            "https://pagure.org/fork/pingou/fedmsg"
          ]
        }

    """
    tags = flask.request.values.getlist('tags')
    username = flask.request.values.get('username', None)
    fork = flask.request.values.get('fork', None)

    if str(fork).lower() in ['1', 'true']:
        fork = True
    elif str(fork).lower() in ['0', 'false']:
        fork = False

    projects = pagure.lib.search_projects(
        SESSION, username=username, fork=fork, tags=tags)

    if not projects:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENOPROJECTS)

    root = pagure.APP.config['APP_URL']
    if root.endswith('/'):
        root = root[:-1]

    jsonout = flask.jsonify({
        'projects': [
            root + flask.url_for(
                'view_repo',
                repo=p.name,
                username=p.user.username if p.is_fork else None)
            for p in projects
        ]})
    return jsonout
