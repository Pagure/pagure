# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

API namespace version 0.

"""

import functools

import flask
import enum

API = flask.Blueprint('api_ns', __name__, url_prefix='/api/0')


import pagure
import pagure.lib
from pagure import __api_version__, APP, SESSION
from pagure.doc_utils import load_doc
from pagure.exceptions import APIError


class APIERROR(enum.Enum):
    """ Clast listing as Enum all the possible error thrown by the API.
    """
    ENOCODE = 'Variable message describing the issue'
    ENOPROJECT = 'Project not found'
    ETRACKERDISABLED = 'Issue tracker disabled for this project'
    EDBERROR = 'An error occured at the database level and prevent the ' \
        'action from reaching completion'
    EINVALIDREQ = 'Invalid or incomplete input submited'
    EINVALIDTOK = 'Invalid or expired token. Please visit %s to get or '\
        'renew your API token.' % APP.config['APP_URL']
    ENOISSUE = 'Issue not found'
    EISSUENOTALLOWED = 'You are not allowed to view this issue'
    EPULLREQUESTSDISABLED = 'Pull-Request have been deactivated for this '\
        'project'
    ENOREQ = 'Pull-Request not found'
    ENOPRCLOSE = 'You are not allowed to merge/close pull-request for '\
        'this project'
    EPRSCORE = 'This request does not have the minimum review score '\
        'necessary to be merged'
    ENOTASSIGNEE = 'Only the assignee can merge this review'
    ENOTASSIGNED = 'This request must be assigned to be merged'
    ENOUSER = 'No such user found'


def check_api_acls(acls, optional=False):
    ''' Checks if the user provided an API token with its request and if
    this token allows the user to access the endpoint desired.
    '''

    flask.g.token = None
    flask.g.user = None
    token = None
    token_str = None
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
    elif optional:
        return

    if not token_auth:
        output = {
            'error_code': APIERROR.EINVALIDTOK.name,
            'error': APIERROR.EINVALIDTOK.value,
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

            response = check_api_acls(acls, optional=True)
            if response:
                return response
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
            if e.error_code in [APIERROR.EDBERROR]:
                APP.logger.exception(e)

            if e.error_code in [APIERROR.ENOCODE]:
                response = flask.jsonify(
                    {
                        'error': e.error,
                        'error_code': e.error_code
                    }
                )
            else:
                response = flask.jsonify(
                    {
                        'error': e.error_code.value,
                        'error_code': e.error_code.name,
                    }
                )
            response.status_code = e.status_code
        else:
            response = result

        return response

    return wrapper


from pagure.api import issue
from pagure.api import fork
from pagure.api import project
from pagure.api import user


@API.route('/version/')
@API.route('/version')
def api_version():
    '''
    API Version
    -----------
    Get the current API version.

    ::

        GET /api/0/version

    Sample response
    ^^^^^^^^^^^^^^^

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
    Retrieve users that have logged into the Paugre instance.
    This can then be used as input for autocompletion in some forms/fields.

    ::

        GET /api/0/users

    Parameters
    ^^^^^^^^^^

    +---------------+----------+---------------+------------------------------+
    | Key           | Type     | Optionality   | Description                  |
    +===============+==========+===============+==============================+
    | ``pattern``   | string   | Optional      | | Filters the starting       |
    |               |          |               |   letters of the usernames   |
    +---------------+----------+---------------+------------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

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
    List the tags made on the project's issues.

    ::

        GET /api/0/<repo>/tags

    ::

        GET /api/0/fork/<username>/<repo>/tags

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
          "tags": ["tag1", "tag2"]
        }

    '''
    pattern = flask.request.args.get('pattern', None)
    if pattern is not None and not pattern.endswith('*'):
        pattern += '*'

    project_obj = pagure.lib.get_project(SESSION, repo, username)
    if not project_obj:
        output = {'output': 'notok', 'error': 'Project not found'}
        jsonout = flask.jsonify(output)
        jsonout.status_code = 404
        return jsonout

    return flask.jsonify(
        {
            'tags': [
                tag.tag
                for tag in pagure.lib.get_tags_of_project(
                    SESSION, project_obj, pattern=pattern)
            ]
        }
    )


@API.route('/groups/')
@API.route('/groups')
def api_groups():
    '''
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

    Sample response
    ^^^^^^^^^^^^^^^

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


@API.route('/error_codes/')
@API.route('/error_codes')
def api_error_codes():
    '''
    Error codes
    ------------
    Get a dictionary (hash) of all error codes.

    ::

        GET /api/0/error_codes

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          ENOCODE: 'Variable message describing the issue',
          ENOPROJECT: 'Project not found',
        }

    '''
    errors = {val.name: val.value for val in APIERROR.__members__.values()}

    return flask.jsonify(errors)


@API.route('/')
def api():
    ''' Display the api information page. '''
    api_git_tags_doc = load_doc(project.api_git_tags)

    api_new_issue_doc = load_doc(issue.api_new_issue)
    api_view_issue_doc = load_doc(issue.api_view_issue)
    api_view_issue_comment_doc = load_doc(issue.api_view_issue_comment)
    api_view_issues_doc = load_doc(issue.api_view_issues)
    api_issue_add_comment_doc = load_doc(issue.api_comment_issue)

    api_pull_request_views_doc = load_doc(fork.api_pull_request_views)
    api_pull_request_view_doc = load_doc(fork.api_pull_request_view)
    api_pull_request_merge_doc = load_doc(fork.api_pull_request_merge)
    api_pull_request_close_doc = load_doc(fork.api_pull_request_close)
    api_pull_request_add_comment_doc = load_doc(
        fork.api_pull_request_add_comment)
    api_pull_request_add_flag_doc = load_doc(fork.api_pull_request_add_flag)

    api_version_doc = load_doc(api_version)
    api_users_doc = load_doc(api_users)
    api_view_user_doc = load_doc(user.api_view_user)
    api_project_tags_doc = load_doc(api_project_tags)
    api_groups_doc = load_doc(api_groups)
    api_error_codes_doc = load_doc(api_error_codes)

    return flask.render_template(
        'api.html',
        projects=[
            api_git_tags_doc,
        ],
        issues=[
            api_new_issue_doc,
            api_view_issues_doc,
            api_view_issue_doc,
            api_view_issue_comment_doc,
            api_issue_add_comment_doc,
        ],
        requests=[
            api_pull_request_views_doc,
            api_pull_request_view_doc,
            api_pull_request_merge_doc,
            api_pull_request_close_doc,
            api_pull_request_add_comment_doc,
            api_pull_request_add_flag_doc,
        ],
        users=[
            api_users_doc,
            api_view_user_doc,
            api_groups_doc,
        ],
        extras=[
            api_version_doc,
            api_project_tags_doc,
            api_error_codes_doc,
        ],
    )


@APP.route('/api/')
@APP.route('/api')
def api_redirect():
    ''' Redirects the user to the API documentation page.

    '''
    return flask.redirect(flask.url_for('api_ns.api'))
