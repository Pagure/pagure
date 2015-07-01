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
from pagure import APP, SESSION, is_repo_admin, api_authenticated
from pagure.api import (
    API, api_method, api_login_required, api_login_optional, APIERROR
)


@API.route('/<repo>/new_issue', methods=['POST'])
@API.route('/fork/<username>/<repo>/new_issue', methods=['POST'])
@api_login_required(acls=['issue_create'])
@api_method
def api_new_issue(repo, username=None):
    """
    Create a new issue
    ------------------
    Open a new issue on a project.

    ::

        POST /api/0/<repo>/new_issue

    ::

        POST /api/0/fork/<username>/<repo>/new_issue

    Input
    ^^^^^

    +---------------+-----------+---------------+------------------------------+
    | Key           | Type      | Optionality   | Description                  |
    +===============+===========+===============+==============================+
    | ``title``     | string    | Mandatory     | The title of the issue       |
    +---------------+-----------+---------------+------------------------------+
    | ``content``   | string    | Mandatory     | | The description of the     |
    |               |           |               |   issue                      |
    +---------------+-----------+---------------+------------------------------+
    | ``private``   | boolean   | Optional      | | Include this key if        |
    |               |           |               |   you want a private issue   |
    |               |           |               |   to be created              |
    +---------------+-----------+---------------+------------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "Issue created"
        }

    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    if repo != flask.g.token.project:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    form = pagure.forms.IssueFormSimplied(csrf_enabled=False)
    if form.validate_on_submit():
        title = form.title.data
        content = form.issue_content.data
        private = form.private.data

        try:
            issue = pagure.lib.new_issue(
                SESSION,
                repo=repo,
                title=title,
                content=content,
                private=private or False,
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
                    user=flask.g.fas_user,
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
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/issues')
@API.route('/fork/<username>/<repo>/issues')
@api_login_optional()
@api_method
def api_view_issues(repo, username=None):
    """
    List project's issues
    ---------------------
    List issues of a project.

    ::

        GET /api/0/<repo>/issues

    ::

        GET /api/0/fork/<username>/<repo>/issues

    Parameters
    ^^^^^^^^^^

    +----------------+----------+---------------+---------------------------+
    | Key            | Type     | Optionality   | Description               |
    +================+==========+===============+===========================+
    | ``status``     | string   | Optional      | | Filters the status of   |
    |                |          |               |   issues. Default:        |
    |                |          |               |   ``Open``                |
    +----------------+----------+---------------+---------------------------+
    | ``tags``       | string   | Optional      | | A list of tags you      |
    |                |          |               |   wish to filter. If      |
    |                |          |               |   you want to filter      |
    |                |          |               |   for issues not having   |
    |                |          |               |   a tag, add an           |
    |                |          |               |   exclamation mark in     |
    |                |          |               |   front of it             |
    +----------------+----------+---------------+---------------------------+
    | ``assignee``   | string   | Optional      | | Filter the issues       |
    |                |          |               |   by assignee             |
    +----------------+----------+---------------+---------------------------+
    | ``author``     | string   | Optional      | | Filter the issues       |
    |                |          |               |   by creator              |
    +----------------+----------+---------------+---------------------------+

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
          "issues": [
            {
              "assignee": null,
              "blocks": [],
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

    repo = pagure.lib.get_project(SESSION, repo, user=username)

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

    # Hide private tickets
    private = False
    # If user is authenticated, show him/her his/her private tickets
    if api_authenticated():
        if repo != flask.g.token.project:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK)
        private = flask.g.fas_user.username
    # If user is repo admin, show all tickets included the private ones
    if is_repo_admin(repo):
        private = None

    if status is not None:
        if status.lower() == 'closed':
            issues = pagure.lib.search_issues(
                SESSION,
                repo,
                closed=True,
                tags=tags,
                assignee=assignee,
                author=author,
                private=private,
            )
        else:
            issues = pagure.lib.search_issues(
                SESSION,
                repo,
                status=status,
                tags=tags,
                assignee=assignee,
                author=author,
                private=private,
            )
    else:
        issues = pagure.lib.search_issues(
            SESSION, repo, status='Open', tags=tags, assignee=assignee,
            author=author, private=private)

    jsonout = flask.jsonify({
        'issues': [issue.to_json(public=True) for issue in issues],
        'args': {
            'status': status,
            'tags': tags,
            'assignee': assignee,
            'author': author,
        }
    })
    return jsonout


@API.route('/<repo>/issue/<issueid>')
@API.route('/fork/<username>/<repo>/issue/<issueid>')
@api_login_optional()
@api_method
def api_view_issue(repo, issueid, username=None):
    """
    Issue information
    -----------------
    Retrieve information of a specific issue.

    ::

        GET /api/0/<repo>/issue/<issue id>

    ::

        GET /api/0/fork/<username>/<repo>/issue/<issue id>

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
          "depends": [],
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

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    issue_id = issue_uid = None
    try:
        issue_id = int(issueid)
    except:
        issue_uid = issueid

    issue = pagure.lib.search_issues(
        SESSION, repo, issueid=issue_id, issueuid=issue_uid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOISSUE)

    if api_authenticated():
        if repo != flask.g.token.project:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK)

    if issue.private and not is_repo_admin(repo) \
            and (not api_authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EISSUENOTALLOWED)

    jsonout = flask.jsonify(
        issue.to_json(public=True, with_comments=comments))
    return jsonout


@API.route('/<repo>/issue/<issue_uid>/comment/<int:commentid>')
@API.route('/fork/<username>/<repo>/issue/<issue_uid>/comment/<int:commentid>')
@api_login_optional()
@api_method
def api_view_issue_comment(repo, issue_uid, commentid, username=None):
    """
    Comment of a ticket
    -------------------
    Retrieve a specific comment of a ticket.

    ::

        GET /api/0/<repo>/issue/<issue uid>/comment/<comment id>

    ::

        GET /api/0/fork/<username>/<repo>/issue/<issue uid>/comment/<comment id>

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "avatar_url": "https://seccdn.libravatar.org/avatar/...?s=16&d=retro",
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

    comment = pagure.lib.get_issue_comment(SESSION, issue_uid, commentid)

    if comment is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not comment.issue.project.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    if api_authenticated():
        if repo != flask.g.token.project:
            raise pagure.exceptions.APIError(
                401, error_code=APIERROR.EINVALIDTOK)

    if comment.issue.private and not is_repo_admin(comment.issue.project) \
            and (not api_authenticated() or
                 not comment.issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EISSUENOTALLOWED)


    output = comment.to_json(public=True)
    output['avatar_url'] = pagure.lib.avatar_url(comment.user.user, size=16)
    output['comment_date'] = comment.date_created.strftime('%Y-%m-%d %H:%M')
    jsonout = flask.jsonify(output)
    return jsonout



@API.route('/<repo>/issue/<int:issueid>/status', methods=['POST'])
@API.route('/fork/<username>/<repo>/<int:issueid>/status', methods=['POST'])
@api_login_required(acls=['issue_change_status'])
@api_method
def api_change_status_issue(repo, issueid, username=None):
    """
    Change issue status
    -------------------
    Change the status of an issue.

    ::

        POST /api/0/<repo>/issue/<issue id>/status

    ::

        POST /api/0/fork/<username>/<repo>/issue/<issue id>/status

    Input
    ^^^^^

    +--------------+----------+---------------+-------------------------------+
    | Key          | Type     | Optionality   | Description                   |
    +==============+==========+===============+===============================+
    | ``status``   | string   | Mandatory     | The new status of the issue   |
    +--------------+----------+---------------+-------------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "Successfully edited issue #1"
        }

    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    if repo != flask.g.token.project:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOISSUE)

    if issue.private and not is_repo_admin(repo) \
            and (not api_authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(
            403, error_code=APIERROR.EISSUENOTALLOWED)

    status = pagure.lib.get_issue_statuses(SESSION)
    form = pagure.forms.StatusForm(status=status, csrf_enabled=False)
    if form.validate_on_submit():
        new_status = form.status.data
        try:
            # Update status
            message = pagure.lib.edit_issue(
                SESSION,
                issue=issue,
                status=new_status,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
            )
            SESSION.commit()
            if message:
                output['message'] = message
            else:
                output['message'] = 'No changes'
        except pagure.exceptions.PagureException, err:
            raise pagure.exceptions.APIError(
                400, error_code=APIERROR.ENOCODE, error=str(err))
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    jsonout = flask.jsonify(output)
    return jsonout


@API.route('/<repo>/issue/<int:issueid>/comment', methods=['POST'])
@API.route('/fork/<username>/<repo>/<int:issueid>/comment', methods=['POST'])
@api_login_required(acls=['issue_comment'])
@api_method
def api_comment_issue(repo, issueid, username=None):
    """
    Comment to an issue
    -------------------
    Add a comment to an issue.

    ::

        POST /api/0/<repo>/issue/<issue id>/comment

    ::

        POST /api/0/fork/<username>/<repo>/issue/<issue id>/comment

    Input
    ^^^^^

    +---------------+----------+---------------+---------------------------+
    | Key           | Type     | Optionality   | Description               |
    +===============+==========+===============+===========================+
    | ``comment``   | string   | Mandatory     | | The comment to add to   |
    |               |          |               |   the issue               |
    +---------------+----------+---------------+---------------------------+

    Sample response
    ^^^^^^^^^^^^^^^

    ::

        {
          "message": "Comment added"
        }

    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    if repo.fullname != flask.g.token.project.fullname:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOISSUE)

    if issue.private and not is_repo_admin(repo) \
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
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    jsonout = flask.jsonify(output)
    return jsonout
