# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import datetime

from sqlalchemy.exc import SQLAlchemyError

import pagure
import pagure.exceptions
import pagure.lib

from pagure import (
    APP, SESSION, is_repo_committer, api_authenticated, urlpattern
)
from pagure.api import (
    API, api_method, api_login_required, api_login_optional, APIERROR
)


@API.route('/<repo>/new_issue', methods=['POST'])
@API.route('/<namespace>/<repo>/new_issue', methods=['POST'])
@API.route('/fork/<username>/<repo>/new_issue', methods=['POST'])
@API.route('/fork/<username>/<namespace>/<repo>/new_issue', methods=['POST'])
@api_login_required(acls=['issue_create'])
@api_method
def api_new_issue(repo, username=None, namespace=None):
    """
    Create a new issue
    ------------------
    Open a new issue on a project.

    ::

        POST /api/0/<repo>/new_issue
        POST /api/0/<namespace>/<repo>/new_issue

    ::

        POST /api/0/fork/<username>/<repo>/new_issue
        POST /api/0/fork/<username>/<namespace>/<repo>/new_issue

    Input
    ^^^^^

    +-------------------+--------+-------------+---------------------------+
    | Key               | Type   | Optionality | Description               |
    +===================+========+=============+===========================+
    | ``title``         | string | Mandatory   | The title of the issue    |
    +-------------------+--------+-------------+---------------------------+
    | ``issue_content`` | string | Mandatory   | | The description of the  |
    |                   |        |             |   issue                   |
    +-------------------+--------+-------------+---------------------------+
    | ``private``       | boolean| Optional    | | Include this key if     |
    |                   |        |             |   you want a private issue|
    |                   |        |             |   to be created           |
    +-------------------+--------+-------------+---------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "issue": {
            "assignee": null,
            "blocks": [],
            "close_status": null,
            "closed_at": null,
            "comments": [],
            "content": "This issue needs attention",
            "custom_fields": [],
            "date_created": "1479458613",
            "depends": [],
            "id": 1,
            "milestone": null,
            "priority": null,
            "private": false,
            "status": "Open",
            "tags": [],
            "title": "test issue",
            "user": {
              "fullname": "PY C",
              "name": "pingou"
            }
          },
          "message": "Issue created"
        }

    """
    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    if flask.g.token.project and repo != flask.g.token.project:
        raise pagure.exceptions.APIError(
            401, error_code=APIERROR.EINVALIDTOK)

    user_obj = pagure.lib.get_user(
        SESSION, flask.g.fas_user.username)
    if not user_obj:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOUSER)

    form = pagure.forms.IssueFormSimplied(csrf_enabled=False)
    if form.validate_on_submit():
        title = form.title.data
        content = form.issue_content.data
        milestone = form.milestone.data
        private = str(form.private.data).lower() in ['true', '1']

        try:
            issue = pagure.lib.new_issue(
                SESSION,
                repo=repo,
                title=title,
                content=content,
                private=private,
                milestone=milestone,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
            )
            SESSION.flush()
            # If there is a file attached, attach it.
            filestream = flask.request.files.get('filestream')
            if filestream and '<!!image>' in issue.content:
                new_filename = pagure.lib.git.add_file_to_git(
                    repo=repo,
                    issue=issue,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                    user=user_obj,
                    filename=filestream.filename,
                    filestream=filestream.stream,
                )
                # Replace the <!!image> tag in the comment with the link
                # to the actual image
                filelocation = flask.url_for(
                    'view_issue_raw_file',
                    repo=repo.name,
                    username=username,
                    filename=new_filename,
                )
                new_filename = new_filename.split('-', 1)[1]
                url = '[![%s](%s)](%s)' % (
                    new_filename, filelocation, filelocation)
                issue.content = issue.content.replace('<!!image>', url)
                SESSION.add(issue)
                SESSION.flush()

            SESSION.commit()
            output['message'] = 'Issue created'
            output['issue'] = issue.to_json(public=True)
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<namespace>/<repo>/issues')
@API.route('/fork/<username>/<repo>/issues')
@API.route('/<repo>/issues')
@API.route('/fork/<username>/<namespace>/<repo>/issues')
@api_login_optional()
@api_method
def api_view_issues(repo, username=None, namespace=None):
    """
    List project's issues
    ---------------------
    List issues of a project.

    ::

        GET /api/0/<repo>/issues
        GET /api/0/<namespace>/<repo>/issues

    ::

        GET /api/0/fork/<username>/<repo>/issues
        GET /api/0/fork/<username>/<namespace>/<repo>/issues

    Parameters
    ^^^^^^^^^^

    +---------------+---------+--------------+---------------------------+
    | Key           | Type    | Optionality  | Description               |
    +===============+=========+==============+===========================+
    | ``status``    | string  | Optional     | | Filters the status of   |
    |               |         |              |   issues. Fetches all the |
    |               |         |              |   issues if status is     |
    |               |         |              |   ``all``. Default:       |
    |               |         |              |   ``Open``                |
    +---------------+---------+--------------+---------------------------+
    | ``tags``      | string  | Optional     | | A list of tags you      |
    |               |         |              |   wish to filter. If      |
    |               |         |              |   you want to filter      |
    |               |         |              |   for issues not having   |
    |               |         |              |   a tag, add an           |
    |               |         |              |   exclamation mark in     |
    |               |         |              |   front of it             |
    +---------------+---------+--------------+---------------------------+
    | ``assignee``  | string  | Optional     | | Filter the issues       |
    |               |         |              |   by assignee             |
    +---------------+---------+--------------+---------------------------+
    | ``author``    | string  | Optional     | | Filter the issues       |
    |               |         |              |   by creator              |
    +---------------+---------+--------------+---------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "args": {
            "assignee": null,
            "author": null,
            "status": "Closed",
            "tags": [
              "0.1"
            ]
          },
          "total_issues": 1,
          "issues": [
            {
              "assignee": null,
              "blocks": ["1"],
              "comments": [],
              "content": "asd",
              "date_created": "1427442217",
              "depends": [],
              "id": 4,
              "private": false,
              "status": "Fixed",
              "tags": [
                "0.1"
              ],
              "title": "bug",
              "user": {
                "fullname": "PY.C",
                "name": "pingou"
              }
            }
          ]
        }

    """

    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    status = flask.request.args.get('status', None)
    tags = flask.request.args.getlist('tags')
    tags = [tag.strip() for tag in tags if tag.strip()]
    assignee = flask.request.args.get('assignee', None)
    author = flask.request.args.get('author', None)
    since = flask.request.args.get('since', None)

    # Hide private tickets
    private = False
    # If user is authenticated, show him/her his/her private tickets
    if api_authenticated():
        if repo != flask.g.token.project:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK)
        private = flask.g.fas_user.username
    # If user is repo committer, show all tickets included the private ones
    if is_repo_committer(repo):
        private = None

    params = {
        'session': SESSION,
        'repo': repo,
        'tags': tags,
        'assignee': assignee,
        'author': author,
        'private': private,
    }

    if status is not None:
        if status.lower() == 'all':
            params.update({'status': None})
        elif status.lower() == 'closed':
            params.update({'closed': True})
        else:
            params.update({'status': status})

    updated_after = None
    if since:
        # Validate and convert the time
        if since.isdigit():
            # We assume its a timestamp, so convert it to datetime
            try:
                updated_after = datetime.datetime.fromtimestamp(int(since))
            except ValueError:
                raise pagure.exceptions.APIError(
                    400, error_code=APIERROR.ETIMESTAMP)
        else:
            # We assume datetime format, so validate it
            try:
                updated_after = datetime.datetime.strptime(since, '%Y-%m-%d')
            except ValueError:
                raise pagure.exceptions.APIError(
                    400, error_code=APIERROR.EDATETIME)

    params.update({'updated_after': updated_after})
    issues = pagure.lib.search_issues(**params)
    jsonout = flask.jsonify({
        'total_issues': len(issues),
        'issues': [issue.to_json(public=True) for issue in issues],
        'args': {
            'status': status,
            'tags': tags,
            'assignee': assignee,
            'author': author,
            'since': since
        }
    })
    return jsonout


@API.route('/<repo>/issue/<issueid>')
@API.route('/<namespace>/<repo>/issue/<issueid>')
@API.route('/fork/<username>/<repo>/issue/<issueid>')
@API.route('/fork/<username>/<namespace>/<repo>/issue/<issueid>')
@api_login_optional()
@api_method
def api_view_issue(repo, issueid, username=None, namespace=None):
    """
    Issue information
    -----------------
    Retrieve information of a specific issue.

    ::

        GET /api/0/<repo>/issue/<issue id>
        GET /api/0/<namespace>/<repo>/issue/<issue id>

    ::

        GET /api/0/fork/<username>/<repo>/issue/<issue id>
        GET /api/0/fork/<username>/<namespace>/<repo>/issue/<issue id>

    The identifier provided can be either the unique identifier or the
    regular identifier used in the UI (for example ``24`` in
    ``/forks/user/test/issue/24``)

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "assignee": null,
          "blocks": [],
          "comments": [],
          "content": "This issue needs attention",
          "date_created": "1431414800",
          "depends": ["4"],
          "id": 1,
          "private": false,
          "status": "Open",
          "tags": [],
          "title": "test issue",
          "user": {
            "fullname": "PY C",
            "name": "pingou"
          }
        }

    """
    comments = flask.request.args.get('comments', True)
    if str(comments).lower() in ['0', 'False']:
        comments = False

    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    issue_id = issue_uid = None
    try:
        issue_id = int(issueid)
    except (ValueError, TypeError):
        issue_uid = issueid

    issue = pagure.lib.search_issues(
        SESSION, repo, issueid=issue_id, issueuid=issue_uid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOISSUE)

    if api_authenticated():
        if repo != flask.g.token.project:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK)

    if issue.private and not is_repo_committer(repo) \
            and (not api_authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EISSUENOTALLOWED)

    jsonout = flask.jsonify(
        issue.to_json(public=True, with_comments=comments))
    return jsonout


@API.route('/<repo>/issue/<issueid>/comment/<int:commentid>')
@API.route('/<namespace>/<repo>/issue/<issueid>/comment/<int:commentid>')
@API.route('/fork/<username>/<repo>/issue/<issueid>/comment/<int:commentid>')
@API.route(
    '/fork/<username>/<namespace>/<repo>/issue/<issueid>/'
    'comment/<int:commentid>')
@api_login_optional()
@api_method
def api_view_issue_comment(
        repo, issueid, commentid, username=None, namespace=None):
    """
    Comment of an issue
    --------------------
    Retrieve a specific comment of an issue.

    ::

        GET /api/0/<repo>/issue/<issue id>/comment/<comment id>
        GET /api/0/<namespace>/<repo>/issue/<issue id>/comment/<comment id>

    ::

        GET /api/0/fork/<username>/<repo>/issue/<issue id>/comment/<comment id>
        GET /api/0/fork/<username>/<namespace>/<repo>/issue/<issue id>/comment/<comment id>

    The identifier provided can be either the unique identifier or the
    regular identifier used in the UI (for example ``24`` in
    ``/forks/user/test/issue/24``)

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "avatar_url": "https://seccdn.libravatar.org/avatar/...",
          "comment": "9",
          "comment_date": "2015-07-01 15:08",
          "date_created": "1435756127",
          "id": 464,
          "parent": null,
          "user": {
            "fullname": "P.-Y.C.",
            "name": "pingou"
          }
        }

    """

    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    issue_id = issue_uid = None
    try:
        issue_id = int(issueid)
    except (ValueError, TypeError):
        issue_uid = issueid

    issue = pagure.lib.search_issues(
        SESSION, repo, issueid=issue_id, issueuid=issue_uid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOISSUE)

    if api_authenticated():
        if repo != flask.g.token.project:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK)

    if issue.private and not is_repo_committer(issue.project) \
            and (not api_authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EISSUENOTALLOWED)

    comment = pagure.lib.get_issue_comment(SESSION, issue.uid, commentid)
    if not comment:
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ENOCOMMENT)

    output = comment.to_json(public=True)
    output['avatar_url'] = pagure.lib.avatar_url_from_email(
        comment.user.default_email, size=16)
    output['comment_date'] = comment.date_created.strftime(
        '%Y-%m-%d %H:%M:%S')
    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/issue/<int:issueid>/status', methods=['POST'])
@API.route('/<namespace>/<repo>/issue/<int:issueid>/status', methods=['POST'])
@API.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/status', methods=['POST'])
@API.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/status',
    methods=['POST'])
@api_login_required(acls=['issue_change_status', 'issue_update'])
@api_method
def api_change_status_issue(repo, issueid, username=None, namespace=None):
    """
    Change issue status
    -------------------
    Change the status of an issue.

    ::

        POST /api/0/<repo>/issue/<issue id>/status
        POST /api/0/<namespace>/<repo>/issue/<issue id>/status

    ::

        POST /api/0/fork/<username>/<repo>/issue/<issue id>/status
        POST /api/0/fork/<username>/<namespace>/<repo>/issue/<issue id>/status

    Input
    ^^^^^

    +----------------- +---------+--------------+------------------------+
    | Key              | Type    | Optionality  | Description            |
    +==================+=========+==============+========================+
    | ``close_status`` | string  | Optional     | The close status of    |
    |                  |         |              | the issue              |
    +----------------- +---------+--------------+------------------------+
    | ``status``       | string  | Mandatory    | The new status of the  |
    |                  |         |              | issue, can be 'Open' or|
    |                  |         |              | 'Closed'               |
    +----------------- +---------+--------------+------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "Successfully edited issue #1"
        }

    """
    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)

    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    if api_authenticated():
        if repo != flask.g.token.project:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK)

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOISSUE)

    if issue.private and not is_repo_committer(repo) \
            and (not api_authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EISSUENOTALLOWED)

    status = pagure.lib.get_issue_statuses(SESSION)
    form = pagure.forms.StatusForm(
        status=status,
        close_status=repo.close_status,
        csrf_enabled=False)

    close_status = None
    if form.close_status.raw_data:
        close_status = form.close_status.data
    new_status = form.status.data.strip()
    if new_status in repo.close_status and not close_status:
        close_status = new_status
        new_status = 'Closed'
        form.status.data = new_status

    if form.validate_on_submit():
        try:
            # Update status
            message = pagure.lib.edit_issue(
                SESSION,
                issue=issue,
                status=new_status,
                close_status=close_status,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
            )
            SESSION.commit()
            if message:
                output['message'] = message
            else:
                output['message'] = 'No changes'

            if message:
                pagure.lib.add_metadata_update_notif(
                    session=SESSION,
                    issue=issue,
                    messages=message,
                    user=flask.g.fas_user.username,
                    ticketfolder=APP.config['TICKETS_FOLDER']
                )
        except pagure.exceptions.PagureException as err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err))
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/issue/<int:issueid>/comment', methods=['POST'])
@API.route('/<namespace>/<repo>/issue/<int:issueid>/comment', methods=['POST'])
@API.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/comment', methods=['POST'])
@API.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/comment',
    methods=['POST'])
@api_login_required(acls=['issue_comment', 'issue_update'])
@api_method
def api_comment_issue(repo, issueid, username=None, namespace=None):
    """
    Comment to an issue
    -------------------
    Add a comment to an issue.

    ::

        POST /api/0/<repo>/issue/<issue id>/comment
        POST /api/0/<namespace>/<repo>/issue/<issue id>/comment

    ::

        POST /api/0/fork/<username>/<repo>/issue/<issue id>/comment
        POST /api/0/fork/<username>/<namespace>/<repo>/issue/<issue id>/comment

    Input
    ^^^^^

    +--------------+----------+---------------+---------------------------+
    | Key          | Type     | Optionality   | Description               |
    +==============+==========+===============+===========================+
    | ``comment``  | string   | Mandatory     | | The comment to add to   |
    |              |          |               |   the issue               |
    +--------------+----------+---------------+---------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "Comment added"
        }

    """
    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    if api_authenticated():
        if flask.g.token.project and repo != flask.g.token.project:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK)

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOISSUE)

    if issue.private and not is_repo_committer(repo) \
            and (not api_authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EISSUENOTALLOWED)

    form = pagure.forms.CommentForm(csrf_enabled=False)
    if form.validate_on_submit():
        comment = form.comment.data
        try:
            # New comment
            message = pagure.lib.add_issue_comment(
                SESSION,
                issue=issue,
                comment=comment,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
            )
            SESSION.commit()
            output['message'] = message
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/issue/<int:issueid>/assign', methods=['POST'])
@API.route('/<namespace>/<repo>/issue/<int:issueid>/assign', methods=['POST'])
@API.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/assign', methods=['POST'])
@API.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/assign',
    methods=['POST'])
@api_login_required(acls=['issue_assign', 'issue_update'])
@api_method
def api_assign_issue(repo, issueid, username=None, namespace=None):
    """
    Assign an issue
    ---------------
    Assign an issue to someone.

    ::

        POST /api/0/<repo>/issue/<issue id>/assign
        POST /api/0/<namespace>/<repo>/issue/<issue id>/assign

    ::

        POST /api/0/fork/<username>/<repo>/issue/<issue id>/assign
        POST /api/0/fork/<username>/<namespace>/<repo>/issue/<issue id>/assign

    Input
    ^^^^^

    +--------------+----------+---------------+---------------------------+
    | Key          | Type     | Optionality   | Description               |
    +==============+==========+===============+===========================+
    | ``assignee`` | string   | Mandatory     | | The username of the user|
    |              |          |               |   to assign the issue to. |
    +--------------+----------+---------------+---------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "Issue assigned"
        }

    """
    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    if api_authenticated():
        if repo != flask.g.token.project:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK)

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOISSUE)

    if issue.private and not is_repo_committer(repo) \
            and (not api_authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EISSUENOTALLOWED)

    form = pagure.forms.AssignIssueForm(csrf_enabled=False)
    if form.validate_on_submit():
        assignee = form.assignee.data or None
        # Create our metadata comment object
        try:
            # New comment
            message = pagure.lib.add_issue_assignee(
                SESSION,
                issue=issue,
                assignee=assignee,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
            )
            SESSION.commit()
            if message:
                pagure.lib.add_metadata_update_notif(
                    session=SESSION,
                    issue=issue,
                    messages=message,
                    user=flask.g.fas_user.username,
                    ticketfolder=APP.config['TICKETS_FOLDER']
                )
                output['message'] = message
            else:
                output['message'] = 'Nothing to change'
        except pagure.exceptions.PagureException as err:  # pragma: no cover
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err))
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/issue/<int:issueid>/subscribe', methods=['POST'])
@API.route('/<namespace>/<repo>/issue/<int:issueid>/subscribe', methods=['POST'])
@API.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/subscribe', methods=['POST'])
@API.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/subscribe',
    methods=['POST'])
@api_login_required(acls=['issue_subscribe'])
@api_method
def api_subscribe_issue(repo, issueid, username=None, namespace=None):
    """
    Subscribe to an issue
    ---------------------
    Allows someone to subscribe or unscribe to the notifications related to
    an issue.

    ::

        POST /api/0/<repo>/issue/<issue id>/subscribe
        POST /api/0/<namespace>/<repo>/issue/<issue id>/subscribe

    ::

        POST /api/0/fork/<username>/<repo>/issue/<issue id>/subscribe
        POST /api/0/fork/<username>/<namespace>/<repo>/issue/<issue id>/subscribe

    Input
    ^^^^^

    +--------------+----------+---------------+---------------------------+
    | Key          | Type     | Optionality   | Description               |
    +==============+==========+===============+===========================+
    | ``status``   | boolean   | Mandatory    | | The subscription status |
    |              |          |               |   to subscribe or         |
    |              |          |               |   unsubscribe to the.     |
    |              |          |               |   issue.                  |
    +--------------+----------+---------------+---------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "User subscribed"
        }

    """
    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    if api_authenticated():
        if repo != flask.g.token.project:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK)

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOISSUE)

    if issue.private and not is_repo_admin(repo) \
            and (not api_authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EISSUENOTALLOWED)

    form = pagure.forms.SubscribtionForm(csrf_enabled=False)
    if form.validate_on_submit():
        status = str(form.status.data).strip().lower() in ['1', 'true']
        try:
            # Toggle subscribtion
            message = pagure.lib.set_watch_obj(
                SESSION,
                user=flask.g.fas_user.username,
                obj=issue,
                watch_status=status
            )
            SESSION.commit()
            output['message'] = message
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDREQ, errors=form.errors)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/issue/<int:issueid>/custom/<field>', methods=['POST'])
@API.route(
    '/<namespace>/<repo>/issue/<int:issueid>/custom/<field>',
    methods=['POST'])
@API.route(
    '/fork/<username>/<repo>/issue/<int:issueid>/custom/<field>',
    methods=['POST'])
@API.route(
    '/fork/<username>/<namespace>/<repo>/issue/<int:issueid>/custom/<field>',
    methods=['POST'])
@api_login_required(acls=['issue_update_custom_fields', 'issue_update'])
@api_method
def api_update_custom_field(
        repo, issueid, field, username=None, namespace=None):
    """
    Update custom field
    -------------------
    Update or reset the content of a custom field associated to an issue.

    ::

        POST /api/0/<repo>/issue/<issue id>/custom/<field>
        POST /api/0/<namespace>/<repo>/issue/<issue id>/custom/<field>

    ::

        POST /api/0/fork/<username>/<repo>/issue/<issue id>/custom/<field>
        POST /api/0/fork/<username>/<namespace>/<repo>/issue/<issue id>/custom/<field>

    Input
    ^^^^^

    +----------------- +---------+--------------+-------------------------+
    | Key              | Type    | Optionality  | Description             |
    +==================+=========+==============+=========================+
    | ``value``        | string  | Optional     | The new value of the    |
    |                  |         |              | custom field of interest|
    +----------------- +---------+--------------+-------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "Custom field adjusted"
        }

    """
    repo = pagure.lib.get_project(
        SESSION, repo, user=username, namespace=namespace)

    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    if api_authenticated():
        if repo != flask.g.token.project:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK)

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOISSUE)

    if issue.private and not is_repo_admin(repo) \
            and (not api_authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EISSUENOTALLOWED)

    fields = {k.name: k for k in repo.issue_keys}
    if field not in fields:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.EINVALIDISSUEFIELD)

    key = fields[field]
    value = flask.request.form.get('value')
    if value:
        if key.key_type == 'link':
            links = value.split(',')
            for link in links:
                link = link.replace(' ', '')
                if not urlpattern.match(link):
                    raise pagure.exceptions.APIError(
                        400, error_code=APIERROR.EINVALIDISSUEFIELD_LINK)
    try:
        message = pagure.lib.set_custom_key_value(
            SESSION, issue, key, value)

        SESSION.commit()
        if message:
            output['message'] = message
            pagure.lib.add_metadata_update_notif(
                session=SESSION,
                issue=issue,
                messages=message,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER']
            )
        else:
            output['message'] = 'No changes'
    except pagure.exceptions.PagureException as err:
        raise pagure.exceptions.APIError(
            400, error_code=APIERROR.ENOCODE, error=str(err))
    except SQLAlchemyError as err:  # pragma: no cover
        print err
        SESSION.rollback()
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)


    if message:
        pagure.lib.add_metadata_update_notif(
            session=SESSION,
            issue=issue,
            messages=message,
            user=flask.g.fas_user.username,
            ticketfolder=APP.config['TICKETS_FOLDER']
        )

    jsonout = flask.jsonify(output)
    return jsonout
