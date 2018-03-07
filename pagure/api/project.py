# -*- coding: utf-8 -*-

"""
 (c) 2015-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import logging

from sqlalchemy.exc import SQLAlchemyError
from six import string_types
from pygit2 import GitError, Repository

import pagure
import pagure.forms
import pagure.exceptions
import pagure.lib
import pagure.lib.git
import pagure.utils
from pagure.api import (API, api_method, APIERROR, api_login_required,
                        get_authorized_api_project, api_login_optional)
from pagure.config import config as pagure_config


_log = logging.getLogger(__name__)


@API.route('/<repo>/git/tags')
@API.route('/<namespace>/<repo>/git/tags')
@API.route('/fork/<username>/<repo>/git/tags')
@API.route('/fork/<username>/<namespace>/<repo>/git/tags')
@api_method
def api_git_tags(repo, username=None, namespace=None):
    """
    Project git tags
    ----------------
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
    with_commits = flask.request.values.get('with_commits', None) or False

    if str(with_commits).lower() in ['1', 'true']:
        with_commits = True

    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)
    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    tags = pagure.lib.git.get_git_tags(repo, with_commits=with_commits)

    jsonout = flask.jsonify({
        'total_tags': len(tags),
        'tags': tags
    })
    return jsonout


@API.route('/<repo>/watchers')
@API.route('/<namespace>/<repo>/watchers')
@API.route('/fork/<username>/<repo>/watchers')
@API.route('/fork/<username>/<namespace>/<repo>/watchers')
@api_method
def api_project_watchers(repo, username=None, namespace=None):
    '''
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
    '''
    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)
    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    implicit_watch_users = {repo.user.username}
    for access_type in repo.access_users.keys():
        implicit_watch_users = \
            implicit_watch_users | set(
                [user.username for user in repo.access_users[access_type]])

    watching_users_to_watch_level = {}
    for implicit_watch_user in implicit_watch_users:
        user_watch_level = pagure.lib.get_watch_level_on_repo(
            flask.g.session, implicit_watch_user, repo)
        watching_users_to_watch_level[implicit_watch_user] = user_watch_level

    for access_type in repo.access_groups.keys():
        group_names = ['@' + group.group_name
                       for group in repo.access_groups[access_type]]
        for group_name in group_names:
            if group_name not in watching_users_to_watch_level:
                watching_users_to_watch_level[group_name] = set()
            # By the logic in pagure.lib.get_watch_level_on_repo, group members
            # only by default watch issues.  If they want to watch commits they
            # have to explicitly subscribe.
            watching_users_to_watch_level[group_name].add('issues')

    # Get the explicit watch statuses
    for watcher in repo.watchers:
        if watcher.watch_issues or watcher.watch_commits:
            watching_users_to_watch_level[watcher.user.username] = \
                pagure.lib.get_watch_level_on_repo(
                    flask.g.session, watcher.user.username, repo)
        else:
            if watcher.user.username in watching_users_to_watch_level:
                watching_users_to_watch_level.pop(watcher.user.username, None)

    return flask.jsonify({
        'total_watchers': len(watching_users_to_watch_level),
        'watchers': watching_users_to_watch_level
    })


@API.route('/<repo>/git/urls')
@API.route('/<namespace>/<repo>/git/urls')
@API.route('/fork/<username>/<repo>/git/urls')
@API.route('/fork/<username>/<namespace>/<repo>/git/urls')
@api_login_optional()
@api_method
def api_project_git_urls(repo, username=None, namespace=None):
    '''
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
    '''
    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)
    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)
    git_urls = {}

    git_url_ssh = pagure_config.get('GIT_URL_SSH')
    if pagure.utils.authenticated() and git_url_ssh:
        try:
            git_url_ssh = git_url_ssh.format(
                username=flask.g.fas_user.username)
        except (KeyError, IndexError):
            pass

    if git_url_ssh:
        git_urls['ssh'] = '{0}{1}.git'.format(git_url_ssh, repo.fullname)
    if pagure_config.get('GIT_URL_GIT'):
        git_urls['git'] = '{0}{1}.git'.format(
            pagure_config['GIT_URL_GIT'], repo.fullname)

    return flask.jsonify({
        'total_urls': len(git_urls),
        "urls": git_urls
    })


@API.route('/<repo>/git/branches')
@API.route('/<namespace>/<repo>/git/branches')
@API.route('/fork/<username>/<repo>/git/branches')
@API.route('/fork/<username>/<namespace>/<repo>/git/branches')
@api_method
def api_git_branches(repo, username=None, namespace=None):
    '''
    List project branches
    ---------------------
    List the branches associated with a Pagure git repository

    ::

        GET /api/0/<repo>/git/branches
        GET /api/0/<namespace>/<repo>/git/branches

    ::

        GET /api/0/fork/<username>/<repo>/git/branches
        GET /api/0/fork/<username>/<namespace>/<repo>/git/branches

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "total_branches": 2,
          "branches": ["master", "dev"]
        }

    '''
    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)
    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    branches = pagure.lib.git.get_git_branches(repo)

    return flask.jsonify(
        {
            'total_branches': len(branches),
            'branches': branches
        }
    )


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
    |               |          |               |   by ownership           |
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
    | ``page``      | int      | Optional      | | Specifies that         |
    |               |          |               |   pagination should be   |
    |               |          |               |   turned on and that     |
    |               |          |               |   this specific page     |
    |               |          |               |   should be displayed    |
    +---------------+----------+---------------+--------------------------+
    | ``per_page``  | int      | Optional      | | The number of projects |
    |               |          |               |   to return per page.    |
    |               |          |               |   The maximum is 100.    |
    +---------------+----------+---------------+--------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "total_projects": 2,
          "projects": [
            {
              "access_groups": {
                "admin": [],
                "commit": [],
                "ticket": []
              },
              "access_users": {
                "admin": [],
                "commit": [
                  "some_user"
                ],
                "owner": [
                  "pingou"
                ],
                "ticket": []
              },
              "close_status": [],
              "custom_keys": [],
              "date_created": "1427441537",
              "date_modified": "1427441537",
              "description": "A web-based calendar for Fedora",
              "milestones": {},
              "namespace": null,
              "id": 7,
              "name": "fedocal",
              "fullname": "fedocal",
              "parent": null,
              "priorities": {},
              "tags": [],
              "user": {
                "fullname": "Pierre-Yves C",
                "name": "pingou"
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
                  "pingou"
                ],
                "ticket": []
              },
              "close_status": [],
              "custom_keys": [],
              "date_created": "1431666007",
              "description": "An awesome messaging servicefor everyone",
              "id": 12,
              "milestones": {},
              "name": "fedmsg",
              "namespace": null,
              "fullname": "forks/pingou/fedmsg",
              "parent": {
                "date_created": "1433423298",
                "description": "An awesome messaging servicefor everyone",
                "id": 11,
                "name": "fedmsg",
                "fullname": "fedmsg",
                "parent": null,
                "user": {
                  "fullname": "Ralph B",
                  "name": "ralph"
                }
              },
              "priorities": {},
              "tags": [],
              "user": {
                "fullname": "Pierre-Yves C",
                "name": "pingou"
              }
            }
          ]
        }

    Sample Response With Pagination
    ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
              "user": {
                "fullname": "Matt Prahl",
                "name": "mprahl"
              }
            }
          ],
          "total_projects": 1000
        }
    """
    tags = flask.request.values.getlist('tags')
    username = flask.request.values.get('username', None)
    fork = flask.request.values.get('fork', None)
    namespace = flask.request.values.get('namespace', None)
    owner = flask.request.values.get('owner', None)
    pattern = flask.request.values.get('pattern', None)
    short = flask.request.values.get('short', None)
    page = flask.request.values.get('page', None)
    per_page = flask.request.values.get('per_page', None)

    if str(fork).lower() in ['1', 'true']:
        fork = True
    elif str(fork).lower() in ['0', 'false']:
        fork = False
    if str(short).lower() in ['1', 'true']:
        short = True
    else:
        short = False

    private = False
    if pagure.utils.authenticated() \
            and username == flask.g.fas_user.username:
        private = flask.g.fas_user.username

    project_count = pagure.lib.search_projects(
        flask.g.session, username=username, fork=fork, tags=tags,
        pattern=pattern, private=private, namespace=namespace, owner=owner,
        count=True)
    # Pagination code inspired by Flask-SQLAlchemy
    pagination_metadata = None
    query_start = None
    query_limit = None
    if page:
        try:
            page = int(page)
        except (TypeError, ValueError):
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EINVALIDREQ)

        if page < 1:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EINVALIDREQ)

        if per_page:
            try:
                per_page = int(per_page)
            except (TypeError, ValueError):
                raise pagure.exceptions.APIError(
                    400, error_code=APIERROR.EINVALIDREQ)

            if per_page < 1 or per_page > 100:
                raise pagure.exceptions.APIError(
                    400, error_code=APIERROR.EINVALIDPERPAGEVALUE)
        else:
            per_page = 20

        pagination_metadata = pagure.lib.get_pagination_metadata(
            flask.request, page, per_page, project_count)
        query_start = (page - 1) * per_page
        query_limit = per_page

    projects = pagure.lib.search_projects(
        flask.g.session, username=username, fork=fork, tags=tags,
        pattern=pattern, private=private, namespace=namespace, owner=owner,
        limit=query_limit, start=query_start)

    # prepare the output json
    jsonout = {
        'total_projects': project_count,
        'projects': projects,
        'args': {
            'tags': tags,
            'username': username,
            'fork': fork,
            'pattern': pattern,
            'namespace': namespace,
            'owner': owner,
            'short': short,
        }
    }

    if not short:
        projects = [p.to_json(api=True, public=True) for p in projects]
    else:
        projects = [
            {
                'name': p.name,
                'namespace': p.namespace,
                'fullname': p.fullname.replace('forks/', 'fork/', 1)
                if p.fullname.startswith('forks/') else p.fullname,
                'description': p.description,
            }
            for p in projects
        ]

    jsonout['projects'] = projects
    if pagination_metadata:
        jsonout['args']['page'] = page
        jsonout['args']['per_page'] = per_page
        jsonout['pagination'] = pagination_metadata
    return flask.jsonify(jsonout)


@API.route('/<repo>')
@API.route('/<namespace>/<repo>')
@API.route('/fork/<username>/<repo>')
@API.route('/fork/<username>/<namespace>/<repo>')
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
    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)

    expand_group = str(
        flask.request.values.get('expand_group', None)
    ).lower() in ['1', 't', 'True']

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    output = repo.to_json(api=True, public=True)

    if expand_group:
        group_details = {}
        for grp in repo.projects_groups:
            group_details[grp.group.group_name] = [
                user.username for user in grp.group.users]
        output['group_details'] = group_details

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/new/', methods=['POST'])
@API.route('/new', methods=['POST'])
@api_login_required(acls=['create_project'])
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

    +------------------+---------+--------------+---------------------------+
    | Key              | Type    | Optionality  | Description               |
    +==================+=========+==============+===========================+
    | ``name``         | string  | Mandatory    | | The name of the new     |
    |                  |         |              |   project.                |
    +------------------+---------+--------------+---------------------------+
    | ``description``  | string  | Mandatory    | | A short description of  |
    |                  |         |              |   the new project.        |
    +------------------+---------+--------------+---------------------------+
    | ``namespace``    | string  | Optional     | | The namespace of the    |
    |                  |         |              |   project to fork.        |
    +------------------+---------+--------------+---------------------------+
    | ``url``          | string  | Optional     | | An url providing more   |
    |                  |         |              |   information about the   |
    |                  |         |              |   project.                |
    +------------------+---------+--------------+---------------------------+
    | ``avatar_email`` | string  | Optional     | | An email address for the|
    |                  |         |              |   avatar of the project.  |
    +------------------+---------+--------------+---------------------------+
    | ``create_readme``| boolean | Optional     | | A boolean to specify if |
    |                  |         |              |   there should be a readme|
    |                  |         |              |   added to the project on |
    |                  |         |              |   creation.               |
    +------------------+---------+--------------+---------------------------+
    | ``private``      | boolean | Optional     | | A boolean to specify if |
    |                  |         |              |   the project to create   |
    |                  |         |              |   is private.             |
    |                  |         |              |   Note: not all pagure    |
    |                  |         |              |   instance support private|
    |                  |         |              |   projects, confirm this  |
    |                  |         |              |   with your administrators|
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
          'message': 'Project creation queued',
          'taskid': '123-abcd'
        }

        wait=True:
        {
          'message': 'Project creation queued'
        }

    """
    user = pagure.lib.search_user(
        flask.g.session, username=flask.g.fas_user.username)
    output = {}

    if not pagure_config.get('ENABLE_NEW_PROJECTS', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENEWPROJECTDISABLED)

    namespaces = pagure_config['ALLOWED_PREFIX'][:]
    if user:
        namespaces.extend([grp for grp in user.groups])

    form = pagure.forms.ProjectForm(
        namespaces=namespaces, csrf_enabled=False)
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
        if pagure_config.get('PRIVATE_PROJECTS', False):
            private = form.private.data

        try:
            taskid = pagure.lib.new_project(
                flask.g.session,
                name=name,
                namespace=namespace,
                description=description,
                private=private,
                url=url,
                avatar_email=avatar_email,
                user=flask.g.fas_user.username,
                blacklist=pagure_config['BLACKLISTED_PROJECTS'],
                allowed_prefix=pagure_config['ALLOWED_PREFIX'],
                gitfolder=pagure_config['GIT_FOLDER'],
                docfolder=pagure_config['DOCS_FOLDER'],
                ticketfolder=pagure_config['TICKETS_FOLDER'],
                requestfolder=pagure_config['REQUESTS_FOLDER'],
                add_readme=create_readme,
                userobj=user,
                prevent_40_chars=pagure_config.get(
                    'OLD_VIEW_COMMIT_ENABLED', False),
                user_ns=pagure_config.get('USER_NAMESPACE', False),
            )
            flask.g.session.commit()
            output = {'message': 'Project creation queued',
                      'taskid': taskid}

            if flask.request.form.get('wait', True):
                result = pagure.lib.tasks.get_result(taskid).get()
                project = pagure.lib._get_project(
                    flask.g.session, name=result['repo'],
                    namespace=result['namespace'],
                    case=pagure_config.get('CASE_SENSITIVE', False))
                output = {'message': 'Project "%s" created' % project.fullname}
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


@API.route('/<repo>', methods=['PATCH'])
@API.route('/<namespace>/<repo>', methods=['PATCH'])
@api_login_required(acls=['modify_project'])
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
    project = get_authorized_api_project(
        flask.g.session, repo, namespace=namespace)
    if not project:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENOPROJECT)

    is_site_admin = pagure.utils.is_admin()
    admins = [u.username for u in project.get_project_users('admin')]
    # Only allow the main admin, the admins of the project, and Pagure site
    # admins to modify projects, even if the user has the right ACLs on their
    # token
    if flask.g.fas_user.username not in admins \
            and flask.g.fas_user.username != project.user.username \
            and not is_site_admin:
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.EMODIFYPROJECTNOTALLOWED)

    valid_keys = ['main_admin', 'retain_access']
    # Check if it's JSON or form data
    if flask.request.headers.get('Content-Type') == 'application/json':
        # Set force to True to ignore the mimetype. Set silent so that None is
        # returned if it's invalid JSON.
        args = flask.request.get_json(force=True, silent=True) or {}
        retain_access = args.get('retain_access', False)
    else:
        args = flask.request.form
        retain_access = args.get('retain_access', '').lower() in ['true', '1']

    if not args:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    # Check to make sure there aren't parameters we don't support
    for key in args.keys():
        if key not in valid_keys:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EINVALIDREQ)

    if 'main_admin' in args:
        if flask.g.fas_user.username != project.user.username \
                and not is_site_admin:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.ENOTMAINADMIN)
        # If the main_admin is already set correctly, don't do anything
        if flask.g.fas_user.username == project.user:
            return flask.jsonify(project.to_json(public=False, api=True))

        try:
            new_main_admin = pagure.lib.get_user(
                flask.g.session, args['main_admin'])
        except pagure.exceptions.PagureException:
            raise pagure.exceptions.APIError(400, error_code=APIERROR.ENOUSER)

        old_main_admin = project.user.user
        pagure.lib.set_project_owner(
            flask.g.session, project, new_main_admin)
        if retain_access and flask.g.fas_user.username == old_main_admin:
            pagure.lib.add_user_to_project(
                flask.g.session, project, new_user=flask.g.fas_user.username,
                user=flask.g.fas_user.username)

    try:
        flask.g.session.commit()
    except SQLAlchemyError:  # pragma: no cover
        flask.g.session.rollback()
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EDBERROR)

    pagure.lib.git.generate_gitolite_acls(project=project)

    return flask.jsonify(project.to_json(public=False, api=True))


@API.route('/fork/', methods=['POST'])
@API.route('/fork', methods=['POST'])
@api_login_required(acls=['fork_project'])
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
            flask.g.session, repo, user=username, namespace=namespace)
        if repo is None:
            raise pagure.exceptions.APIError(
                404, error_code=APIERROR.ENOPROJECT)

        try:
            taskid = pagure.lib.fork_project(
                flask.g.session,
                user=flask.g.fas_user.username,
                repo=repo,
                gitfolder=pagure_config['GIT_FOLDER'],
                docfolder=pagure_config['DOCS_FOLDER'],
                ticketfolder=pagure_config['TICKETS_FOLDER'],
                requestfolder=pagure_config['REQUESTS_FOLDER'],
            )
            flask.g.session.commit()
            output = {'message': 'Project forking queued',
                      'taskid': taskid}

            if flask.request.form.get('wait', True):
                pagure.lib.tasks.get_result(taskid).get()
                output = {'message': 'Repo "%s" cloned to "%s/%s"'
                          % (repo.fullname, flask.g.fas_user.username,
                             repo.fullname)}
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err))
        except SQLAlchemyError as err:  # pragma: no cover
            _log.exception(err)
            flask.g.session.rollback()
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EDBERROR)
    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/git/generateacls', methods=['POST'])
@API.route('/<namespace>/<repo>/git/generateacls', methods=['POST'])
@API.route('/fork/<username>/<repo>/git/generateacls', methods=['POST'])
@API.route('/fork/<username>/<namespace>/<repo>/git/generateacls',
           methods=['POST'])
@api_login_required(acls=['generate_acls_project'])
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
    project = get_authorized_api_project(
        flask.g.session, repo, namespace=namespace)
    if not project:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    # Check if it's JSON or form data
    if flask.request.headers.get('Content-Type') == 'application/json':
        # Set force to True to ignore the mimetype. Set silent so that None is
        # returned if it's invalid JSON.
        json = flask.request.get_json(force=True, silent=True) or {}
        wait = json.get('wait', False)
    else:
        wait = str(flask.request.form.get('wait')).lower() in ['true', '1']

    try:
        taskid = pagure.lib.git.generate_gitolite_acls(
            project=project,
        ).id

        if wait:
            pagure.lib.tasks.get_result(taskid).get()
            output = {'message': 'Project ACLs generated'}
        else:
            output = {'message': 'Project ACL generation queued',
                      'taskid': taskid}
    except pagure.exceptions.PagureException as err:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(err))

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/git/branch', methods=['POST'])
@API.route('/<namespace>/<repo>/git/branch', methods=['POST'])
@API.route('/fork/<username>/<repo>/git/branch', methods=['POST'])
@API.route('/fork/<username>/<namespace>/<repo>/git/branch',
           methods=['POST'])
@api_login_required(acls=['modify_project'])
@api_method
def api_new_branch(repo, username=None, namespace=None):
    """
    Create a new git branch on a project
    ------------------------------------
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
    project = get_authorized_api_project(
        flask.g.session, repo, namespace=namespace)
    if not project:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    # Check if it's JSON or form data
    if flask.request.headers.get('Content-Type') == 'application/json':
        # Set force to True to ignore the mimetype. Set silent so that None is
        # returned if it's invalid JSON.
        args = flask.request.get_json(force=True, silent=True) or {}
    else:
        args = flask.request.form

    branch = args.get('branch')
    from_branch = args.get('from_branch')
    from_commit = args.get('from_commit')

    if from_branch and from_commit:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    if not branch or not isinstance(branch, string_types) or \
            (from_branch and not isinstance(from_branch, string_types)) or \
            (from_commit and not isinstance(from_commit, string_types)):
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    try:
        pagure.lib.git.new_git_branch(project, branch, from_branch=from_branch,
                                      from_commit=from_commit)
    except GitError:  # pragma: no cover
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EGITERROR)
    except pagure.exceptions.PagureException as error:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(error))

    output = {'message': 'Project branch was created'}
    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/c/<commit_hash>/flag', methods=['POST'])
@API.route('/<namespace>/<repo>/c/<commit_hash>/flag', methods=['POST'])
@API.route('/fork/<username>/<repo>/c/<commit_hash>/flag', methods=['POST'])
@API.route(
    '/fork/<username>/<namespace>/<repo>/c/<commit_hash>/flag',
    methods=['POST'])
@api_login_required(acls=['commit_flag'])
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
    |               |         |              |   can be any of: success,   |
    |               |         |              |   failure, error, pending,  |
    |               |         |              |   canceled                  |
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

    repo = get_authorized_api_project(
        flask.g.session, repo, user=username, namespace=namespace)

    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENOPROJECT)

    if flask.g.token.project and repo != flask.g.token.project:
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.EINVALIDTOK)

    reponame = pagure.utils.get_repo_path(repo)
    repo_obj = Repository(reponame)
    try:
        repo_obj.get(commit_hash)
    except ValueError:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENOCOMMIT)

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
            message, uid = pagure.lib.add_commit_flag(
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
            c_flag = pagure.lib.get_commit_flag_by_uid(
                flask.g.session, commit_hash, uid)
            output['message'] = message
            output['uid'] = uid
            output['flag'] = c_flag.to_json()
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err))
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EDBERROR)
    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors)

    jsonout = flask.jsonify(output)
    return jsonout
