# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask

from sqlalchemy.exc import SQLAlchemyError

import pagure
import pagure.exceptions
import pagure.lib
import pagure.lib.git
from pagure import SESSION, APP, authenticated
from pagure.api import (API, api_method, APIERROR, api_login_required,
                        get_authorized_api_project, api_login_optional)


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

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "total_tags": 2,
          "tags": ["0.0.1", "0.0.2"]
        }

    """
    repo = get_authorized_api_project(
        SESSION, repo, user=username, namespace=namespace)
    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    tags = pagure.lib.git.get_git_tags(repo)

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
        SESSION, repo, user=username, namespace=namespace)
    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    implicit_watch_users = {repo.user.username}
    for access_type in repo.access_users.keys():
        implicit_watch_users = \
            implicit_watch_users | set(
                [user.username for user in repo.access_users[access_type]])
    for access_type in repo.access_groups.keys():
        group_names = [group.group_name
                       for group in repo.access_groups[access_type]]
        for group_name in group_names:
            group = pagure.lib.search_groups(SESSION, group_name=group_name)
            implicit_watch_users = \
                implicit_watch_users | set([
                    user.username for user in group.users])

    watching_users_to_watch_level = {}
    for implicit_watch_user in implicit_watch_users:
        user_watch_level = pagure.lib.get_watch_level_on_repo(
            SESSION, implicit_watch_user, repo)
        watching_users_to_watch_level[implicit_watch_user] = user_watch_level

    # Get the explicit watch statuses
    for watcher in repo.watchers:
        if watcher.watch_issues or watcher.watch_commits:
            watching_users_to_watch_level[watcher.user.username] = \
                pagure.lib.get_watch_level_on_repo(
                    SESSION, watcher.user.username, repo)
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
        SESSION, repo, user=username, namespace=namespace)
    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)
    git_urls = {}
    if pagure.APP.config.get('GIT_URL_SSH'):
        git_urls['ssh'] = '{0}{1}.git'.format(
            pagure.APP.config['GIT_URL_SSH'], repo.fullname)
    if pagure.APP.config.get('GIT_URL_GIT'):
        git_urls['git'] = '{0}{1}.git'.format(
            pagure.APP.config['GIT_URL_GIT'], repo.fullname)

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
        SESSION, repo, user=username, namespace=namespace)
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

    """
    tags = flask.request.values.getlist('tags')
    username = flask.request.values.get('username', None)
    fork = flask.request.values.get('fork', None)
    namespace = flask.request.values.get('namespace', None)
    owner = flask.request.values.get('owner', None)
    pattern = flask.request.values.get('pattern', None)
    short = flask.request.values.get('short', None)

    if str(fork).lower() in ['1', 'true']:
        fork = True
    elif str(fork).lower() in ['0', 'false']:
        fork = False
    if str(short).lower() in ['1', 'true']:
        short = True
    else:
        short = False

    private = False
    if authenticated() and username == flask.g.fas_user.username:
        private = flask.g.fas_user.username

    projects = pagure.lib.search_projects(
        SESSION, username=username, fork=fork, tags=tags, pattern=pattern,
        private=private, namespace=namespace, owner=owner)

    if not projects:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENOPROJECTS)

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

    jsonout = flask.jsonify({
        'total_projects': len(projects),
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
    })
    return jsonout


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
          "total_tags": 2,
          "tags": ["0.0.1", "0.0.2"]
        }

    """
    repo = get_authorized_api_project(
        SESSION, repo, user=username, namespace=namespace)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    jsonout = flask.jsonify(repo.to_json(api=True, public=True))
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

        POST /api/0/<repo>/new


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
    user = pagure.lib.search_user(SESSION, username=flask.g.fas_user.username)
    output = {}

    if not pagure.APP.config.get('ENABLE_NEW_PROJECTS', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENEWPROJECTDISABLED)

    namespaces = APP.config['ALLOWED_PREFIX'][:]
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
        if pagure.APP.config.get('PRIVATE_PROJECTS', False):
            private = form.private.data

        try:
            taskid = pagure.lib.new_project(
                SESSION,
                name=name,
                namespace=namespace,
                description=description,
                private=private,
                url=url,
                avatar_email=avatar_email,
                user=flask.g.fas_user.username,
                blacklist=APP.config['BLACKLISTED_PROJECTS'],
                allowed_prefix=APP.config['ALLOWED_PREFIX'],
                gitfolder=APP.config['GIT_FOLDER'],
                docfolder=APP.config['DOCS_FOLDER'],
                ticketfolder=APP.config['TICKETS_FOLDER'],
                requestfolder=APP.config['REQUESTS_FOLDER'],
                add_readme=create_readme,
                userobj=user,
                prevent_40_chars=APP.config.get(
                    'OLD_VIEW_COMMIT_ENABLED', False),
                user_ns=APP.config.get('USER_NAMESPACE', False),
            )
            SESSION.commit()
            output = {'message': 'Project creation queued',
                      'taskid': taskid}

            if flask.request.form.get('wait', True):
                result = pagure.lib.tasks.get_result(taskid).get()
                project = pagure.lib._get_project(
                    SESSION, name=result['repo'],
                    namespace=result['namespace'])
                output = {'message': 'Project "%s" created' % project.fullname}
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err))
        except SQLAlchemyError as err:  # pragma: no cover
            APP.logger.exception(err)
            SESSION.rollback()
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
        SESSION, repo, namespace=namespace)
    if not project:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENOPROJECT)

    admins = project.get_project_users('admin')
    if flask.g.fas_user not in admins and flask.g.fas_user != project.user:
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.EMODIFYPROJECTNOTALLOWED)

    valid_keys = ['main_admin']
    # Set force to True to ignore the mimetype. Set silent so that None is
    # returned if it's invalid JSON.
    json = flask.request.get_json(force=True, silent=True)
    if not json:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    # Check to make sure there aren't parameters we don't support
    for key in json.keys():
        if key not in valid_keys:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EINVALIDREQ)

    if 'main_admin' in json:
        if flask.g.fas_user != project.user:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.ENOTMAINADMIN)
        # If the main_admin is already set correctly, don't do anything
        if flask.g.fas_user.username == json['main_admin']:
            return flask.jsonify(project.to_json(public=False, api=True))

        try:
            new_main_admin = pagure.lib.get_user(SESSION, json['main_admin'])
        except pagure.exceptions.PagureException:
            raise pagure.exceptions.APIError(400, error_code=APIERROR.ENOUSER)

        pagure.lib.set_project_owner(SESSION, project, new_main_admin)

    try:
        SESSION.commit()
    except SQLAlchemyError:  # pragma: no cover
        SESSION.rollback()
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EDBERROR)

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

        POST /api/0/<repo>/fork


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
            SESSION, repo, user=username, namespace=namespace)
        if repo is None:
            raise pagure.exceptions.APIError(
                404, error_code=APIERROR.ENOPROJECT)

        try:
            taskid = pagure.lib.fork_project(
                SESSION,
                user=flask.g.fas_user.username,
                repo=repo,
                gitfolder=APP.config['GIT_FOLDER'],
                docfolder=APP.config['DOCS_FOLDER'],
                ticketfolder=APP.config['TICKETS_FOLDER'],
                requestfolder=APP.config['REQUESTS_FOLDER'],
            )
            SESSION.commit()
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
            APP.logger.exception(err)
            SESSION.rollback()
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.EDBERROR)
    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors)

    jsonout = flask.jsonify(output)
    return jsonout
