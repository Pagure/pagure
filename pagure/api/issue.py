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
    API, api_method, api_login_required, api_login_optional, API_ERROR_CODE
)


@API.route('/<repo>/new_issue', methods=['POST'])
@API.route('/fork/<username>/<repo>/new_issue', methods=['POST'])
@api_login_required(acls=['create_issue'])
@api_method
def api_new_issue(repo, username=None):
    """ Create a new issue
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=1)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(404, error_code=2)

    if repo != flask.g.token.project:
        raise pagure.exceptions.APIError(401, error_code=5)

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

            output['message'] = 'issue created'
            output['message'] = 'issue created'
        except SQLAlchemyError, err:  # pragma: no cover
            raise pagure.exceptions.APIError(400, error_code=3)

    else:
        raise pagure.exceptions.APIError(400, error_code=4)

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/<repo>/issue/<int:issueid>')
@API.route('/fork/<username>/<repo>/issue/<int:issueid>')
@api_login_optional()
@api_method
def api_view_issue(repo, issueid, username=None):
    """ List all issues associated to a repo
    """

    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=1)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(404, error_code=2)

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=6)

    if issue.private and not is_repo_admin(repo) \
            and (not authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(403, error_code=7)

    jsonout = flask.jsonify(issue.to_json())
    jsonout.status_code = httpcode
    return jsonout


@API.route('/<repo>/issue/<int:issueid>/status', methods=['POST'])
@API.route('/fork/<username>/<repo>/<int:issueid>/status', methods=['POST'])
@api_login_required(acls=['change_status_issue'])
@api_method
def api_change_status_issue(repo, issueid, username=None):
    """ Change the status of an issue
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=1)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(404, error_code=2)

    if repo != flask.g.token.project:
        raise pagure.exceptions.APIError(401, error_code=5)

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=6)

    if issue.private and not is_repo_admin(repo) \
            and (not authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(403, error_code=7)

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
                400, error_code=0, error=str(err))
        except SQLAlchemyError, err:  # pragma: no cover
            raise pagure.exceptions.APIError(400, error_code=3)

    else:
        raise pagure.exceptions.APIError(400, error_code=4)

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout


@API.route('/<repo>/issue/<int:issueid>/comment', methods=['POST'])
@API.route('/fork/<username>/<repo>/<int:issueid>/comment', methods=['POST'])
@api_login_required(acls=['comment_issue'])
@api_method
def api_comment_issue(repo, issueid, username=None):
    """ Add a comment to an issue
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)
    httpcode = 200
    output = {}

    if repo is None:
        raise pagure.exceptions.APIError(404, error_code=1)

    if not repo.settings.get('issue_tracker', True):
        raise pagure.exceptions.APIError(404, error_code=2)

    if repo.fullname != flask.g.token.project.fullname:
        raise pagure.exceptions.APIError(401, error_code=5)

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        raise pagure.exceptions.APIError(404, error_code=6)

    if issue.private and not is_repo_admin(repo) \
            and (not authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        raise pagure.exceptions.APIError(403, error_code=7)

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
            raise pagure.exceptions.APIError(400, error_code=3)

    else:
        raise pagure.exceptions.APIError(400, error_code=4)

    jsonout = flask.jsonify(output)
    jsonout.status_code = httpcode
    return jsonout
