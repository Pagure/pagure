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


from __future__ import unicode_literals

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
from pagure.config import config as pagure_config
from pagure.ui import UI_NS
from pagure.utils import (
    login_required, __get_file_in_tree, get_parent_repo_path, is_true)


_log = logging.getLogger(__name__)


def _get_parent_request_repo_path(repo):
    """ Return the path of the parent git repository corresponding to the
    provided Repository object from the DB.
    """
    if repo.parent:
        parentpath = os.path.join(
            pagure_config['REQUESTS_FOLDER'], repo.parent.path)
    else:
        parentpath = os.path.join(
            pagure_config['REQUESTS_FOLDER'], repo.path)

    return parentpath


@UI_NS.route('/<repo>/pull-requests/')
@UI_NS.route('/<repo>/pull-requests')
@UI_NS.route('/<namespace>/<repo>/pull-requests/')
@UI_NS.route('/<namespace>/<repo>/pull-requests')
@UI_NS.route('/fork/<username>/<repo>/pull-requests/')
@UI_NS.route('/fork/<username>/<repo>/pull-requests')
@UI_NS.route('/fork/<username>/<namespace>/<repo>/pull-requests/')
@UI_NS.route('/fork/<username>/<namespace>/<repo>/pull-requests')
def request_pulls(repo, username=None, namespace=None):
    """ List all Pull-requests associated to a repo
    """
    status = flask.request.args.get('status', 'Open')
    assignee = flask.request.args.get('assignee', None)
    author = flask.request.args.get('author', None)
    order = flask.request.args.get('order', 'desc')
    order_key = flask.request.args.get('order_key', 'date_created')

    repo = flask.g.repo

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    total_open = pagure.lib.search_pull_requests(
        flask.g.session,
        project_id=repo.id,
        status=True,
        count=True)

    total_merged = pagure.lib.search_pull_requests(
        flask.g.session,
        project_id=repo.id,
        status='Merged',
        count=True)

    if status.lower() == 'merged' or is_true(status, ['false', '0']):
        status_filter = 'Merged'
        requests = pagure.lib.search_pull_requests(
            flask.g.session,
            project_id=repo.id,
            status='Merged',
            order=order,
            order_key=order_key,
            assignee=assignee,
            author=author,
            offset=flask.g.offset,
            limit=flask.g.limit)
    elif is_true(status, ['true', '1', 'open']):
        status_filter = 'Open'
        requests = pagure.lib.search_pull_requests(
            flask.g.session,
            project_id=repo.id,
            status='Open',
            order=order,
            order_key=order_key,
            assignee=assignee,
            author=author,
            offset=flask.g.offset,
            limit=flask.g.limit)
    elif status.lower() == 'closed':
        status_filter = 'Closed'
        requests = pagure.lib.search_pull_requests(
            flask.g.session,
            project_id=repo.id,
            status='Closed',
            order=order,
            order_key=order_key,
            assignee=assignee,
            author=author,
            offset=flask.g.offset,
            limit=flask.g.limit)
    else:
        status_filter = None
        requests = pagure.lib.search_pull_requests(
            flask.g.session,
            project_id=repo.id,
            status=None,
            order=order,
            order_key=order_key,
            assignee=assignee,
            author=author,
            offset=flask.g.offset,
            limit=flask.g.limit)

    open_cnt = pagure.lib.search_pull_requests(
        flask.g.session,
        project_id=repo.id,
        status='Open',
        assignee=assignee,
        author=author,
        count=True)

    merged_cnt = pagure.lib.search_pull_requests(
        flask.g.session,
        project_id=repo.id,
        status='Merged',
        assignee=assignee,
        author=author,
        count=True)

    closed_cnt = pagure.lib.search_pull_requests(
        flask.g.session,
        project_id=repo.id,
        status='Closed',
        assignee=assignee,
        author=author,
        count=True)

    repo_obj = flask.g.repo_obj
    if not repo_obj.is_empty and not repo_obj.head_is_unborn:
        head = repo_obj.head.shorthand
    else:
        head = 'master'

    total_page = 1
    if len(requests):
        total_page = int(ceil(len(requests) / float(flask.g.limit)))

    return flask.render_template(
        'requests.html',
        select='requests',
        repo=repo,
        username=username,
        requests=requests,
        open_cnt=open_cnt,
        merged_cnt=merged_cnt,
        closed_cnt=closed_cnt,
        order=order,
        order_key=order_key,
        status=status,
        status_filter=status_filter,
        assignee=assignee,
        author=author,
        head=head,
        total_page=total_page,
        total_open=total_open,
        total_merged=total_merged,
    )


@UI_NS.route('/<repo>/pull-request/<int:requestid>/')
@UI_NS.route('/<repo>/pull-request/<int:requestid>')
@UI_NS.route('/<namespace>/<repo>/pull-request/<int:requestid>/')
@UI_NS.route('/<namespace>/<repo>/pull-request/<int:requestid>')
@UI_NS.route('/fork/<username>/<repo>/pull-request/<int:requestid>/')
@UI_NS.route('/fork/<username>/<repo>/pull-request/<int:requestid>')
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/')
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>')
def request_pull(repo, requestid, username=None, namespace=None):
    """ Create a pull request with the changes from the fork into the project.
    """
    repo = flask.g.repo

    _log.info('Viewing pull Request #%s repo: %s', requestid, repo.fullname)

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        flask.g.session, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if request.remote:
        repopath = pagure.utils.get_remote_repo_path(
            request.remote_git, request.branch_from)
        parentpath = pagure.utils.get_repo_path(request.project)
    else:
        repo_from = request.project_from
        parentpath = pagure.utils.get_repo_path(request.project)
        repopath = parentpath
        if repo_from:
            repopath = pagure.utils.get_repo_path(repo_from)

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
                flask.g.session, request, repo_obj, orig_repo,
                requestfolder=pagure_config['REQUESTS_FOLDER'])
        except pagure.exceptions.PagureException as err:
            flask.flash('%s' % err, 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash(
                'Could not update this pull-request in the database',
                'error')

    if diff:
        diff.find_similar()

    form = pagure.forms.MergePRForm()

    can_delete_branch = (
        pagure_config.get('ALLOW_DELETE_BRANCH', True)
        and not request.remote_git
        and pagure.utils.is_repo_committer(request.project_from)
    )
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
        subscribers=pagure.lib.get_watch_list(flask.g.session, request),
        tag_list=pagure.lib.get_tags_of_project(flask.g.session, repo),
        can_delete_branch=can_delete_branch,
    )


@UI_NS.route('/<repo>/pull-request/<int:requestid>.patch')
@UI_NS.route('/<namespace>/<repo>/pull-request/<int:requestid>.patch')
@UI_NS.route('/fork/<username>/<repo>/pull-request/<int:requestid>.patch')
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>.patch')
def request_pull_patch(repo, requestid, username=None, namespace=None):
    """ Returns the commits from the specified pull-request as patches.
    """
    return request_pull_to_diff_or_patch(
        repo, requestid, username, namespace, diff=False)


@UI_NS.route('/<repo>/pull-request/<int:requestid>.diff')
@UI_NS.route('/<namespace>/<repo>/pull-request/<int:requestid>.diff')
@UI_NS.route('/fork/<username>/<repo>/pull-request/<int:requestid>.diff')
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>.diff')
def request_pull_diff(repo, requestid, username=None, namespace=None):
    """ Returns the commits from the specified pull-request as patches.
    """
    return request_pull_to_diff_or_patch(
        repo, requestid, username, namespace, diff=True)


def request_pull_to_diff_or_patch(
        repo, requestid, username=None, namespace=None, diff=False):
    """ Returns the commits from the specified pull-request as patches.

    :arg repo: the `pagure.lib.model.Project` object of the current pagure
        project browsed
    :type repo: `pagure.lib.model.Project`
    :arg requestid: the identifier of the pull-request to convert to patch
        or diff
    :type requestid: int
    :kwarg username: the username of the user who forked then project when
        the project viewed is a fork
    :type username: str or None
    :kwarg namespace: the namespace of the project if it has one
    :type namespace: str or None
    :kwarg diff: a boolean whether the data returned is a patch or a diff
    :type diff: boolean
    :return: the patch or diff representation of the specified pull-request
    :rtype: str

    """
    repo = flask.g.repo

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        flask.g.session, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if request.remote:
        repopath = pagure.utils.get_remote_repo_path(
            request.remote_git, request.branch_from)
        parentpath = pagure.utils.get_repo_path(request.project)
    else:
        repo_from = request.project_from
        parentpath = pagure.utils.get_repo_path(request.project)
        repopath = parentpath
        if repo_from:
            repopath = pagure.utils.get_repo_path(repo_from)

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
                flask.g.session, request, repo_obj, orig_repo,
                requestfolder=pagure_config['REQUESTS_FOLDER'],
                with_diff=False)
        except pagure.exceptions.PagureException as err:
            flask.flash('%s' % err, 'error')
            return flask.redirect(flask.url_for(
                'ui_ns.view_repo', username=username, repo=repo.name,
                namespace=namespace))
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash(
                'Could not update this pull-request in the database',
                'error')

    diff_commits.reverse()
    patch = pagure.lib.git.commit_to_patch(
        repo_obj, diff_commits, diff_view=diff)

    return flask.Response(patch, content_type="text/plain;charset=UTF-8")


@UI_NS.route(
    '/<repo>/pull-request/<int:requestid>/edit/', methods=('GET', 'POST'))
@UI_NS.route(
    '/<repo>/pull-request/<int:requestid>/edit', methods=('GET', 'POST'))
@UI_NS.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/edit/',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/edit',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/edit/',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/edit',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/edit/',
    methods=('GET', 'POST'))
@UI_NS.route(
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
        flask.g.session, project_id=repo.id, requestid=requestid)

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
        flask.g.session.add(request)
        try:
            flask.g.session.commit()
            flask.flash('Pull request edited!')
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash(
                'Could not edit this pull-request in the database',
                'error')
        return flask.redirect(flask.url_for(
            'ui_ns.request_pull', username=username, namespace=namespace,
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


@UI_NS.route(
    '/<repo>/pull-request/<int:requestid>/comment',
    methods=['POST'])
@UI_NS.route(
    '/<repo>/pull-request/<int:requestid>/comment/<commit>/'
    '<path:filename>/<row>', methods=('GET', 'POST'))
@UI_NS.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/comment',
    methods=['POST'])
@UI_NS.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/comment/<commit>/'
    '<path:filename>/<row>', methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/comment',
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/comment/'
    '<commit>/<path:filename>/<row>', methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/'
    'comment', methods=['POST'])
@UI_NS.route(
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
        flask.g.session, project_id=repo.id, requestid=requestid)

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
                flask.g.session,
                request=request,
                commit=commit,
                tree_id=tree_id,
                filename=filename,
                row=row,
                comment=comment,
                user=flask.g.fas_user.username,
                requestfolder=pagure_config['REQUESTS_FOLDER'],
                trigger_ci=pagure_config['TRIGGER_CI'],
            )
            flask.g.session.commit()
            if not is_js:
                flask.flash(message)
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            if is_js:
                return 'error'
            else:
                flask.flash(str(err), 'error')

        if is_js:
            return 'ok'
        return flask.redirect(flask.url_for(
            'ui_ns.request_pull', username=username, namespace=namespace,
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


@UI_NS.route(
    '/<repo>/pull-request/<int:requestid>/comment/drop',
    methods=['POST'])
@UI_NS.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/comment/drop',
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/comment/drop',
    methods=['POST'])
@UI_NS.route(
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
        flask.g.session, project_id=repo.id, requestid=requestid)

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
                flask.g.session, request.uid, commentid)
            if comment is None or comment.pull_request.project != repo:
                flask.abort(404, 'Comment not found')

            if (flask.g.fas_user.username != comment.user.username
                    or comment.parent.status is False) \
                    and not flask.g.repo_committer:
                flask.abort(
                    403,
                    'You are not allowed to remove this comment from '
                    'this issue')

            flask.g.session.delete(comment)
            try:
                flask.g.session.commit()
                flask.flash('Comment removed')
            except SQLAlchemyError as err:  # pragma: no cover
                flask.g.session.rollback()
                _log.error(err)
                flask.flash(
                    'Could not remove the comment: %s' % commentid, 'error')

    return flask.redirect(flask.url_for(
        'ui_ns.request_pull', username=username, namespace=namespace,
        repo=repo.name, requestid=requestid))


@UI_NS.route(
    '/<repo>/pull-request/<int:requestid>/comment/<int:commentid>/edit',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/comment/'
    '<int:commentid>/edit', methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/comment'
    '/<int:commentid>/edit', methods=('GET', 'POST'))
@UI_NS.route(
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
        flask.g.session, project_id=project.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    comment = pagure.lib.get_request_comment(
        flask.g.session, request.uid, commentid)

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
                flask.g.session,
                parent=request,
                comment=comment,
                user=flask.g.fas_user.username,
                updated_comment=updated_comment,
                folder=pagure_config['REQUESTS_FOLDER'],
            )
            flask.g.session.commit()
            if not is_js:
                flask.flash(message)
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.error(err)
            if is_js:
                return 'error'
            else:
                flask.flash(
                    'Could not edit the comment: %s' % commentid, 'error')

        if is_js:
            return 'ok'
        return flask.redirect(flask.url_for(
            'ui_ns.request_pull', username=username, namespace=namespace,
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


@UI_NS.route(
    '/<repo>/pull-request/<int:requestid>/merge', methods=['POST'])
@UI_NS.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/merge',
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/merge',
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/merge',
    methods=['POST'])
@login_required
def merge_request_pull(repo, requestid, username=None, namespace=None):
    """ Create a pull request with the changes from the fork into the project.
    """

    form = pagure.forms.MergePRForm()
    if not form.validate_on_submit():
        flask.flash('Invalid input submitted', 'error')
        return flask.redirect(flask.url_for(
            'ui_ns.request_pull', repo=repo, requestid=requestid,
            username=username, namespace=namespace))

    repo = flask.g.repo

    _log.info(
        'called merge_request_pull for repo: %s - requestid: %s',
        repo.fullname, requestid)

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        flask.g.session, project_id=repo.id, requestid=requestid)

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
                'ui_ns.request_pull', username=username, namespace=namespace,
                repo=repo.name, requestid=requestid))
        if request.assignee.username != flask.g.fas_user.username:
            flask.flash('Only the assignee can merge this review', 'error')
            return flask.redirect(flask.url_for(
                'ui_ns.request_pull', username=username, namespace=namespace,
                repo=repo.name, requestid=requestid))

    threshold = repo.settings.get('Minimum_score_to_merge_pull-request', -1)
    if threshold > 0 and int(request.score) < int(threshold):
        flask.flash(
            'This request does not have the minimum review score necessary '
            'to be merged', 'error')
        return flask.redirect(flask.url_for(
            'ui_ns.request_pull', username=username, namespace=namespace,
            repo=repo.name, requestid=requestid))

    if form.delete_branch.data:
        if not pagure_config.get('ALLOW_DELETE_BRANCH', True):
            flask.flash(
                'This pagure instance does not allow branch deletion', 'error')
            return flask.redirect(flask.url_for(
                'ui_ns.request_pull', username=username, namespace=namespace,
                repo=repo.name, requestid=requestid))
        if not pagure.utils.is_repo_committer(request.project_from):
            flask.flash(
                'You do not have permissions to delete the branch in the '
                'source repo', 'error')
            return flask.redirect(flask.url_for(
                'ui_ns.request_pull', username=username, namespace=namespace,
                repo=repo.name, requestid=requestid))
        if request.remote_git:
            flask.flash(
                'You can not delete branch in remote repo', 'error')
            return flask.redirect(flask.url_for(
                'ui_ns.request_pull', username=username, namespace=namespace,
                repo=repo.name, requestid=requestid))

    _log.info('All checks in the controller passed')

    try:
        task = pagure.lib.tasks.merge_pull_request.delay(
            repo.name, namespace, username, requestid,
            flask.g.fas_user.username,
            delete_branch_after=form.delete_branch.data)
        return pagure.utils.wait_for_task(
            task,
            prev=flask.url_for('ui_ns.request_pull',
                               repo=repo.name,
                               namespace=namespace,
                               username=username,
                               requestid=requestid))
    except pygit2.GitError as err:
        _log.info('GitError exception raised')
        flask.flash('%s' % err, 'error')
        return flask.redirect(flask.url_for(
            'ui_ns.request_pull', repo=repo.name, requestid=requestid,
            username=username, namespace=namespace))
    except pagure.exceptions.PagureException as err:
        _log.info('PagureException exception raised')
        flask.flash(str(err), 'error')
        return flask.redirect(flask.url_for(
            'ui_ns.request_pull', repo=repo.name, requestid=requestid,
            username=username, namespace=namespace))

    _log.info('All fine, returning')
    return flask.redirect(flask.url_for(
        'ui_ns.view_repo', repo=repo.name, username=username,
        namespace=namespace))


@UI_NS.route(
    '/<repo>/pull-request/cancel/<int:requestid>', methods=['POST'])
@UI_NS.route(
    '/<namespace>/<repo>/pull-request/cancel/<int:requestid>',
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<repo>/pull-request/cancel/<int:requestid>',
    methods=['POST'])
@UI_NS.route(
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
            flask.g.session, project_id=flask.g.repo.id, requestid=requestid)

        if not request:
            flask.abort(404, 'Pull-request not found')

        if not flask.g.repo_committer \
                and not flask.g.fas_user.username == request.user.username:
            flask.abort(
                403,
                'You are not allowed to cancel pull-request for this project')

        pagure.lib.close_pull_request(
            flask.g.session, request, flask.g.fas_user.username,
            requestfolder=pagure_config['REQUESTS_FOLDER'],
            merged=False)
        try:
            flask.g.session.commit()
            flask.flash('Pull request canceled!')
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash(
                'Could not update this pull-request in the database',
                'error')

    else:
        flask.flash('Invalid input submitted', 'error')

    return flask.redirect(flask.url_for(
        'ui_ns.view_repo', repo=repo, username=username, namespace=namespace))


@UI_NS.route(
    '/<repo>/pull-request/refresh/<int:requestid>', methods=['POST'])
@UI_NS.route(
    '/<namespace>/<repo>/pull-request/refresh/<int:requestid>',
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<repo>/pull-request/refresh/<int:requestid>',
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/refresh/<int:requestid>',
    methods=['POST'])
@login_required
def refresh_request_pull(repo, requestid, username=None, namespace=None):
    """ Refresh a remote pull request.
    """

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():

        if not flask.g.repo.settings.get('pull_requests', True):
            flask.abort(404, 'No pull-requests found for this project')

        request = pagure.lib.search_pull_requests(
            flask.g.session, project_id=flask.g.repo.id, requestid=requestid)

        if not request:
            flask.abort(404, 'Pull-request not found')

        if not flask.g.repo_committer \
                and not flask.g.fas_user.username == request.user.username:
            flask.abort(
                403,
                'You are not allowed to refresh this pull request')

        task = pagure.lib.tasks.refresh_remote_pr.delay(
            flask.g.repo.name, namespace, username, requestid)
        return pagure.utils.wait_for_task(
            task,
            prev=flask.url_for('ui_ns.request_pull',
                               repo=flask.g.repo.name,
                               namespace=namespace,
                               username=username,
                               requestid=requestid))
    else:
        flask.flash('Invalid input submitted', 'error')

    return flask.redirect(flask.url_for(
        'ui_ns.request_pull', username=username, namespace=namespace,
        repo=flask.g.repo.name, requestid=requestid))


@UI_NS.route(
    '/<repo>/pull-request/<int:requestid>/update', methods=['POST'])
@UI_NS.route(
    '/<namespace>/<repo>/pull-request/<int:requestid>/update',
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<repo>/pull-request/<int:requestid>/update',
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/pull-request/<int:requestid>/update',
    methods=['POST'])
@login_required
def update_pull_requests(repo, requestid, username=None, namespace=None):
    ''' Update the metadata of a pull-request. '''
    repo = flask.g.repo

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-request allowed on this project')

    request = pagure.lib.search_pull_requests(
        flask.g.session, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if request.status != 'Open':
        flask.abort(403, 'Pull-request closed')

    if not flask.g.repo_committer \
            and flask.g.fas_user.username != request.user.username:
        flask.abort(403, 'You are not allowed to update this pull-request')

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        tags = [
            tag.strip()
            for tag in flask.request.form.get('tag', '').strip().split(',')
            if tag.strip()]

        messages = set()
        try:
            # Adjust (add/remove) tags
            msgs = pagure.lib.update_tags(
                flask.g.session,
                obj=request,
                tags=tags,
                username=flask.g.fas_user.username,
                gitfolder=pagure_config['TICKETS_FOLDER'],
            )
            messages = messages.union(set(msgs))

            if flask.g.repo_committer:
                # Assign or update assignee of the ticket
                msg = pagure.lib.add_pull_request_assignee(
                    flask.g.session,
                    request=request,
                    assignee=flask.request.form.get(
                        'user', '').strip() or None,
                    user=flask.g.fas_user.username,
                    requestfolder=pagure_config['REQUESTS_FOLDER'],
                )
                if msg:
                    messages.add(msg)

            if messages:
                # Add the comment for field updates:
                not_needed = set(['Comment added', 'Updated comment'])
                pagure.lib.add_metadata_update_notif(
                    session=flask.g.session,
                    obj=request,
                    messages=messages - not_needed,
                    user=flask.g.fas_user.username,
                    gitfolder=pagure_config['REQUESTS_FOLDER']
                )
                messages.add('Metadata fields updated')

                flask.g.session.commit()
                for message in messages:
                    flask.flash(message)

        except pagure.exceptions.PagureException as err:
            flask.g.session.rollback()
            flask.flash('%s' % err, 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'ui_ns.request_pull', username=username, namespace=namespace,
        repo=repo.name, requestid=requestid))


# Specific actions


@UI_NS.route('/do_fork/<repo>', methods=['POST'])
@UI_NS.route('/do_fork/<namespace>/<repo>', methods=['POST'])
@UI_NS.route('/do_fork/fork/<username>/<repo>', methods=['POST'])
@UI_NS.route(
    '/do_fork/fork/<username>/<namespace>/<repo>', methods=['POST'])
@login_required
def fork_project(repo, username=None, namespace=None):
    """ Fork the project specified into the user's namespace
    """
    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.abort(400)

    if pagure.lib._get_project(
            flask.g.session, repo.name, user=flask.g.fas_user.username,
            namespace=namespace,
            case=pagure_config.get('CASE_SENSITIVE', False)):
        return flask.redirect(flask.url_for(
            'ui_ns.view_repo',
            repo=repo.name,
            username=flask.g.fas_user.username,
            namespace=namespace))

    try:
        task = pagure.lib.fork_project(
            session=flask.g.session,
            repo=repo,
            gitfolder=pagure_config['GIT_FOLDER'],
            docfolder=pagure_config.get('DOCS_FOLDER'),
            ticketfolder=pagure_config.get('TICKETS_FOLDER'),
            requestfolder=pagure_config['REQUESTS_FOLDER'],
            user=flask.g.fas_user.username)

        flask.g.session.commit()
        return pagure.utils.wait_for_task(
            task,
            prev=flask.url_for(
                'ui_ns.view_repo', repo=repo.name,
                username=username, namespace=namespace,
                _external=True
            )
        )
    except pagure.exceptions.PagureException as err:
        flask.flash(str(err), 'error')
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'ui_ns.view_repo', repo=repo.name, username=username,
        namespace=namespace
    ))


@UI_NS.route(
    '/<repo>/diff/<path:branch_to>..<path:branch_from>/',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/<repo>/diff/<path:branch_to>..<path:branch_from>',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/<namespace>/<repo>/diff/<path:branch_to>..<path:branch_from>/',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/<namespace>/<repo>/diff/<path:branch_to>..<path:branch_from>',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/diff/<path:branch_to>..<path:branch_from>/',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/diff/<path:branch_to>..<path:branch_from>',
    methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/diff/'
    '<path:branch_to>..<path:branch_from>/', methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/diff/'
    '<path:branch_to>..<path:branch_from>', methods=('GET', 'POST'))
def new_request_pull(
        repo, branch_to, branch_from, username=None, namespace=None):
    """ Create a pull request with the changes from the fork into the project.
    """
    branch_to = flask.request.values.get('branch_to', branch_to)
    project_to = flask.request.values.get('project_to')

    repo = flask.g.repo

    parent = repo
    if repo.parent:
        parent = repo.parent

    repo_obj = flask.g.repo_obj

    if not project_to:
        parentpath = get_parent_repo_path(repo)
        orig_repo = pygit2.Repository(parentpath)
    else:
        p_namespace = None
        p_username = None
        p_name = None
        project_to = project_to.rstrip('/')
        if project_to.startswith('fork/'):
            tmp = project_to.split('fork/')[1]
            p_username, left = tmp.split('/', 1)
        else:
            left = project_to

        if '/' in left:
            p_namespace, p_name = left.split('/', 1)
        else:
            p_name = left
        parent = pagure.lib.get_authorized_project(
            flask.g.session,
            p_name,
            user=p_username,
            namespace=p_namespace
        )
        if parent:
            family = [
                p.url_path for p in
                pagure.lib.get_project_family(flask.g.session, repo)
            ]
            if parent.url_path not in family:
                flask.abort(
                    400,
                    '%s is not part of %s\'s family' % (
                        project_to, repo.url_path))
            orig_repo = pygit2.Repository(os.path.join(
                pagure_config['GIT_FOLDER'], parent.path))
        else:
            flask.abort(404, 'No project found for %s' % project_to)

    if not parent.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-request allowed on this project')

    if parent.settings.get(
            'Enforce_signed-off_commits_in_pull-request', False):
        flask.flash(
            'This project enforces the Signed-off-by statement on all '
            'commits')

    try:
        diff, diff_commits, orig_commit = pagure.lib.git.get_diff_info(
            repo_obj, orig_repo, branch_from, branch_to)
    except pagure.exceptions.PagureException as err:
        flask.abort(400, str(err))

    repo_committer = flask.g.repo_committer

    form = pagure.forms.RequestPullForm()
    if form.validate_on_submit() and repo_committer:
        try:
            if parent.settings.get(
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
                flask.g.session,
                repo_to=parent,
                branch_to=branch_to,
                branch_from=branch_from,
                repo_from=repo,
                title=form.title.data,
                initial_comment=initial_comment,
                user=flask.g.fas_user.username,
                requestfolder=pagure_config['REQUESTS_FOLDER'],
                commit_start=commit_start,
                commit_stop=commit_stop,
            )

            try:
                flask.g.session.commit()
            except SQLAlchemyError as err:  # pragma: no cover
                flask.g.session.rollback()
                _log.exception(err)
                flask.flash(
                    'Could not register this pull-request in the database',
                    'error')

            if not parent.is_fork:
                url = flask.url_for(
                    'ui_ns.request_pull', requestid=request.id,
                    username=None, repo=parent.name, namespace=namespace)
            else:
                url = flask.url_for(
                    'ui_ns.request_pull', requestid=request.id,
                    username=parent.user.user, repo=parent.name,
                    namespace=namespace)

            return flask.redirect(url)
        except pagure.exceptions.PagureException as err:  # pragma: no cover
            # There could be a PagureException thrown if the flask.g.fas_user
            # wasn't in the DB but then it shouldn't be recognized as a
            # repo admin and thus, if we ever are here, we are in trouble.
            flask.flash(str(err), 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
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
        parent_branches=sorted(orig_repo.listall_branches()),
        diff_commits=diff_commits,
        diff=diff,
        form=form,
        branch_to=branch_to,
        branch_from=branch_from,
        contributing=contributing,
        parent=parent,
        project_to=project_to,
    )


@UI_NS.route('/<repo>/diff/remote/', methods=('GET', 'POST'))
@UI_NS.route('/<repo>/diff/remote', methods=('GET', 'POST'))
@UI_NS.route('/<namespace>/<repo>/diff/remote/', methods=('GET', 'POST'))
@UI_NS.route('/<namespace>/<repo>/diff/remote', methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/diff/remote/', methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<repo>/diff/remote', methods=('GET', 'POST'))
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/diff/remote/',
    methods=('GET', 'POST'))
@UI_NS.route(
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

    if repo.settings.get(
            'Enforce_signed-off_commits_in_pull-request', False):
        flask.flash(
            'This project enforces the Signed-off-by statement on all '
            'commits')

    orig_repo = flask.g.repo_obj

    form = pagure.forms.RemoteRequestPullForm()
    if form.validate_on_submit():
        taskid = flask.request.values.get('taskid')
        if taskid:
            result = pagure.lib.tasks.get_result(taskid)
            if not result.ready:
                return pagure.utils.wait_for_task_post(
                    taskid, form, 'ui_ns.new_remote_request_pull',
                    repo=repo.name, username=username, namespace=namespace)
            # Make sure to collect any exceptions resulting from the task
            try:
                result.get(timeout=0)
            except Exception as err:
                flask.abort(500, err)

        branch_from = form.branch_from.data.strip()
        branch_to = form.branch_to.data.strip()
        remote_git = form.git_repo.data.strip()

        repopath = pagure.utils.get_remote_repo_path(remote_git, branch_from)
        if not repopath:
            taskid = pagure.lib.tasks.pull_remote_repo.delay(
                remote_git, branch_from)
            return pagure.utils.wait_for_task_post(
                taskid, form, 'ui_ns.new_remote_request_pull',
                repo=repo.name, username=username, namespace=namespace,
                initial=True)

        repo_obj = pygit2.Repository(repopath)

        try:
            diff, diff_commits, orig_commit = pagure.lib.git.get_diff_info(
                repo_obj, orig_repo, branch_from, branch_to)
        except pagure.exceptions.PagureException as err:
            flask.flash('%s' % err, 'error')
            return flask.redirect(flask.url_for(
                'ui_ns.view_repo', username=username, repo=repo.name,
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
                parent=repo,
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
                flask.g.session,
                repo_to=parent,
                branch_to=branch_to,
                branch_from=branch_from,
                repo_from=None,
                remote_git=remote_git,
                title=form.title.data,
                user=flask.g.fas_user.username,
                requestfolder=pagure_config['REQUESTS_FOLDER'],
            )

            if form.initial_comment.data.strip() != '':
                pagure.lib.add_pull_request_comment(
                    flask.g.session,
                    request=request,
                    commit=None,
                    tree_id=None,
                    filename=None,
                    row=None,
                    comment=form.initial_comment.data.strip(),
                    user=flask.g.fas_user.username,
                    requestfolder=pagure_config['REQUESTS_FOLDER'],
                )

            try:
                flask.g.session.commit()
                flask.flash('Request created')
            except SQLAlchemyError as err:  # pragma: no cover
                flask.g.session.rollback()
                _log.exception(err)
                flask.flash(
                    'Could not register this pull-request in '
                    'the database', 'error')

            if not parent.is_fork:
                url = flask.url_for(
                    'ui_ns.request_pull', requestid=request.id,
                    username=None, repo=parent.name,
                    namespace=namespace)
            else:
                url = flask.url_for(
                    'ui_ns.request_pull', requestid=request.id,
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
            flask.g.session.rollback()
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


@UI_NS.route(
    '/fork_edit/<repo>/edit/<path:branchname>/f/<path:filename>',
    methods=['POST'])
@UI_NS.route(
    '/fork_edit/<namespace>/<repo>/edit/<path:branchname>/f/<path:filename>',
    methods=['POST'])
@UI_NS.route(
    '/fork_edit/fork/<username>/<repo>/edit/<path:branchname>/'
    'f/<path:filename>', methods=['POST'])
@UI_NS.route(
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
            flask.g.session, repo.name, user=flask.g.fas_user.username,
            case=pagure_config.get('CASE_SENSITIVE', False)):
        flask.flash('You had already forked this project')
        return flask.redirect(flask.url_for(
            'ui_ns.edit_file',
            username=flask.g.fas_user.username,
            namespace=namespace,
            repo=repo.name,
            branchname=branchname,
            filename=filename
        ))

    try:
        task = pagure.lib.fork_project(
            session=flask.g.session,
            repo=repo,
            gitfolder=pagure_config['GIT_FOLDER'],
            docfolder=pagure_config['DOCS_FOLDER'],
            ticketfolder=pagure_config['TICKETS_FOLDER'],
            requestfolder=pagure_config['REQUESTS_FOLDER'],
            user=flask.g.fas_user.username,
            editbranch=branchname,
            editfile=filename)

        flask.g.session.commit()
        return pagure.utils.wait_for_task(task)
    except pagure.exceptions.PagureException as err:
        flask.flash(str(err), 'error')
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'ui_ns.view_repo', repo=repo.name, username=username,
        namespace=namespace))


_REACTION_URL_SNIPPET = (
    'pull-request/<int:requestid>/comment/<int:commentid>/react'
)


@UI_NS.route(
    '/<repo>/%s/' % _REACTION_URL_SNIPPET, methods=['POST'])
@UI_NS.route(
    '/<repo>/%s' % _REACTION_URL_SNIPPET, methods=['POST'])
@UI_NS.route(
    '/<namespace>/<repo>/%s/' % _REACTION_URL_SNIPPET,
    methods=['POST'])
@UI_NS.route(
    '/<namespace>/<repo>/%s' % _REACTION_URL_SNIPPET,
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<repo>/%s/' % _REACTION_URL_SNIPPET,
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<repo>/%s' % _REACTION_URL_SNIPPET,
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/%s/' % _REACTION_URL_SNIPPET,
    methods=['POST'])
@UI_NS.route(
    '/fork/<username>/<namespace>/<repo>/%s' % _REACTION_URL_SNIPPET,
    methods=['POST'])
@login_required
def pull_request_comment_add_reaction(repo, requestid, commentid,
                                      username=None, namespace=None):
    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.abort(400, 'CSRF token not valid')

    request = pagure.lib.search_pull_requests(
        flask.g.session, requestid=requestid, project_id=repo.id
    )

    if not request:
        flask.abort(404, 'Comment not found')

    comment = pagure.lib.get_request_comment(
        flask.g.session, request.uid, commentid)

    if 'reaction' not in flask.request.form:
        flask.abort(400, 'Reaction not found')

    reactions = comment.reactions
    r = flask.request.form['reaction']
    if not r:
        flask.abort(400, 'Empty reaction is not acceptable')
    if flask.g.fas_user.username in reactions.get(r, []):
        flask.abort(409, 'Already posted this one')

    reactions.setdefault(r, []).append(flask.g.fas_user.username)
    comment.reactions = reactions
    flask.g.session.add(comment)

    try:
        flask.g.session.commit()
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        _log.error(err)
        return 'error'

    return 'ok'
