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
from pagure import APP, SESSION, is_repo_admin, authenticated
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
    This endpoint can be used to open an issue on a project

    ::

        /api/0/<repo>/new_issue

        /api/0/fork/<username>/<repo>/new_issue

    Accepts POST queries only.

    :arg title: The title of the issue/ticket to create
    :arg content: The content of the issue to create (ie the description of
        the problem)
    :arg private: A boolean specifying whether this issue is private or not

    Sample response:

    ::

        {
          "message": "Issue created"
        }

    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    if repo != flask.g.token.project:
        raise pagure.exceptions.APIError(401, error_code=APIERROR.EINVALIDTOK)

    status = pagure.lib.get_issue_statuses(SESSION)
    form = pagure.forms.IssueForm(status=status, csrf_enabled=False)
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
            SESSION.commit()
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
                SESSION.commit()

            output['message'] = 'Issue created'
        except SQLAlchemyError, err:  # pragma: no cover
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/<repo>/issues')
@API.route('/fork/<username>/<repo>/issues')
@api_login_optional()
@api_method
def api_view_issues(repo, username=None):
    """
    List project's issues
    ---------------------
    This endpoint can be used to retrieve the list of all issues of the
    specified project

    ::

        /api/0/<repo>/issues

        /api/0/fork/<username>/<repo>/issues

    Accepts GET queries only.

    :kwarg status: The status of the issues to return, default to 'Open'
    :kwarg tags: One or more tags to filter the issues returned.
        If you want to wish to filter for issues not having a specific tag
        you can mark the tag with an exclamation mark in front of it, for
        example to get all the issues not tagged as ``easyfix`` you can
        filter using the tag ``!easyfix``
    :kwarg assignee: Filters the issues returned by the user they are
        assigned to
    :kwarg author: Filters the issues returned by the user that opened the
        issue

    Sample response:

    ::

        {
          "assignee": null,
          "author": null,
          "issues": [
            {
              "assignee": null,
              "blocks": [],
              "comments": [
                {
                  "comment": "bing",
                  "date_created": "1427441560",
                  "id": 379,
                  "parent": null,
                  "user": {
                    "fullname": "PY.C",
                    "name": "pingou"
                  }
                }
              ],
              "content": "bar",
              "date_created": "1427441555",
              "depends": [],
              "id": 1,
              "private": false,
              "status": "Open",
              "tags": [],
              "title": "foo",
              "user": {
                "fullname": "PY.C",
                "name": "pingou"
              }
            },
            {
              "assignee": null,
              "blocks": [],
              "comments": [],
              "content": "report",
              "date_created": "1427442076",
              "depends": [],
              "id": 2,
              "private": false,
              "status": "Open",
              "tags": [],
              "title": "bug",
              "user": {
                "fullname": "PY.C",
                "name": "pingou"
              }
            }
          ],
          "status": null,
          "tags": []
        }

        Second example:

        {
          "assignee": null,
          "author": null,
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
          ],
          "status": "Closed",
          "tags": [
            "0.1"
          ]
        }

    """

    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

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
    if authenticated():
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
        'status': status,
        'tags': tags,
        'assignee': assignee,
        'author': author,
    })
    jsonout.status_code = httpcode
    return jsonout



@API.route('/<repo>/issue/<int:issueid>')
@API.route('/fork/<username>/<repo>/issue/<int:issueid>')
@api_login_optional()
@api_method
def api_view_issue(repo, issueid, username=None):
    """
    Issue information
    -----------------
    This endpoint can be used to retrieve information about a specific
    issue/ticket

    ::

        /api/0/<repo>/issue/<issue id>

        /api/0/fork/<username>/<repo>/issue/<issue id>

    Accepts GET queries only.

    Sample response:

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

    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOPROJECT)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(
            404, error_code=APIERROR.ETRACKERDISABLED)

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=APIERROR.ENOISSUE)

    if issue.private and not is_repo_admin(repo) \
            and (not authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.EISSUEREST)

    jsonout = flask.jsonify(issue.to_json(public=True))
    jsonout.status_code = httpcode
    return jsonout


@API.route('/<repo>/issue/<int:issueid>/status', methods=['POST'])
@API.route('/fork/<username>/<repo>/<int:issueid>/status', methods=['POST'])
@api_login_required(acls=['issue_change_status'])
@api_method
def api_change_status_issue(repo, issueid, username=None):
    """
    Change issue status
    -------------------
    This endpoint can be used to change the status of an issue

    ::

        /api/0/<repo>/issue/<issue id>/status

        /api/0/fork/<username>/<repo>/issue/<issue id>/status

    Accepts POST queries only.

    :arg status: The new status of the specified issue

    Sample response:

    ::

        {
          "message": "Edited successfully issue #1"
        }

    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
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
            and (not authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.EISSUEREST)

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
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/<repo>/issue/<int:issueid>/comment', methods=['POST'])
@API.route('/fork/<username>/<repo>/<int:issueid>/comment', methods=['POST'])
@api_login_required(acls=['issue_comment'])
@api_method
def api_comment_issue(repo, issueid, username=None):
    """
    Comment to an issue
    -------------------
    This endpoint can be used to add a comment to an issue

    ::

        /api/0/<repo>/issue/<issue id>/comment

        /api/0/fork/<username>/<repo>/issue/<issue id>/comment

    Accepts POST queries only.

    :arg comment: The comment to add to the specified issue

    Sample response:

    ::

        {
          "message": "Comment added"
        }

    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
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
            and (not authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(403, error_code=APIERROR.EISSUEREST)

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
            raise pagure.exceptions.APIError(400, error_code=APIERROR.EDBERROR)

    else:
        raise pagure.exceptions.APIError(400, error_code=APIERROR.EINVALIDREQ)

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout
