# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

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

import mimetypes

import progit.doc_utils
import progit.lib
import progit.forms
from progit import (APP, SESSION, LOG, __get_file_in_tree, cla_required,
                    is_repo_admin, authenticated)


# URLs

@APP.route('/<repo>/issue/<int:issueid>/update', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/update',
           methods=('GET', 'POST'))
def update_issue(repo, issueid, username=None):
    ''' Add a comment to an issue. '''
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.issue_tracker:
        flask.abort(404, 'No issue tracker found for this project')

    issue = progit.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if issue.private and not is_repo_admin(repo) \
            and (
                not authenticated() or
                not issue.user.user == flask.g.fas_user.username):
        flask.abort(
            403, 'This issue is private and you are not allowed to view it')

    status = progit.lib.get_issue_statuses(SESSION)
    form = progit.forms.UpdateIssueForm(status=status)

    if form.validate_on_submit():
        comment = form.comment.data
        try:
            depends = [
                int(depend.strip())
                for depend in form.depends.data.split(',')
                if depend.strip()]
        except ValueError:
            depends = []

        try:
            blocks = [
                int(block.strip())
                for block in form.blocks.data.split(',')
                if block.strip()]
        except ValueError:
            blocks = []

        assignee = form.assignee.data
        new_status = form.status.data
        tags = [
            tag.strip()
            for tag in form.tag.data.split(',')
            if tag.strip()]

        try:

            # New comment
            if comment:
                message = progit.lib.add_issue_comment(
                    SESSION,
                    issue=issue,
                    comment=comment,
                    user=flask.g.fas_user.username,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                )
                SESSION.commit()
                if message:
                    flask.flash(message)

            # Adjust (add/remove) tags
            messages = progit.lib.update_tags_issue(
                SESSION, issue, tags,
                username=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'])
            for message in messages:
                flask.flash(message)

            # Assign or update assignee of the ticket
            message = progit.lib.add_issue_assignee(
                SESSION,
                issue=issue,
                assignee=assignee or None,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],)
            if message:
                SESSION.commit()
                flask.flash(message)

            # Update status
            if new_status == 'Fixed' and issue.parents:
                for parent in issue.parents:
                    if parent.status == 'Open':
                        flask.flash(
                            'You cannot close a ticket that has ticket '
                            'depending that are still open.',
                            'error')
                        return flask.redirect(flask.url_for(
                            'view_issue', repo=repo.name, username=username,
                            issueid=issueid))

            if new_status in status:
                message = progit.lib.edit_issue(
                    SESSION,
                    issue=issue,
                    status=new_status,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                )
                SESSION.commit()
                if message:
                    flask.flash(message)

            # Update ticket this one depends on
            messages = progit.lib.update_dependency_issue(
                SESSION, issue, depends,
                username=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'])
            for message in messages:
                flask.flash(message)

            # Update ticket(s) depending on this one
            messages = progit.lib.update_blocked_issue(
                SESSION, issue, depends,
                username=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'])
            for message in messages:
                flask.flash(message)

        except progit.exceptions.ProgitException, err:
            SESSION.rollback()
            flask.flash(str(err), 'error')
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_issue', username=username, repo=repo.name, issueid=issueid))


@APP.route('/<repo>/tag/<tag>/edit', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/tag/<tag>/edit', methods=('GET', 'POST'))
@cla_required
def edit_tag(repo, tag, username=None):
    """ Edit the specified tag of a project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to add users to this project')

    form = progit.forms.AddIssueTagForm()
    if form.validate_on_submit():
        new_tag = form.tag.data

        msgs = progit.lib.edit_issue_tags(
            SESSION, repo, tag, new_tag,
            ticketfolder=APP.config['TICKETS_FOLDER']
        )

        try:
            SESSION.commit()
            for msg in msgs:
                flask.flash(msg)
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            LOG.error(err)
            flask.flash('Could not edit tag: %s' % tag, 'error')

        return flask.redirect(flask.url_for(
            '.view_settings', repo=repo.name, username=username)
        )

    return flask.render_template(
        'edit_tag.html',
        form=form,
        username=username,
        repo=repo,
        tag=tag,
    )


@APP.route('/<repo>/droptag/', methods=['POST'])
@APP.route('/fork/<username>/<repo>/droptag/', methods=['POST'])
@cla_required
def remove_tag(repo, username=None):
    """ Remove the specified tag from the project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the users for this project')

    form = progit.forms.AddIssueTagForm()
    if form.validate_on_submit():
        tags = form.tag.data
        tags = [tag.strip() for tag in tags.split(',')]

        msgs = progit.lib.remove_tags(
            SESSION, repo, tags,
            ticketfolder=APP.config['TICKETS_FOLDER']
        )

        try:
            SESSION.commit()
            for msg in msgs:
                flask.flash(msg)
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            LOG.error(err)
            flask.flash(
                'Could not remove tag: %s' % ','.join(tags), 'error')

    return flask.redirect(
        flask.url_for('.view_settings', repo=repo.name, username=username)
    )


@APP.route('/<repo>/issues')
@APP.route('/fork/<username>/<repo>/issues')
def view_issues(repo, username=None):
    """ List all issues associated to a repo
    """
    status = flask.request.args.get('status', None)
    tags = flask.request.args.getlist('tags')
    tags = [tag.strip() for tag in tags if tag.strip()]
    assignee = flask.request.args.get('assignee', None)
    author = flask.request.args.get('author', None)

    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.issue_tracker:
        flask.abort(404, 'No issue tracker found for this project')

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
            issues = progit.lib.search_issues(
                SESSION,
                repo,
                closed=True,
                tags=tags,
                assignee=assignee,
                author=author,
                private=private,
            )
        else:
            issues = progit.lib.search_issues(
                SESSION,
                repo,
                status=status,
                tags=tags,
                assignee=assignee,
                author=author,
                private=private,
            )
    else:
        issues = progit.lib.search_issues(
            SESSION, repo, status='Open', tags=tags, assignee=assignee,
            author=author, private=private)

    tag_list = progit.lib.get_tags_of_project(SESSION, repo)

    return flask.render_template(
        'issues.html',
        select='issues',
        repo=repo,
        username=username,
        tag_list=tag_list,
        status=status,
        issues=issues,
        tags=tags,
        assignee=assignee,
        author=author,
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
        private = form.private.data

        try:
            message = progit.lib.new_issue(
                SESSION,
                repo=repo,
                title=title,
                content=content,
                private=private or False,
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


@APP.route('/<repo>/issue/<int:issueid>')
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>')
def view_issue(repo, issueid, username=None):
    """ List all issues associated to a repo
    """

    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.issue_tracker:
        flask.abort(404, 'No issue tracker found for this project')

    issue = progit.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if issue.private and not is_repo_admin(repo) \
            and (
                not authenticated() or
                not issue.user.user == flask.g.fas_user.username):
        flask.abort(
            403, 'This issue is private and you are not allowed to view it')

    status = progit.lib.get_issue_statuses(SESSION)

    form = progit.forms.UpdateIssueForm(status=status)
    form.status.data = issue.status

    return flask.render_template(
        'issue.html',
        select='issues',
        repo=repo,
        username=username,
        issue=issue,
        issueid=issueid,
        form=form,
        repo_admin=is_repo_admin(repo),
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

    issue = progit.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    status = progit.lib.get_issue_statuses(SESSION)
    form = progit.forms.IssueForm(status=status)
    if form.validate_on_submit():
        title = form.title.data
        content = form.issue_content.data
        status = form.status.data
        private = form.private.data

        try:
            message = progit.lib.edit_issue(
                SESSION,
                issue=issue,
                title=title,
                content=content,
                status=status,
                ticketfolder=APP.config['TICKETS_FOLDER'],
                private=private,
            )
            SESSION.commit()
            flask.flash(message)
            url = flask.url_for(
                'view_issue', username=username,
                repo=repo.name, issueid=issueid)
            return flask.redirect(url)
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')
    elif flask.request.method == 'GET':
        form.title.data = issue.title
        form.issue_content.data = issue.content
        form.status.data = issue.status
        form.private.data = issue.private

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


@APP.route('/<repo>/issue/<int:issueid>/upload', methods=['POST'])
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/upload',
           methods=['POST'])
@cla_required
def upload_issue(repo, issueid, username=None):
    ''' Upload a file to a ticket.
    '''
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.issue_tracker:
        flask.abort(404, 'No issue tracker found for this project')

    if not is_repo_admin(repo):
        flask.abort(
            403, 'You are not allowed to edit issues for this project')

    issue = progit.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    form = progit.forms.UploadFileForm()
    # pylint: disable=E1101
    if form.validate_on_submit():
        filestream = flask.request.files['filestream']
        new_filename = progit.lib.git.add_file_to_git(
            repo=repo,
            issue=issue,
            ticketfolder=APP.config['TICKETS_FOLDER'],
            user=flask.g.fas_user,
            filename=filestream.filename,
            filestream=filestream.stream,
        )
        return flask.jsonify({
            'output': 'ok',
            'filename': new_filename.split('-', 1)[1],
            'filelocation': flask.url_for(
                'view_issue_raw_file',
                repo=repo.name,
                username=username,
                filename=new_filename,
            )
        })
    else:
        return flask.jsonify({'output': 'notok'})


@APP.route('/<repo>/issue/raw/<path:filename>')
@APP.route('/fork/<username>/<repo>/issue/raw/<path:filename>')
def view_issue_raw_file(repo, filename=None, username=None):
    """ Displays the raw content of a file of a commit for the specified
    ticket repo.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = os.path.join(APP.config['TICKETS_FOLDER'], repo.path)

    repo_obj = pygit2.Repository(reponame)

    if repo_obj.is_empty:
        flask.abort(404, 'Empty repo cannot have a file')


    branch = repo_obj.lookup_branch('master')
    commit = branch.get_object()

    mimetype = None
    encoding = None
    if filename:
        content = __get_file_in_tree(
            repo_obj, commit.tree, filename.split('/'))
        if not content or isinstance(content, pygit2.Tree):
            flask.abort(404, 'File not found')

        mimetype, encoding = mimetypes.guess_type(filename)
        data = repo_obj[content.oid].data
    else:
        if commit.parents:
            diff = commit.tree.diff_to_tree()

            parent = repo_obj.revparse_single('%s^' % identifier)
            diff = repo_obj.diff(parent, commit)
        else:
            # First commit in the repo
            diff = commit.tree.diff_to_tree(swap=True)
        data = diff.patch

    if not mimetype and data[:2] == '#!':
        mimetype = 'text/plain'

    if not mimetype:
        if '\0' in data:
            mimetype = 'application/octet-stream'
        else:
            mimetype = 'text/plain'

    if mimetype.startswith('text/') and not encoding:
        encoding = chardet.detect(ktc.to_bytes(data))['encoding']

    headers = {'Content-Type': mimetype}
    if encoding:
        headers['Content-Encoding'] = encoding

    return (data, 200, headers)
