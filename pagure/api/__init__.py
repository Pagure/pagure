# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

API namespace version 0.

"""

import functools

import flask

API = flask.Blueprint('api_ns', __name__, url_prefix='/api/0')


import pagure
import pagure.lib
from pagure import __api_version__, APP, SESSION
from pagure.exceptions import APIError


API_ERROR_CODE = {
    0: 'Variable message describing the issue',
    1: 'Project not found',
    2: 'No issue tracker found for this project',
    3: 'An error occured at the database level and prevent the action from '
        'reaching completion',
    4: 'Invalid or incomplete input submited',
    5: 'Invalid or expired token. Please visit %s get or renew your '
        'API token.' % APP.config['APP_URL'],
    6: 'Issue not found',
    7: 'You are not allowed to view this issue',
}


def check_api_acls(acls, optional=False):
    ''' Checks if the user provided an API token with its request and if
    this token allows the user to access the endpoint desired.
    '''

    flask.g.token = None
    flask.g.user = None
    token = None
    token_str = None
    apt_login = None
    if 'Authorization' in flask.request.headers:
        authorization = flask.request.headers['Authorization']
        if 'token' in authorization:
            token_str = authorization.split('token', 1)[1].strip()

    token_auth = False
    if token_str:
        token = pagure.lib.get_api_token(SESSION, token_str)
        if token and not token.expired:
            if acls and set(token.acls_list).intersection(set(acls)):
                token_auth = True
                flask.g.fas_user = token.user
                flask.g.token = token
            elif not acls and optional:
                token_auth = True
                flask.g.fas_user = token.user
                flask.g.token = token

    if not token_auth:
        output = {
            'error_code': 5,
            'error': API_ERROR_CODE[5],
        }
        jsonout = flask.jsonify(output)
        jsonout.status_code = 401
        return jsonout


def api_login_required(acls=None):
    ''' Decorator used to indicate that authentication is required for some
    API endpoint.
    '''

    def decorator(fn):
        ''' The decorator of the function '''

        @functools.wraps(fn)
        def decorated_function(*args, **kwargs):
            ''' Actually does the job with the arguments provided. '''

            response = check_api_acls(acls)
            if response:
                return response
            return fn(*args, **kwargs)

        return decorated_function

    return decorator


def api_login_optional(acls=None):
    ''' Decorator used to indicate that authentication is optional for some
    API endpoint.
    '''

    def decorator(fn):
        ''' The decorator of the function '''

        @functools.wraps(fn)
        def decorated_function(*args, **kwargs):
            ''' Actually does the job with the arguments provided. '''

            check_api_acls(acls, optional=True)
            return fn(*args, **kwargs)

        return decorated_function

    return decorator


def api_method(function):
    ''' Runs an API endpoint and catch all the APIException thrown. '''

    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            result = function(*args, **kwargs)
        except APIError as e:
            if e.error_code in [3]:
                APP.log.exception(e)

            if e.error_code in [0]:
                response = flask.jsonify(
                    {
                        'error': e.error,
                        'error_code': e.error_code
                    }
                )
            else:
                response = flask.jsonify(
                    {
                        'error': API_ERROR_CODE[e.error_code],
                        'error_code': e.error_code
                    }
                )
            response.status_code = e.status_code
        else:
            response = result

        return response

    return wrapper


from pagure.api import issue
from pagure.api import fork


@API.route('/version/')
@API.route('/version')
def api_version():
    '''
    API Version
    -----------
    Display the most recent api version.

    ::

        /api/version

    Accepts GET queries only.

    Sample response:

    ::

        {
          "version": "1"
        }

    '''
    return flask.jsonify({'version': __api_version__})


@API.route('/users/')
@API.route('/users')
def api_users():
    '''
    List users
    -----------
    Returns the list of all users that have logged into this pagure instances.
    This can then be used as input for autocompletion in some forms/fields.

    ::

        /api/users

    Accepts GET queries only.

    Sample response:

    ::

        {
          "users": ["user1", "user2"]
        }

    '''
    pattern = flask.request.args.get('pattern', None)
    if pattern is not None and not pattern.endswith('*'):
        pattern += '*'

    return flask.jsonify(
        {
            'users': [
                user.username
                for user in pagure.lib.search_user(
                    SESSION, pattern=pattern)
            ]
        }
    )


@API.route('/<repo>/tags')
@API.route('/<repo>/tags/')
@API.route('/fork/<username>/<repo>/tags')
@API.route('/fork/<username>/<repo>/tags/')
def api_project_tags(repo, username=None):
    '''
    List all the tags of a project
    ------------------------------
    Returns the list of all tags of the specified project.

    ::

        /api/<repo>/tags

        /api/fork/<username>/<repo>/tags

    Accepts GET queries only.

    Sample response:

    ::

        {
          "tags": ["tag1", "tag2"]
        }

    '''
    pattern = flask.request.args.get('pattern', None)
    if pattern is not None and not pattern.endswith('*'):
        pattern += '*'

    project = pagure.lib.get_project(SESSION, repo, username)
    if not project:
        output = {'output': 'notok', 'error': 'Project not found'}
        jsonout = flask.jsonify(output)
        jsonout.status_code = 404
        return jsonout

    return flask.jsonify(
        {
            'tags': [
                tag.tag
                for tag in pagure.lib.get_tags_of_project(
                    SESSION, project, pattern=pattern)
            ]
        }
    )


@API.route('/groups/')
@API.route('/groups')
def api_groups():
    '''
    List groups
    -----------
    Returns the list of all groups present on this pagure instance
    This can then be used as input for autocompletion in some forms/fields.

    ::

        /api/groups

    Accepts GET queries only.

    Sample response:

    ::

        {
          "groups": ["group1", "group2"]
        }

    '''
    pattern = flask.request.args.get('pattern', None)
    if pattern is not None and not pattern.endswith('*'):
        pattern += '*'

    return flask.jsonify(
        {
            'groups': [
                group.group_name
                for group in pagure.lib.search_groups(
                    SESSION, pattern=pattern)
            ]
        }
    )
