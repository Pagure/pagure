# -*- coding: utf-8 -*-

"""
 (c) 2014-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-many-return-statements
# pylint: disable=too-many-branches
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# pylint: disable=too-many-lines


import logging
import os
from math import ceil

import flask
import pygit2
from sqlalchemy.exc import SQLAlchemyError

import pagure
import pagure.doc_utils
import pagure.exceptions
import pagure.lib
import pagure.lib.git
import pagure.lib.tasks
import pagure.forms
from pagure import (APP, SESSION, login_required, __get_file_in_tree)


_log = logging.getLogger(__name__)


def _get_parent_repo_path(repo):
    """ Return the path of the parent git repository corresponding to the
    provided Repository object from the DB.
    """
    if repo.parent:
        parentpath = os.path.join(APP.config['GIT_FOLDER'], repo.parent.path)
    else:
        parentpath = os.path.join(APP.config['GIT_FOLDER'], repo.path)

    return parentpath


def _get_parent_request_repo_path(repo):
    """ Return the path of the parent git repository corresponding to the
    provided Repository object from the DB.
    """
    if repo.parent:
        parentpath = os.path.join(
            APP.config['REQUESTS_FOLDER'], repo.parent.path)
    else:
        parentpath = os.path.join(APP.config['REQUESTS_FOLDER'], repo.path)

    return parentpath


@APP.route('/<repo>/pull-requests/')
@APP.route('/<repo>/pull-requests')
@APP.route('/<namespace>/<repo>/pull-requests/')
@APP.route('/<namespace>/<repo>/pull-requests')
@APP.route('/fork/<username>/<repo>/pull-requests/')
@APP.route('/fork/<username>/<repo>/pull-requests')
@APP.route('/fork/<username>/<namespace>/<repo>/pull-requests/')
@APP.route('/fork/<username>/<namespace>/<repo>/pull-requests')
def request_pulls(repo, username=None, namespace=None):
    """ Create a pull request with the changes from the fork into the project.
    """
    status = flask.request.args.get('status', 'Open')
    assignee = flask.request.args.get('assignee', None)
    author = flask.request.args.get('author', None)

    repo = flask.g.repo

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    if str(status).lower() in ['false', '0']:
        status = False
    elif str(status).lower() in ['all']:
        status = None

    if str(status).lower() in ['true', '1', 'open']:
        requests = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            status=True,
            assignee=assignee,
            author=author,
            offset=flask.g.offset,
            limit=flask.g.limit)
        requests_cnt = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            status=True,
            assignee=assignee,
            author=author,
            count=True)
        oth_requests = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            status=False,
            assignee=assignee,
            author=author,
            count=True)
    else:
        requests = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            assignee=assignee,
            author=author,
            status=status,
            offset=flask.g.offset,
            limit=flask.g.limit)
        requests_cnt = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            assignee=assignee,
            author=author,
            status=status,
            count=True)
        oth_requests = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            status=True,
            assignee=assignee,
            author=author,
            count=True)

    repo_obj = flask.g.repo_obj
    if not repo_obj.is_empty and not repo_obj.head_is_unborn:
        head = repo_obj.head.shorthand
    else:
        head = 'master'

    total_page = 1
    if requests_cnt:
        total_page = int(ceil(requests_cnt / float(flask.g.limit)))

    return flask.render_template(
        'requests.html',
        select='requests',
        repo=repo,
        username=username,
        requests=requests,
        requests_cnt=requests_cnt,
        oth_requests=oth_requests,
        status=status,
        assignee=assignee,
        author=author,
        form=pagure.forms.ConfirmationForm(),
        head=head,
        total_page=total_page,
    )


@APP.route('/<repo>/pull-request/<int:requestid>/')
@APP.route('/<repo>/pull-request/<int:requestid>')
@APP.route('/<namespace>/<repo>/pull-request/<int:requestid>/')
@APP.route('/<namespace>/<repo>/pull-request/<int:requestid>')
@APP.route('/fork/<username>/<repo>/pull-request/<int:requestid>/')
@APP.route('/fork/<username>/<repo>/pull-request/<int:requestid>')
@APP.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/')
@APP.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>')
def request_pull(repo, requestid, username=None, namespace=None):
    """ Create a pull request with the changes from the fork into the project.
    """
    repo = flask.g.repo

    _log.info('Viewing pull Request #%s repo: %s', requestid, repo.fullname)

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if request.remote:
        repopath = pagure.get_remote_repo_path(
            request.remote_git, request.branch_from)
        parentpath = pagure.get_repo_path(request.project)
    else:
        repo_from = request.project_from
        repopath = pagure.get_repo_path(repo_from)
        parentpath = _get_parent_repo_path(repo_from)

    repo_obj = pygit2.Repository(repopath)
    orig_repo = pygit2.Repository(parentpath)

    diff_commits = []
    diff = None
    # Closed pull-request
    if request.status != 'Open':
        commitid = request.commit_stop
        try:
            for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
                diff_commits.append(commit)
                if commit.oid.hex == request.commit_start:
                    break
        except KeyError:
            # This happens when repo.walk() cannot find commitid
            pass

        if diff_commits:
            diff = repo_obj.diff(
                repo_obj.revparse_single(diff_commits[-1].parents[0].oid.hex),
                repo_obj.revparse_single(diff_commits[0].oid.hex)
            )
    else:
        try:
            diff_commits, diff = pagure.lib.git.diff_pull_request(
                SESSION, request, repo_obj, orig_repo,
                requestfolder=APP.config['REQUESTS_FOLDER'])
        except pagure.exceptions.PagureException as err:
            flask.flash(err.message, 'error')
            return flask.redirect(flask.url_for(
                'view_repo', username=username, repo=repo.name,
                namespace=namespace))
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            _log.exception(err)
            flask.flash(
                'Could not update this pull-request in the database',
                'error')

    if diff:
        diff.find_similar()

    form = pagure.forms.ConfirmationForm()

    return flask.render_template(
        'pull_request.html',
        select='requests',
        requestid=requestid,
        repo=repo,
        username=username,
        repo_obj=repo_obj,
        pull_request=request,
        diff_commits=diff_commits,
        diff=diff,
        mergeform=form,
        subscribers=pagure.lib.get_watch_list(SESSION, request),
    )


@APP.route('/<repo>/pull-request/<int:requestid>.patch')
@APP.route('/<namespace>/<repo>/pull-request/<int:requestid>.patch')
@APP.route('/fork/<username>/<repo>/pull-request/<int:requestid>.patch')
@APP.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>.patch')
def request_pull_patch(repo, requestid, username=None, namespace=None):
    """ Returns the commits from the specified pull-request as patches.
    """
    repo = flask.g.repo

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if request.remote:
        repopath = pagure.get_remote_repo_path(
            request.remote_git, request.branch_from)
        parentpath = pagure.get_repo_path(request.project)
    else:
        repo_from = request.project_from
        repopath = pagure.get_repo_path(repo_from)
        parentpath = _get_parent_repo_path(repo_from)

    repo_obj = pygit2.Repository(repopath)
    orig_repo = pygit2.Repository(parentpath)

    branch = repo_obj.lookup_branch(request.branch_from)
    commitid = None
    if branch:
        commitid = branch.get_object().hex

    diff_commits = []
    if request.status != 'Open':
        commitid = request.commit_stop
        try:
            for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
                diff_commits.append(commit)
                if commit.oid.hex == request.commit_start:
                    break
        except KeyError:
            # This happens when repo.walk() cannot find commitid
            pass
    else:
        try:
            diff_commits = pagure.lib.git.diff_pull_request(
                SESSION, request, repo_obj, orig_repo,
                requestfolder=APP.config['REQUESTS_FOLDER'],
                with_diff=False)
        except pagure.exceptions.PagureException as err:
            flask.flash(err.message, 'error')
            return flask.redirect(flask.url_for(
                'view_repo', username=username, repo=repo.name,
                namespace=namespace))
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            _log.exception(err)
            flask.flash(
                'Could not update this pull-request in the database',
                'error')

    diff_commits.reverse()
    patch = pagure.lib.git.commit_to_patch(repo_obj, diff_commits)

    return flask.Response(patch, content_type="text/plain;charset=UTF-8")


@APP.route(
    '/<repo>/pull-request/<int:requestid>/edit/', methods=('GET', 'POST'))
@APP.route(
    '/<repo>/pull-request/<int:requestid>/edit', methods=('GET', 'POST'))
@APP.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/edit/',
    methods=('GET', 'POST'))
@APP.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/edit',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/edit/',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/edit',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/edit/',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/edit',
    methods=('GET', 'POST'))
@login_required
def request_pull_edit(repo, requestid, username=None, namespace=None):
    """ Edit the title of a pull-request.
    """

    repo = flask.g.repo

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if request.status != 'Open':
        flask.abort(400, 'Pull-request is already closed')

    if not flask.g.repo_committer \
            and flask.g.fas_user.username != request.user.username:
        flask.abort(403, 'You are not allowed to edit this pull-request')

    form = pagure.forms.RequestPullForm()
    if form.validate_on_submit():
        request.title = form.title.data.strip()
        request.initial_comment = form.initial_comment.data.strip()
        SESSION.add(request)
        try:
            SESSION.commit()
            flask.flash('Pull request edited!')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            _log.exception(err)
            flask.flash(
                'Could not edit this pull-request in the database',
                'error')
        return flask.redirect(flask.url_for(
            'request_pull', username=username, namespace=namespace,
            repo=repo.name, requestid=requestid))
    elif flask.request.method == 'GET':
        form.title.data = request.title
        form.initial_comment.data = request.initial_comment

    return flask.render_template(
        'pull_request_title.html',
        select='requests',
        request=request,
        repo=repo,
        username=username,
        form=form,
    )


@APP.route('/<repo>/pull-request/<int:requestid>/comment',
           methods=['POST'])
@APP.route('/<repo>/pull-request/<int:requestid>/comment/<commit>/'
           '<path:filename>/<row>', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/pull-request/<int:requestid>/comment',
           methods=['POST'])
@APP.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/comment/<commit>/'
    '<path:filename>/<row>', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/pull-request/<int:requestid>/comment',
           methods=['POST'])
@APP.route('/fork/<username>/<repo>/pull-request/<int:requestid>/comment/'
           '<commit>/<path:filename>/<row>', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/'
    'comment', methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/'
    'comment/<commit>/<path:filename>/<row>', methods=('GET', 'POST'))
@login_required
def pull_request_add_comment(
        repo, requestid, commit=None,
        filename=None, row=None, username=None, namespace=None):
    """ Add a comment to a commit in a pull-request.
    """
    repo = flask.g.repo

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    is_js = flask.request.args.get('js', False)
    tree_id = flask.request.args.get('tree_id') or None

    form = pagure.forms.AddPullRequestCommentForm()
    form.commit.data = commit
    form.filename.data = filename
    form.requestid.data = requestid
    form.row.data = row
    form.tree_id.data = tree_id

    if form.validate_on_submit():
        comment = form.comment.data

        try:
            message = pagure.lib.add_pull_request_comment(
                SESSION,
                request=request,
                commit=commit,
                tree_id=tree_id,
                filename=filename,
                row=row,
                comment=comment,
                user=flask.g.fas_user.username,
                requestfolder=APP.config['REQUESTS_FOLDER'],
                trigger_ci=APP.config['TRIGGER_CI'],
            )
            SESSION.commit()
            if not is_js:
                flask.flash(message)
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            _log.exception(err)
            if is_js:
                return 'error'
            else:
                flask.flash(str(err), 'error')

        if is_js:
            return 'ok'
        return flask.redirect(flask.url_for(
            'request_pull', username=username, namespace=namespace,
            repo=repo.name, requestid=requestid))

    if is_js and flask.request.method == 'POST':
        return 'failed'

    return flask.render_template(
        'pull_request_comment.html',
        select='requests',
        requestid=requestid,
        repo=repo,
        username=username,
        commit=commit,
        tree_id=tree_id,
        filename=filename,
        row=row,
        form=form,
    )


@APP.route('/<repo>/pull-request/<int:requestid>/comment/drop',
           methods=['POST'])
@APP.route('/<namespace>/<repo>/pull-request/<int:requestid>/comment/drop',
           methods=['POST'])
@APP.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/comment/drop',
    methods=['POST'])
@APP.route(
    '/fork/<namespace>/<username>/<repo>/pull-request/<int:requestid>/'
    'comment/drop', methods=['POST'])
@login_required
def pull_request_drop_comment(
        repo, requestid, username=None, namespace=None):
    """ Delete a comment of a pull-request.
    """
    repo = flask.g.repo

    if not repo:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if flask.request.form.get('edit_comment'):
        commentid = flask.request.form.get('edit_comment')
        form = pagure.forms.EditCommentForm()
        if form.validate_on_submit():
            return pull_request_edit_comment(
                repo.name, requestid, commentid, username=username)

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():

        if flask.request.form.get('drop_comment'):
            commentid = flask.request.form.get('drop_comment')

            comment = pagure.lib.get_request_comment(
                SESSION, request.uid, commentid)
            if comment is None or comment.pull_request.project != repo:
                flask.abort(404, 'Comment not found')

            if (flask.g.fas_user.username != comment.user.username
                    or comment.parent.status is False) \
                    and not flask.g.repo_committer:
                flask.abort(
                    403,
                    'You are not allowed to remove this comment from '
                    'this issue')

            SESSION.delete(comment)
            try:
                SESSION.commit()
                flask.flash('Comment removed')
            except SQLAlchemyError as err:  # pragma: no cover
                SESSION.rollback()
                _log.error(err)
                flask.flash(
                    'Could not remove the comment: %s' % commentid, 'error')

    return flask.redirect(flask.url_for(
        'request_pull', username=username, namespace=namespace,
        repo=repo.name, requestid=requestid))


@APP.route(
    '/<repo>/pull-request/<int:requestid>/comment/<int:commentid>/edit',
    methods=('GET', 'POST'))
@APP.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/comment/'
    '<int:commentid>/edit', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/comment'
    '/<int:commentid>/edit', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/'
    '<int:requestid>/comment/<int:commentid>/edit',
    methods=('GET', 'POST'))
@login_required
def pull_request_edit_comment(
        repo, requestid, commentid, username=None, namespace=None):
    """Edit comment of a pull request
    """
    is_js = flask.request.args.get('js', False)

    project = flask.g.repo

    if not project.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=project.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    comment = pagure.lib.get_request_comment(
        SESSION, request.uid, commentid)

    if comment is None or comment.parent.project != project:
        flask.abort(404, 'Comment not found')

    if (flask.g.fas_user.username != comment.user.username
            or comment.parent.status != 'Open') \
            and not flask.g.repo_committer:
        flask.abort(403, 'You are not allowed to edit the comment')

    form = pagure.forms.EditCommentForm()

    if form.validate_on_submit():

        updated_comment = form.update_comment.data
        try:
            message = pagure.lib.edit_comment(
                SESSION,
                parent=request,
                comment=comment,
                user=flask.g.fas_user.username,
                updated_comment=updated_comment,
                folder=APP.config['REQUESTS_FOLDER'],
            )
            SESSION.commit()
            if not is_js:
                flask.flash(message)
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            _log.error(err)
            if is_js:
                return 'error'
            else:
                flask.flash(
                    'Could not edit the comment: %s' % commentid, 'error')

        if is_js:
            return 'ok'
        return flask.redirect(flask.url_for(
            'request_pull', username=username, namespace=namespace,
            repo=project.name, requestid=requestid))

    if is_js and flask.request.method == 'POST':
        return 'failed'

    return flask.render_template(
        'comment_update.html',
        select='requests',
        requestid=requestid,
        repo=project,
        username=username,
        form=form,
        comment=comment,
        is_js=is_js,
    )


@APP.route('/<repo>/pull-request/<int:requestid>/merge', methods=['POST'])
@APP.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/merge',
    methods=['POST'])
@APP.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/merge',
    methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/merge',
    methods=['POST'])
@login_required
def merge_request_pull(repo, requestid, username=None, namespace=None):
    """ Create a pull request with the changes from the fork into the project.
    """

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.flash('Invalid input submitted', 'error')
        return flask.redirect(flask.url_for(
            'request_pull', repo=repo, requestid=requestid,
            username=username, namespace=namespace))

    repo = flask.g.repo

    _log.info(
        'called merge_request_pull for repo: %s - requestid: %s',
        repo.fullname, requestid)

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if not flask.g.repo_committer:
        flask.abort(
            403,
            'You are not allowed to merge pull-request for this project')

    if repo.settings.get('Only_assignee_can_merge_pull-request', False):
        if not request.assignee:
            flask.flash(
                'This request must be assigned to be merged', 'error')
            return flask.redirect(flask.url_for(
                'request_pull', username=username, namespace=namespace,
                repo=repo.name, requestid=requestid))
        if request.assignee.username != flask.g.fas_user.username:
            flask.flash('Only the assignee can merge this review', 'error')
            return flask.redirect(flask.url_for(
                'request_pull', username=username, namespace=namespace,
                repo=repo.name, requestid=requestid))

    threshold = repo.settings.get('Minimum_score_to_merge_pull-request', -1)
    if threshold > 0 and int(request.score) < int(threshold):
        flask.flash(
            'This request does not have the minimum review score necessary '
            'to be merged', 'error')
        return flask.redirect(flask.url_for(
            'request_pull', username=username, namespace=namespace,
            repo=repo.name, requestid=requestid))

    _log.info('All checks in the controller passed')

    try:
        taskid = pagure.lib.tasks.merge_pull_request.delay(
            repo.name, namespace, username, requestid,
            flask.g.fas_user.username)
        return pagure.wait_for_task(taskid)
    except pygit2.GitError as err:
        _log.info('GitError exception raised')
        flask.flash(str(err.message), 'error')
        return flask.redirect(flask.url_for(
            'request_pull', repo=repo.name, requestid=requestid,
            username=username, namespace=namespace))
    except pagure.exceptions.PagureException as err:
        _log.info('PagureException exception raised')
        flask.flash(str(err), 'error')
        return flask.redirect(flask.url_for(
            'request_pull', repo=repo.name, requestid=requestid,
            username=username, namespace=namespace))

    _log.info('All fine, returning')
    return flask.redirect(flask.url_for(
        'view_repo', repo=repo.name, username=username, namespace=namespace))


@APP.route('/<repo>/pull-request/cancel/<int:requestid>',
           methods=['POST'])
@APP.route('/<namespace>/<repo>/pull-request/cancel/<int:requestid>',
           methods=['POST'])
@APP.route('/fork/<username>/<repo>/pull-request/cancel/<int:requestid>',
           methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/cancel/<int:requestid>',
    methods=['POST'])
@login_required
def cancel_request_pull(repo, requestid, username=None, namespace=None):
    """ Cancel a pull request.
    """

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():

        if not flask.g.repo.settings.get('pull_requests', True):
            flask.abort(404, 'No pull-requests found for this project')

        request = pagure.lib.search_pull_requests(
            SESSION, project_id=flask.g.repo.id, requestid=requestid)

        if not request:
            flask.abort(404, 'Pull-request not found')

        if not flask.g.repo_committer \
                and not flask.g.fas_user.username == request.user.username:
            flask.abort(
                403,
                'You are not allowed to cancel pull-request for this project')

        pagure.lib.close_pull_request(
            SESSION, request, flask.g.fas_user.username,
            requestfolder=APP.config['REQUESTS_FOLDER'],
            merged=False)
        try:
            SESSION.commit()
            flask.flash('Pull request canceled!')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            _log.exception(err)
            flask.flash(
                'Could not update this pull-request in the database',
                'error')

    else:
        flask.flash('Invalid input submitted', 'error')

    return flask.redirect(flask.url_for(
        'view_repo', repo=repo, username=username, namespace=namespace))


@APP.route(
    '/<repo>/pull-request/<int:requestid>/assign', methods=['POST'])
@APP.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/assign',
    methods=['POST'])
@APP.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/assign',
    methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/assign',
    methods=['POST'])
@login_required
def set_assignee_requests(repo, requestid, username=None, namespace=None):
    ''' Assign a pull-request. '''
    repo = flask.g.repo

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-request allowed on this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if request.status != 'Open':
        flask.abort(403, 'Pull-request closed')

    if not flask.g.repo_committer:
        flask.abort(403, 'You are not allowed to assign this pull-request')

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        try:
            # Assign or update assignee of the ticket
            message = pagure.lib.add_pull_request_assignee(
                SESSION,
                request=request,
                assignee=flask.request.form.get('user', '').strip() or None,
                user=flask.g.fas_user.username,
                requestfolder=APP.config['REQUESTS_FOLDER'],)
            if message:
                SESSION.commit()
                flask.flash(message)
        except pagure.exceptions.PagureException as err:
            SESSION.rollback()
            flask.flash(err.message, 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            _log.exception(err)
            flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'request_pull', username=username, namespace=namespace,
        repo=repo.name, requestid=requestid))


# Specific actions


@APP.route('/do_fork/<repo>', methods=['POST'])
@APP.route('/do_fork/<namespace>/<repo>', methods=['POST'])
@APP.route('/do_fork/fork/<username>/<repo>', methods=['POST'])
@APP.route('/do_fork/fork/<username>/<namespace>/<repo>', methods=['POST'])
@login_required
def fork_project(repo, username=None, namespace=None):
    """ Fork the project specified into the user's namespace
    """
    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.abort(400)

    if pagure.lib._get_project(
            SESSION, repo.name, user=flask.g.fas_user.username,
            namespace=namespace):
        return flask.redirect(flask.url_for(
            'view_repo', repo=repo.name, username=flask.g.fas_user.username,
            namespace=namespace))

    try:
        taskid = pagure.lib.fork_project(
            session=SESSION,
            repo=repo,
            gitfolder=APP.config['GIT_FOLDER'],
            docfolder=APP.config['DOCS_FOLDER'],
            ticketfolder=APP.config['TICKETS_FOLDER'],
            requestfolder=APP.config['REQUESTS_FOLDER'],
            user=flask.g.fas_user.username)

        SESSION.commit()
        return pagure.wait_for_task(taskid)
    except pagure.exceptions.PagureException as err:
        flask.flash(str(err), 'error')
    except SQLAlchemyError as err:  # pragma: no cover
        SESSION.rollback()
        flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_repo', repo=repo.name, username=username, namespace=namespace
    ))


@APP.route('/<repo>/diff/<path:branch_to>..<path:branch_from>/',
           methods=('GET', 'POST'))
@APP.route('/<repo>/diff/<path:branch_to>..<path:branch_from>',
           methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/diff/<path:branch_to>..<path:branch_from>/',
           methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/diff/<path:branch_to>..<path:branch_from>',
           methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<repo>/diff/<path:branch_to>..<path:branch_from>/',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<repo>/diff/<path:branch_to>..<path:branch_from>',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/diff/'
    '<path:branch_to>..<path:branch_from>/', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/diff/'
    '<path:branch_to>..<path:branch_from>', methods=('GET', 'POST'))
def new_request_pull(
        repo, branch_to, branch_from, username=None, namespace=None):
    """ Create a pull request with the changes from the fork into the project.
    """
    branch_to = flask.request.values.get('branch_to', branch_to)

    repo = flask.g.repo

    parent = repo
    if repo.parent:
        parent = repo.parent

    if not parent.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-request allowed on this project')

    repo_obj = flask.g.repo_obj

    parentpath = _get_parent_repo_path(repo)
    orig_repo = pygit2.Repository(parentpath)

    try:
        diff, diff_commits, orig_commit = pagure.lib.git.get_diff_info(
            repo_obj, orig_repo, branch_from, branch_to)
    except pagure.exceptions.PagureException as err:
        flask.abort(400, str(err))

    repo_committer = flask.g.repo_committer

    form = pagure.forms.RequestPullForm()
    if form.validate_on_submit() and repo_committer:
        try:
            if repo.settings.get(
                    'Enforce_signed-off_commits_in_pull-request', False):
                for commit in diff_commits:
                    if 'signed-off-by' not in commit.message.lower():
                        raise pagure.exceptions.PagureException(
                            'This repo enforces that all commits are '
                            'signed off by their author. ')

            if orig_commit:
                orig_commit = orig_commit.oid.hex

            initial_comment = form.initial_comment.data.strip() or None
            commit_start = commit_stop = None
            if diff_commits:
                commit_stop = diff_commits[0].oid.hex
                commit_start = diff_commits[-1].oid.hex
            request = pagure.lib.new_pull_request(
                SESSION,
                repo_to=parent,
                branch_to=branch_to,
                branch_from=branch_from,
                repo_from=repo,
                title=form.title.data,
                initial_comment=initial_comment,
                user=flask.g.fas_user.username,
                requestfolder=APP.config['REQUESTS_FOLDER'],
                commit_start=commit_start,
                commit_stop=commit_stop,
            )

            try:
                SESSION.commit()
            except SQLAlchemyError as err:  # pragma: no cover
                SESSION.rollback()
                _log.exception(err)
                flask.flash(
                    'Could not register this pull-request in the database',
                    'error')

            if not parent.is_fork:
                url = flask.url_for(
                    'request_pull', requestid=request.id,
                    username=None, repo=parent.name, namespace=namespace)
            else:
                url = flask.url_for(
                    'request_pull', requestid=request.id,
                    username=parent.user, repo=parent.name,
                    namespace=namespace)

            return flask.redirect(url)
        except pagure.exceptions.PagureException as err:  # pragma: no cover
            # There could be a PagureException thrown if the flask.g.fas_user
            # wasn't in the DB but then it shouldn't be recognized as a
            # repo admin and thus, if we ever are here, we are in trouble.
            flask.flash(str(err), 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')

    if not flask.g.repo_committer:
        form = None

    # if the pull request we are creating only has one commit,
    # we automatically fill out the form fields for the PR with
    # the commit title and bodytext
    if len(diff_commits) == 1 and form:
        form.title.data = diff_commits[0].message.strip().split('\n')[0]
        form.initial_comment.data = diff_commits[0].message.partition('\n')[2]

    # Get the contributing templates from the requests git repo
    contributing = None
    requestrepopath = _get_parent_request_repo_path(repo)
    if os.path.exists(requestrepopath):
        requestrepo = pygit2.Repository(requestrepopath)
        if not requestrepo.is_empty and not requestrepo.head_is_unborn:
            commit = requestrepo[requestrepo.head.target]
            contributing = __get_file_in_tree(
                requestrepo, commit.tree, ['templates', 'contributing.md'],
                bail_on_tree=True)
            if contributing:
                contributing, _ = pagure.doc_utils.convert_readme(
                    contributing.data, 'md')

    flask.g.branches = sorted(orig_repo.listall_branches())

    return flask.render_template(
        'pull_request.html',
        select='requests',
        repo=repo,
        username=username,
        orig_repo=orig_repo,
        diff_commits=diff_commits,
        diff=diff,
        form=form,
        branch_to=branch_to,
        branch_from=branch_from,
        contributing=contributing,
    )


@APP.route('/<repo>/diff/remote/', methods=('GET', 'POST'))
@APP.route('/<repo>/diff/remote', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/diff/remote/', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/diff/remote', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<repo>/diff/remote/', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<repo>/diff/remote', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/diff/remote/',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/diff/remote',
    methods=('GET', 'POST'))
@login_required
def new_remote_request_pull(repo, username=None, namespace=None):
    """ Create a pull request with the changes from a remote fork into the
        project.
    """
    confirm = flask.request.values.get('confirm', False)

    repo = flask.g.repo

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-request allowed on this project')

    orig_repo = flask.g.repo_obj

    form = pagure.forms.RemoteRequestPullForm()
    if form.validate_on_submit():
        taskid = flask.request.values.get('taskid')
        if taskid:
            result = pagure.lib.tasks.get_result(taskid)
            if not result.ready:
                return pagure.wait_for_task_post(
                    taskid, form, 'new_remote_request_pull',
                    repo=repo.name, username=username, namespace=namespace)
            # Make sure to collect any exceptions resulting from the task
            result.get(timeout=0)

        branch_from = form.branch_from.data.strip()
        branch_to = form.branch_to.data.strip()
        remote_git = form.git_repo.data.strip()

        repopath = pagure.get_remote_repo_path(remote_git, branch_from)
        if not repopath:
            taskid = pagure.lib.tasks.pull_remote_repo.delay(
                repo.name, repo.namespace, repo.user.username, remote_git,
                branch_from, branch_to)
            return pagure.wait_for_task_post(
                taskid, form, 'new_remote_request_pull',
                repo=repo.name, username=username, namespace=namespace,
                initial=True)

        repo_obj = pygit2.Repository(repopath)

        try:
            diff, diff_commits, orig_commit = pagure.lib.git.get_diff_info(
                repo_obj, orig_repo, branch_from, branch_to)
        except pagure.exceptions.PagureException as err:
            flask.flash(err.message, 'error')
            return flask.redirect(flask.url_for(
                'view_repo', username=username, repo=repo.name,
                namespace=namespace))

        if not confirm:
            flask.g.branches = sorted(orig_repo.listall_branches())
            return flask.render_template(
                'pull_request.html',
                select='requests',
                repo=repo,
                username=username,
                orig_repo=orig_repo,
                diff_commits=diff_commits,
                diff=diff,
                form=form,
                branch_to=branch_to,
                branch_from=branch_from,
                remote_git=remote_git,
            )

        try:
            if repo.settings.get(
                    'Enforce_signed-off_commits_in_pull-request', False):
                for commit in diff_commits:
                    if 'signed-off-by' not in commit.message.lower():
                        raise pagure.exceptions.PagureException(
                            'This repo enforces that all commits are '
                            'signed off by their author. ')

            if orig_commit:
                orig_commit = orig_commit.oid.hex

            parent = repo
            if repo.parent:
                parent = repo.parent

            request = pagure.lib.new_pull_request(
                SESSION,
                repo_to=parent,
                branch_to=branch_to,
                branch_from=branch_from,
                repo_from=None,
                remote_git=remote_git,
                title=form.title.data,
                user=flask.g.fas_user.username,
                requestfolder=APP.config['REQUESTS_FOLDER'],
            )

            if form.initial_comment.data.strip() != '':
                pagure.lib.add_pull_request_comment(
                    SESSION,
                    request=request,
                    commit=None,
                    tree_id=None,
                    filename=None,
                    row=None,
                    comment=form.initial_comment.data.strip(),
                    user=flask.g.fas_user.username,
                    requestfolder=APP.config['REQUESTS_FOLDER'],
                )

            try:
                SESSION.commit()
                flask.flash('Request created')
            except SQLAlchemyError as err:  # pragma: no cover
                SESSION.rollback()
                _log.exception(err)
                flask.flash(
                    'Could not register this pull-request in '
                    'the database', 'error')

            if not parent.is_fork:
                url = flask.url_for(
                    'request_pull', requestid=request.id,
                    username=None, repo=parent.name,
                    namespace=namespace)
            else:
                url = flask.url_for(
                    'request_pull', requestid=request.id,
                    username=parent.user, repo=parent.name,
                    namespace=namespace)

            return flask.redirect(url)
        except pagure.exceptions.PagureException as err:  # pragma: no cover
            # There could be a PagureException thrown if the
            # flask.g.fas_user wasn't in the DB but then it shouldn't
            # be recognized as a repo admin and thus, if we ever are
            # here, we are in trouble.
            flask.flash(str(err), 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')

    flask.g.branches = sorted(orig_repo.listall_branches())

    return flask.render_template(
        'remote_pull_request.html',
        select='requests',
        repo=repo,
        username=username,
        form=form,
        branch_to=orig_repo.head.shorthand,
    )


@APP.route(
    '/fork_edit/<repo>/edit/<path:branchname>/f/<path:filename>',
    methods=['POST'])
@APP.route(
    '/fork_edit/<namespace>/<repo>/edit/<path:branchname>/f/<path:filename>',
    methods=['POST'])
@APP.route(
    '/fork_edit/fork/<username>/<repo>/edit/<path:branchname>/'
    'f/<path:filename>', methods=['POST'])
@APP.route(
    '/fork_edit/fork/<username>/<namespace>/<repo>/edit/<path:branchname>/'
    'f/<path:filename>', methods=['POST'])
@login_required
def fork_edit_file(
        repo, branchname, filename, username=None, namespace=None):
    """ Fork the project specified and open the specific file to edit
    """
    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.abort(400)

    if pagure.lib._get_project(
            SESSION, repo.name, user=flask.g.fas_user.username):
        flask.flash('You had already forked this project')
        return flask.redirect(flask.url_for(
            'edit_file',
            username=flask.g.fas_user.username,
            namespace=namespace,
            repo=repo.name,
            branchname=branchname,
            filename=filename
        ))

    try:
        taskid = pagure.lib.fork_project(
            session=SESSION,
            repo=repo,
            gitfolder=APP.config['GIT_FOLDER'],
            docfolder=APP.config['DOCS_FOLDER'],
            ticketfolder=APP.config['TICKETS_FOLDER'],
            requestfolder=APP.config['REQUESTS_FOLDER'],
            user=flask.g.fas_user.username,
            editbranch=branchname,
            editfile=filename)

        SESSION.commit()
        return pagure.wait_for_task(taskid)
    except pagure.exceptions.PagureException as err:
        flask.flash(str(err), 'error')
    except SQLAlchemyError as err:  # pragma: no cover
        SESSION.rollback()
        flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_repo', repo=repo.name, username=username, namespace=namespace))
