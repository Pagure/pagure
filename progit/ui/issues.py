#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import os
from math import ceil

import pygit2
from sqlalchemy.exc import SQLAlchemyError
from pygments import highlight
from pygments.lexers import guess_lexer
from pygments.lexers.text import DiffLexer
from pygments.formatters import HtmlFormatter


import progit.doc_utils
import progit.lib
import progit.forms
from progit import (APP, SESSION, LOG, __get_file_in_tree, cla_required,
                    is_repo_admin, authenticated)


## URLs

@APP.route('/<repo>/issue/<int:issueid>/add', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/add',
           methods=('GET', 'POST'))
def add_comment_issue(repo, issueid, username=None):
    ''' Add a comment to an issue. '''
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.issue_tracker:
        flask.abort(404, 'No issue tracker found for this project')

    issue = progit.lib.get_issue(SESSION, repo.id, issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    form = progit.forms.AddIssueCommentForm()
    if form.validate_on_submit():
        comment = form.comment.data

        try:
            message = progit.lib.add_issue_comment(
                SESSION,
                issue=issue,
                comment=comment,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
            )
            SESSION.commit()
            flask.flash(message)
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_issue', username=username, repo=repo.name, issueid=issueid))


@APP.route('/<repo>/issues')
@APP.route('/fork/<username>/<repo>/issues')
def view_issues(repo, username=None):
    """ List all issues associated to a repo
    """
    status = flask.request.args.get('status', None)
    tags = flask.request.args.getlist('tags', None)

    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.issue_tracker:
        flask.abort(404, 'No issue tracker found for this project')

    if status is not None:
        if status.lower() == 'closed':
            issues = progit.lib.get_issues(
                SESSION, repo, closed=True, tags=tags)
        else:
            issues = progit.lib.get_issues(
                SESSION, repo, status=status, tags=tags)
    else:
        issues = progit.lib.get_issues(
            SESSION, repo, status='Open', tags=tags)

    return flask.render_template(
        'issues.html',
        select='issues',
        repo=repo,
        username=username,
        status=status,
        issues=issues,
    )


@APP.route('/<repo>/new_issue', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/new_issue', methods=('GET', 'POST'))
@cla_required
def new_issue(repo, username=None):
    """ Create a new issue
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    status = progit.lib.get_issue_statuses(SESSION)
    form = progit.forms.IssueForm(status=status)
    if form.validate_on_submit():
        title = form.title.data
        content = form.issue_content.data

        try:
            message = progit.lib.new_issue(
                SESSION,
                repo=repo,
                title=title,
                content=content,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
            )
            SESSION.commit()
            flask.flash(message)
            return flask.redirect(flask.url_for(
                'view_issues', username=username, repo=repo.name))
        except progit.exceptions.ProgitException, err:
            flask.flash(str(err), 'error')
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')

    return flask.render_template(
        'new_issue.html',
        select='issues',
        form=form,
        repo=repo,
        username=username,
    )


@APP.route('/<repo>/issue/<int:issueid>', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>',
           methods=('GET', 'POST'))
def view_issue(repo, issueid, username=None):
    """ List all issues associated to a repo
    """

    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.issue_tracker:
        flask.abort(404, 'No issue tracker found for this project')

    issue = progit.lib.get_issue(SESSION, repo.id, issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    status = progit.lib.get_issue_statuses(SESSION)

    form_comment = progit.forms.AddIssueCommentForm()
    form = None
    if authenticated() and is_repo_admin(repo):
        form = progit.forms.UpdateIssueStatusForm(status=status)

        if form.validate_on_submit():
            try:
                message = progit.lib.edit_issue(
                    SESSION,
                    issue=issue,
                    status=form.status.data,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                )
                SESSION.commit()
                flask.flash(message)
                url = flask.url_for(
                    'view_issue', username=username, repo=repo.name,
                    issueid=issueid)
                return flask.redirect(url)
            except SQLAlchemyError, err:  # pragma: no cover
                SESSION.rollback()
                flask.flash(str(err), 'error')
        elif flask.request.method == 'GET':
            form.status.data = issue.status

    return flask.render_template(
        'issue.html',
        select='issues',
        repo=repo,
        username=username,
        issue=issue,
        issueid=issueid,
        form=form,
        form_comment=form_comment,
    )


@APP.route('/<repo>/issue/<int:issueid>/edit', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/edit',
           methods=('GET', 'POST'))
@cla_required
def edit_issue(repo, issueid, username=None):
    """ Edit the specified issue
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.issue_tracker:
        flask.abort(404, 'No issue tracker found for this project')

    if not is_repo_admin(repo):
        flask.abort(
            403, 'You are not allowed to edit issues for this project')

    issue = progit.lib.get_issue(SESSION, repo.id, issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    status = progit.lib.get_issue_statuses(SESSION)
    form = progit.forms.IssueForm(status=status)
    if form.validate_on_submit():
        title = form.title.data
        content = form.issue_content.data
        status = form.status.data

        try:
            message = progit.lib.edit_issue(
                SESSION,
                issue=issue,
                title=title,
                content=content,
                status=status,
                ticketfolder=APP.config['TICKETS_FOLDER'],
            )
            SESSION.commit()
            flask.flash(message)
            url = flask.url_for(
                'view_issue', username=username,
                repo=repo.name, issueid=issueid)
            return flask.redirect(url)
        except progit.exceptions.ProgitException, err:
            flask.flash(str(err), 'error')
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')
    elif flask.request.method == 'GET':
        form.title.data = issue.title
        form.issue_content.data = issue.content
        form.status.data = issue.status

    return flask.render_template(
        'new_issue.html',
        select='issues',
        type='edit',
        form=form,
        repo=repo,
        username=username,
        issue=issue,
        issueid=issueid,
    )
