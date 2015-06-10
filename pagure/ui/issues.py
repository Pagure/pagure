# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import os

import pygit2
from sqlalchemy.exc import SQLAlchemyError

import chardet
import kitchen.text.converters as ktc
import mimetypes

import pagure.doc_utils
import pagure.lib
import pagure.forms
from pagure import (APP,  SESSION, REDIS, LOG, __get_file_in_tree,
                    cla_required, is_repo_admin, authenticated)


# pylint: disable=E1101

# URLs

@APP.route('/<repo>/issue/<int:issueid>/update/', methods=['GET', 'POST'])
@APP.route('/<repo>/issue/<int:issueid>/update', methods=['GET', 'POST'])
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/update/',
           methods=['GET', 'POST'])
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/update',
           methods=['GET', 'POST'])
@cla_required
def update_issue(repo, issueid, username=None):
    ''' Add a comment to an issue. '''
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if flask.request.method == 'GET':
        flask.flash('Invalid method: GET', 'error')
        return flask.redirect(flask.url_for(
            'view_issue', username=username, repo=repo.name, issueid=issueid))

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if issue.private and not is_repo_admin(repo) \
            and (not authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        flask.abort(
            403, 'This issue is private and you are not allowed to view it')

    status = pagure.lib.get_issue_statuses(SESSION)
    form = pagure.forms.UpdateIssueForm(status=status)

    if form.validate_on_submit():
        repo_admin = is_repo_admin(repo)

        if flask.request.form.get('drop_comment'):
            commentid = flask.request.form.get('drop_comment')

            comment = pagure.lib.get_issue_comment(
                SESSION, issue.uid, commentid)
            if comment is None or comment.issue.project != repo:
                flask.abort(404, 'Comment not found')

            if (flask.g.fas_user.username != comment.user.username
                    or comment.parent.status != 'Open') \
                    and not is_repo_admin(repo):
                flask.abort(
                    403,
                    'You are not allowed to remove this comment from '
                    'this issue')

            SESSION.delete(comment)
            try:
                SESSION.commit()
                flask.flash('Comment removed')
            except SQLAlchemyError, err:  # pragma: no cover
                SESSION.rollback()
                LOG.error(err)
                flask.flash(
                    'Could not remove the comment: %s' % commentid, 'error')

        comment = form.comment.data
        depends = []
        for depend in form.depends.data.split(','):
            if depend.strip():
                try:
                    depends.append(int(depend.strip()))
                except ValueError:
                    pass

        blocks = []
        for block in form.blocks.data.split(','):
            if block.strip():
                try:
                    blocks.append(int(block.strip()))
                except ValueError:
                    pass

        assignee = form.assignee.data
        new_status = form.status.data
        tags = [
            tag.strip()
            for tag in form.tag.data.split(',')
            if tag.strip()]

        try:

            # New comment
            if comment:
                message = pagure.lib.add_issue_comment(
                    SESSION,
                    issue=issue,
                    comment=comment,
                    user=flask.g.fas_user.username,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                    redis=REDIS,
                )
                SESSION.commit()
                if message:
                    flask.flash(message)

            if repo_admin:
                # Adjust (add/remove) tags
                messages = pagure.lib.update_tags_issue(
                    SESSION, issue, tags,
                    username=flask.g.fas_user.username,
                    ticketfolder=APP.config['TICKETS_FOLDER'],
                    redis=REDIS)
                for message in messages:
                    flask.flash(message)

            # Assign or update assignee of the ticket
            message = pagure.lib.add_issue_assignee(
                SESSION,
                issue=issue,
                assignee=assignee or None,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
                redis=REDIS,
            )
            if message:
                SESSION.commit()
                flask.flash(message)

            if repo_admin:
                # Update status
                if new_status in status:
                    message = pagure.lib.edit_issue(
                        SESSION,
                        issue=issue,
                        status=new_status,
                        user=flask.g.fas_user.username,
                        ticketfolder=APP.config['TICKETS_FOLDER'],
                        redis=REDIS,
                    )
                    SESSION.commit()
                    if message:
                        flask.flash(message)

            # Update ticket this one depends on
            messages = pagure.lib.update_dependency_issue(
                SESSION, repo, issue, depends,
                username=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
                redis=REDIS,
            )
            for message in messages:
                flask.flash(message)

            # Update ticket(s) depending on this one
            messages = pagure.lib.update_blocked_issue(
                SESSION, repo, issue, blocks,
                username=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
                redis=REDIS,
            )
            for message in messages:
                flask.flash(message)

        except pagure.exceptions.PagureException, err:
            SESSION.rollback()
            flask.flash(err.message, 'error')
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_issue', username=username, repo=repo.name, issueid=issueid))


@APP.route('/<repo>/tag/<tag>/edit/', methods=('GET', 'POST'))
@APP.route('/<repo>/tag/<tag>/edit', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/tag/<tag>/edit/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/tag/<tag>/edit', methods=('GET', 'POST'))
@cla_required
def edit_tag(repo, tag, username=None):
    """ Edit the specified tag of a project.
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to edt tags of this project')

    form = pagure.forms.AddIssueTagForm()
    if form.validate_on_submit():
        new_tag = form.tag.data

        msgs = pagure.lib.edit_issue_tags(
            SESSION, repo, tag, new_tag,
            user=flask.g.fas_user.username,
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
            '.view_settings', repo=repo.name, username=username))

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
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to remove tags of this project')

    form = pagure.forms.AddIssueTagForm()
    if form.validate_on_submit():
        tags = form.tag.data
        tags = [tag.strip() for tag in tags.split(',')]

        msgs = pagure.lib.remove_tags(
            SESSION, repo, tags,
            user=flask.g.fas_user.username,
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


@APP.route('/<repo>/issues/')
@APP.route('/<repo>/issues')
@APP.route('/fork/<username>/<repo>/issues/')
@APP.route('/fork/<username>/<repo>/issues')
def view_issues(repo, username=None):
    """ List all issues associated to a repo
    """
    status = flask.request.args.get('status', None)
    tags = flask.request.args.getlist('tags')
    tags = [tag.strip() for tag in tags if tag.strip()]
    assignee = flask.request.args.get('assignee', None)
    author = flask.request.args.get('author', None)

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    # Hide private tickets
    private = False
    # If user is authenticated, show him/her his/her private tickets
    if authenticated():
        private = flask.g.fas_user.username
    # If user is repo admin, show all tickets included the private ones
    if is_repo_admin(repo):
        private = None

    oth_issues = None
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
            oth_issues = pagure.lib.search_issues(
                SESSION,
                repo,
                status='Open',
                tags=tags,
                assignee=assignee,
                author=author,
                private=private,
                count=True,
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
        oth_issues = pagure.lib.search_issues(
            SESSION, repo, closed=True, tags=tags, assignee=assignee,
            author=author, private=private, count=True)

    tag_list = pagure.lib.get_tags_of_project(SESSION, repo)

    return flask.render_template(
        'issues.html',
        select='issues',
        repo=repo,
        username=username,
        tag_list=tag_list,
        status=status,
        issues=issues,
        oth_issues=oth_issues,
        tags=tags,
        assignee=assignee,
        author=author,
    )


@APP.route('/<repo>/new_issue/', methods=('GET', 'POST'))
@APP.route('/<repo>/new_issue', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/new_issue/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/new_issue', methods=('GET', 'POST'))
@cla_required
def new_issue(repo, username=None):
    """ Create a new issue
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    status = pagure.lib.get_issue_statuses(SESSION)
    form = pagure.forms.IssueForm(status=status)
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

            flask.flash('Issue created')
            return flask.redirect(flask.url_for(
                '.view_issue', username=username, repo=repo.name,
                issueid=issue.id))
        except pagure.exceptions.PagureException, err:
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


@APP.route('/<repo>/issue/<int:issueid>/')
@APP.route('/<repo>/issue/<int:issueid>')
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/')
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>')
def view_issue(repo, issueid, username=None):
    """ List all issues associated to a repo
    """

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if issue.private and not is_repo_admin(repo) \
            and (not authenticated() or
                 not issue.user.user == flask.g.fas_user.username):
        flask.abort(
            403, 'This issue is private and you are not allowed to view it')

    status = pagure.lib.get_issue_statuses(SESSION)

    form = pagure.forms.UpdateIssueForm(status=status)
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


if APP.config['REDIS_EVENTSOURCE']:
    @APP.route('/<repo>/issue/<int:issueid>/stream')
    @APP.route('/fork/<username>/<repo>/issue/<int:issueid>/stream')
    def stream_issue(repo, issueid, username=None):
        """ Streams the changes made to an issue live
        """

        repo = pagure.lib.get_project(SESSION, repo, user=username)

        if repo is None:
            flask.abort(404, 'Project not found')

        if not repo.settings.get('issue_tracker', True):
            flask.abort(404, 'No issue tracker found for this project')

        issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

        if issue is None or issue.project != repo:
            flask.abort(404, 'Issue not found')

        if issue.private and not is_repo_admin(repo) \
                and (not authenticated() or
                     not issue.user.user == flask.g.fas_user.username):
            flask.abort(
                403, 'This issue is private and you are not allowed to view it')

        pubsub = REDIS.pubsub()
        pubsub.subscribe(issue.uid)
        def event_stream(pubsub):
            for message in pubsub.listen():
                yield 'data: %s\n\n' % message['data']

        return flask.Response(
            event_stream(pubsub),
            mimetype="text/event-stream")


@APP.route('/<repo>/issue/<int:issueid>/drop', methods=['POST'])
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/drop',
           methods=['POST'])
def delete_issue(repo, issueid, username=None):
    """ Delete the specified issue
    """

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to remove tickets of this project')

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        try:
            pagure.lib.drop_issue(
                SESSION, issue,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
            )
            SESSION.commit()
            flask.flash('Issue deleted')
            return flask.redirect(flask.url_for(
                'view_issues', username=username, repo=repo.name))
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash('Could not delete the issue', 'error')

    return flask.redirect(flask.url_for(
        'view_issue', username=username, repo=repo.name, issueid=issueid))


@APP.route('/<repo>/issue/<int:issueid>/edit/', methods=('GET', 'POST'))
@APP.route('/<repo>/issue/<int:issueid>/edit', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/edit/',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/issue/<int:issueid>/edit',
           methods=('GET', 'POST'))
@cla_required
def edit_issue(repo, issueid, username=None):
    """ Edit the specified issue
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    if not (is_repo_admin(repo)
            or flask.g.fas_user.username == issue.user.username):
        flask.abort(
            403, 'You are not allowed to edit issues for this project')

    status = pagure.lib.get_issue_statuses(SESSION)
    form = pagure.forms.IssueForm(status=status)
    if form.validate_on_submit():
        title = form.title.data
        content = form.issue_content.data
        status = form.status.data
        private = form.private.data

        try:
            message = pagure.lib.edit_issue(
                SESSION,
                issue=issue,
                title=title,
                content=content,
                status=status,
                user=flask.g.fas_user.username,
                ticketfolder=APP.config['TICKETS_FOLDER'],
                private=private,
                redis=REDIS,
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
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    issue = pagure.lib.search_issues(SESSION, repo, issueid=issueid)

    if issue is None or issue.project != repo:
        flask.abort(404, 'Issue not found')

    form = pagure.forms.UploadFileForm()
    # pylint: disable=E1101
    if form.validate_on_submit():
        filestream = flask.request.files['filestream']
        new_filename = pagure.lib.git.add_file_to_git(
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
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    reponame = os.path.join(APP.config['TICKETS_FOLDER'], repo.path)

    repo_obj = pygit2.Repository(reponame)

    if repo_obj.is_empty:
        flask.abort(404, 'Empty repo cannot have a file')

    branch = repo_obj.lookup_branch('master')
    commit = branch.get_object()

    mimetype = None
    encoding = None

    content = __get_file_in_tree(
        repo_obj, commit.tree, filename.split('/'))
    if not content or isinstance(content, pygit2.Tree):
        flask.abort(404, 'File not found')

    mimetype, encoding = mimetypes.guess_type(filename)
    data = repo_obj[content.oid].data

    if not data:
        flask.abort(404, 'No content found')

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
