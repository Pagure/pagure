# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import os
import shutil
import tempfile

import pygit2
from sqlalchemy.exc import SQLAlchemyError

import pagure.doc_utils
import pagure.lib
import pagure.lib.git
import pagure.forms
import pagure
from pagure import (APP, SESSION, LOG, cla_required,
                    is_repo_admin, generate_gitolite_acls)


# pylint: disable=E1101


def _get_parent_repo_path(repo):
    """ Return the path of the parent git repository corresponding to the
    provided Repository object from the DB.
    """
    if repo.parent:
        parentpath = os.path.join(APP.config['GIT_FOLDER'], repo.parent.path)
    else:
        parentpath = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    return parentpath


@APP.route('/<repo>/pull-requests')
@APP.route('/fork/<username>/<repo>/pull-requests')
def request_pulls(repo, username=None):
    """ Request pulling the changes from the fork into the project.
    """
    status = flask.request.args.get('status', True)
    assignee = flask.request.args.get('assignee', None)
    author = flask.request.args.get('author', None)

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    if status is False or str(status).lower() == 'closed':
        requests = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            status=False,
            assignee=assignee,
            author=author)
        oth_requests = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            status=True,
            assignee=assignee,
            author=author,
            count=True)
    else:
        requests = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            assignee=assignee,
            author=author,
            status=status)
        oth_requests = pagure.lib.search_pull_requests(
            SESSION,
            project_id=repo.id,
            status=False,
            assignee=assignee,
            author=author,
            count=True)

    return flask.render_template(
        'requests.html',
        select='requests',
        repo=repo,
        username=username,
        requests=requests,
        oth_requests=oth_requests,
        status=status,
        assignee=assignee,
        author=author,
    )


@APP.route('/<repo>/pull-request/<int:requestid>')
@APP.route('/fork/<username>/<repo>/pull-request/<int:requestid>')
def request_pull(repo, requestid, username=None):
    """ Request pulling the changes from the fork into the project.
    """

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    repo_from = request.project_from
    repopath = pagure.get_repo_path(repo_from)
    repo_obj = pygit2.Repository(repopath)

    parentpath = _get_parent_repo_path(repo_from)
    orig_repo = pygit2.Repository(parentpath)

    diff_commits = []
    diff = None
    # Closed pull-request
    if request.status is False:
        commitid = request.commit_stop
        for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
            diff_commits.append(commit)
            if commit.oid.hex == request.commit_start:
                break

        if diff_commits:
            diff = repo_obj.diff(
                repo_obj.revparse_single(diff_commits[-1].parents[0].oid.hex),
                repo_obj.revparse_single(diff_commits[0].oid.hex)
            )
    else:
        commitid = None
        branch = repo_obj.lookup_branch(request.branch_from)
        if branch:
            commitid = branch.get_object().hex

        if not repo_obj.is_empty and not orig_repo.is_empty:
            # Pull-request open
            master_commits = [
                commit.oid.hex
                for commit in orig_repo.walk(
                    orig_repo.lookup_branch(request.branch).get_object().hex,
                    pygit2.GIT_SORT_TIME)
            ]
            for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
                if request.status and commit.oid.hex in master_commits:
                    break
                diff_commits.append(commit)

            if request.status and diff_commits:
                first_commit = repo_obj[diff_commits[-1].oid.hex]
                request.commit_start = first_commit.oid.hex
                request.commit_stop = diff_commits[0].oid.hex
                SESSION.add(request)
                try:
                    SESSION.commit()
                    pagure.lib.git.update_git(
                        request, repo=request.project,
                        repofolder=APP.config['REQUESTS_FOLDER'])
                except SQLAlchemyError as err: # pragma: no cover
                    SESSION.rollback()
                    APP.logger.exception(err)
                    flask.flash(
                        'Could not update this pull-request in the database',
                        'error')

            if diff_commits:
                first_commit = repo_obj[diff_commits[-1].oid.hex]
                diff = repo_obj.diff(
                    repo_obj.revparse_single(first_commit.parents[0].oid.hex),
                    repo_obj.revparse_single(diff_commits[0].oid.hex)
                )

        elif orig_repo.is_empty and not repo_obj.is_empty:
            for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
                diff_commits.append(commit)
            if request.status and diff_commits:
                first_commit = repo_obj[diff_commits[-1].oid.hex]
                request.commit_start = first_commit.oid.hex
                request.commit_stop = diff_commits[0].oid.hex
                SESSION.add(request)
                try:
                    SESSION.commit()
                    pagure.lib.git.update_git(
                        request, repo=request.project,
                        repofolder=APP.config['REQUESTS_FOLDER'])
                except SQLAlchemyError as err: # pragma: no cover
                    SESSION.rollback()
                    APP.logger.exception(err)
                    flask.flash(
                        'Could not update this pull-request in the database',
                        'error')

            repo_commit = repo_obj[request.commit_stop]
            diff = repo_commit.tree.diff_to_tree(swap=True)
        else:
            flask.flash(
                'Fork is empty, there are no commits to request pulling',
                'error')
            return flask.redirect(flask.url_for(
                'view_repo', username=username, repo=repo.name))

    form = pagure.forms.ConfirmationForm()

    return flask.render_template(
        'pull_request.html',
        select='requests',
        requestid=requestid,
        repo=repo,
        username=username,
        pull_request=request,
        repo_admin=is_repo_admin(request.project),
        diff_commits=diff_commits,
        diff=diff,
        mergeform=form,
    )


@APP.route('/<repo>/pull-request/<int:requestid>.patch')
@APP.route('/fork/<username>/<repo>/pull-request/<int:requestid>.patch')
def request_pull_patch(repo, requestid, username=None):
    """ Returns the commits from the specified pull-request as patches.
    """

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    repo_from = request.project_from
    repopath = pagure.get_repo_path(repo_from)
    repo_obj = pygit2.Repository(repopath)

    parentpath = _get_parent_repo_path(repo_from)
    orig_repo = pygit2.Repository(parentpath)

    branch = repo_obj.lookup_branch(request.branch_from)
    commitid = None
    if branch:
        commitid = branch.get_object().hex

    diff_commits = []
    if not repo_obj.is_empty and not orig_repo.is_empty:

        # Closed pull-request
        if request.status is False:
            commitid = request.commit_stop
            for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
                diff_commits.append(commit)
                if commit.oid.hex == request.commit_start:
                    break
        # Pull-request open
        else:
            master_commits = [
                commit.oid.hex
                for commit in orig_repo.walk(
                    orig_repo.lookup_branch(request.branch).get_object().hex,
                    pygit2.GIT_SORT_TIME)
            ]
            for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
                if request.status and commit.oid.hex in master_commits:
                    break
                diff_commits.append(commit)

    elif orig_repo.is_empty and not repo_obj.is_empty:
        for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
            diff_commits.append(commit)
        if request.status and diff_commits:
            first_commit = repo_obj[diff_commits[-1].oid.hex]
            request.commit_start = first_commit.oid.hex
            request.commit_stop = diff_commits[0].oid.hex
            SESSION.add(request)
            try:
                SESSION.commit()
                pagure.lib.git.update_git(
                    request, repo=request.project,
                    repofolder=APP.config['REQUESTS_FOLDER'])
            except SQLAlchemyError as err: # pragma: no cover
                SESSION.rollback()
                APP.logger.exception(err)
                flask.flash(
                    'Could not update this pull-request in the database',
                    'error')

        repo_commit = repo_obj[request.commit_stop]
    else:
        flask.flash(
            'Fork is empty, there are no commits to request pulling',
            'error')
        return flask.redirect(flask.url_for(
            'view_repo', username=username, repo=repo.name))

    diff_commits.reverse()
    patch = pagure.lib.git.commit_to_patch(repo_obj, diff_commits)

    return flask.Response(patch, content_type="text/plain;charset=UTF-8")


@APP.route('/<repo>/pull-request/<int:requestid>/comment/',
           methods=['POST'])
@APP.route('/<repo>/pull-request/<int:requestid>/comment/<commit>/'
           '<path:filename>/<row>', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/pull-request/<int:requestid>/comment/',
           methods=['POST'])
@APP.route('/fork/<username>/<repo>/pull-request/<int:requestid>/comment/'
           '<commit>/<path:filename>/<row>', methods=('GET', 'POST'))
@cla_required
def pull_request_add_comment(
        repo, requestid, commit=None,
        filename=None, row=None, username=None):
    """ Add a comment to a commit in a pull-request.
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)
    repo = request.project_from

    if not request:
        flask.abort(404, 'Pull-request not found')

    form = pagure.forms.AddPullRequestCommentForm()
    form.commit.data = commit
    form.filename.data = filename
    form.requestid.data = requestid
    form.row.data = row

    if form.validate_on_submit():
        comment = form.comment.data

        try:
            message = pagure.lib.add_pull_request_comment(
                SESSION,
                request=request,
                commit=commit,
                filename=filename,
                row=row,
                comment=comment,
                user=flask.g.fas_user.username,
                requestfolder=APP.config['REQUESTS_FOLDER'],
            )
            SESSION.commit()
            flask.flash(message)
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash(str(err), 'error')

        return flask.redirect(flask.url_for(
            'request_pull', username=username,
            repo=repo.name, requestid=requestid))

    return flask.render_template(
        'pull_request_comment.html',
        select='requests',
        requestid=requestid,
        repo=repo,
        username=username,
        commit=commit,
        filename=filename,
        row=row,
        form=form,
    )


@APP.route('/<repo>/pull-request/<int:requestid>/comment/drop',
           methods=['POST'])
@APP.route('/fork/<username>/<repo>/pull-request/<int:requestid>/comment/drop',
           methods=['POST'])
@cla_required
def pull_request_drop_comment(repo, requestid, username=None):
    """ Delete a comment of a pull-request.
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():

        if flask.request.form.get('drop_comment'):
            commentid = flask.request.form.get('drop_comment')

            comment = pagure.lib.get_request_comment(
                SESSION, request.uid, commentid)
            if comment is None or comment.pull_request.project != repo:
                flask.abort(404, 'Comment not found')

            if (flask.g.fas_user.username != comment.user.username
                    and comment.parent.status is True) \
                    or not is_repo_admin(repo):
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

    return flask.redirect(flask.url_for(
        'request_pull', username=username,
        repo=repo.name, requestid=requestid))


@APP.route('/<repo>/pull-request/<int:requestid>/merge', methods=['POST'])
@APP.route('/fork/<username>/<repo>/pull-request/<int:requestid>/merge',
           methods=['POST'])
@cla_required
def merge_request_pull(repo, requestid, username=None):
    """ Request pulling the changes from the fork into the project.
    """

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.flash('Invalid input submitted', 'error')
        return flask.redirect(flask.url_for(
            'request_pull', repo=repo, requestid=requestid, username=username))

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    request = pagure.lib.search_pull_requests(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to merge pull-request for this project')

    if repo.settings.get('Only_assignee_can_merge_pull-request', False):
        if not request.assignee:
            flask.flash(
                'This request must be assigned to be merged', 'error')
            return flask.redirect(flask.url_for(
                'request_pull', username=username,
                repo=repo.name, requestid=requestid))
        if request.assignee.username != flask.g.fas_user.username:
            flask.flash('Only the assignee can merge this review', 'error')
            return flask.redirect(flask.url_for(
                'request_pull', username=username,
                repo=repo.name, requestid=requestid))

    threshold = repo.settings.get('Minimum_score_to_merge_pull-request', -1)
    if threshold > 0 and int(request.score) < int(threshold):
        flask.flash(
            'This request does not have the minimum review score necessary '
            'to be merged', 'error')
        return flask.redirect(flask.url_for(
            'request_pull', username=username,
            repo=repo.name, requestid=requestid))

    error_output = flask.url_for(
        'request_pull', repo=repo.name, requestid=requestid,
        username=username)

    # Get the fork
    repopath = pagure.get_repo_path(request.project_from)
    fork_obj = pygit2.Repository(repopath)

    # Get the original repo
    parentpath = pagure.get_repo_path(request.project)

    # Clone the original repo into a temp folder
    newpath = tempfile.mkdtemp(prefix='pagure-pr-merge')
    new_repo = pygit2.clone_repository(parentpath, newpath)

    repo_commit = fork_obj[
        fork_obj.lookup_branch(request.branch_from).get_object().hex]

    ori_remote = new_repo.remotes[0]
    # Add the fork as remote repo
    reponame = '%s_%s' % (request.user.user, repo.name)
    remote = new_repo.create_remote(reponame, repopath)

    # Fetch the commits
    remote.fetch()

    merge = new_repo.merge(repo_commit.oid)
    if merge is None:
        mergecode = new_repo.merge_analysis(repo_commit.oid)[0]

    try:
        branch_ref = new_repo.lookup_reference(
            request.branch).resolve()
    except ValueError:
        branch_ref = new_repo.lookup_reference(
            'refs/heads/%s' % request.branch).resolve()

    refname = '%s:%s' % (branch_ref.name, branch_ref.name)
    if (
            (merge is not None and merge.is_uptodate)
            or
            (merge is None and
             mergecode & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE)):
        flask.flash('Nothing to do, changes were already merged', 'error')
        pagure.lib.close_pull_request(
            SESSION, request, flask.g.fas_user.username,
            requestfolder=APP.config['REQUESTS_FOLDER'])
        try:
            SESSION.commit()
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash('Could not close this pull-request', 'error')
        return flask.redirect(error_output)
    elif (
            (merge is not None and merge.is_fastforward)
            or
            (merge is None and
             mergecode & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD)):
        if merge is not None:
            # This is depending on the pygit2 version
            branch_ref.target = merge.fastforward_oid
        elif merge is None and mergecode is not None:
            branch_ref.set_target(repo_commit.oid.hex)

        ori_remote.push(refname)
        flask.flash('Changes merged!')

    else:
        tree = None
        try:
            tree = new_repo.index.write_tree()
        except pygit2.GitError:
            shutil.rmtree(newpath)
            flask.flash('Merge conflicts!', 'error')
            return flask.redirect(flask.url_for(
                'request_pull',
                repo=repo.name,
                username=username,
                requestid=requestid))
        head = new_repo.lookup_reference('HEAD').get_object()
        new_repo.create_commit(
            'refs/heads/master',
            repo_commit.author,
            repo_commit.committer,
            'Merge #%s `%s`' % (request.id, request.title),
            tree,
            [head.hex, repo_commit.oid.hex])
        ori_remote.push(refname)
        flask.flash('Changes merged!')

    # Update status
    pagure.lib.close_pull_request(
        SESSION, request, flask.g.fas_user.username,
        requestfolder=APP.config['REQUESTS_FOLDER'],
    )
    try:
        SESSION.commit()
    except SQLAlchemyError as err:  # pragma: no cover
        SESSION.rollback()
        APP.logger.exception(err)
        flask.flash(
            'Could not update this pull-request in the database',
            'error')
    shutil.rmtree(newpath)

    return flask.redirect(flask.url_for('view_repo', repo=repo.name))


@APP.route('/<repo>/pull-request/cancel/<int:requestid>',
           methods=['POST'])
@APP.route('/fork/<username>/<repo>/pull-request/cancel/<int:requestid>',
           methods=['POST'])
@cla_required
def cancel_request_pull(repo, requestid, username=None):
    """ Cancel request pulling request.
    """

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():

        repo_obj = pagure.lib.get_project(SESSION, repo, user=username)

        if not repo_obj:
            flask.abort(404, 'Project not found')

        if not repo_obj.settings.get('pull_requests', True):
            flask.abort(404, 'No pull-requests found for this project')

        request = pagure.lib.search_pull_requests(
            SESSION, project_id=repo_obj.id, requestid=requestid)

        if not request:
            flask.abort(404, 'Pull-request not found')

        if not is_repo_admin(repo_obj):
            flask.abort(
                403,
                'You are not allowed to cancel pull-request for this project')

        pagure.lib.close_pull_request(
            SESSION, request, flask.g.fas_user.username,
            requestfolder=APP.config['REQUESTS_FOLDER'],
            merged=False)
        try:
            SESSION.commit()
            flask.flash('Request pull canceled!')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash(
                'Could not update this pull-request in the database',
                'error')
    else:
        flask.flash('Invalid input submitted', 'error')

    return flask.redirect(flask.url_for('view_repo', repo=repo))


@APP.route('/<repo>/pull-request/<int:requestid>/assign', methods=['POST'])
@APP.route('/fork/<username>/<repo>/pull-request/<int:requestid>/assign',
           methods=['POST'])
@cla_required
def set_assignee_requests(repo, requestid, username=None):
    ''' Assign a pull-request. '''
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-request allowed on this project')

    request = pagure.lib.search_pull_requests(
            SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if not request.status:
        flask.abort(403, 'Pull-request closed')

    form = pagure.forms.AddUserForm()
    if form.validate_on_submit():
        try:
            # Assign or update assignee of the ticket
            message = pagure.lib.add_pull_request_assignee(
                SESSION,
                request=request,
                assignee=form.user.data or None,
                user=flask.g.fas_user.username,
                requestfolder=APP.config['REQUESTS_FOLDER'],)
            if message:
                SESSION.commit()
                flask.flash(message)
        except pagure.exceptions.PagureException, err:
            SESSION.rollback()
            flask.flash(err.message, 'error')
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'request_pull', username=username, repo=repo.name, requestid=requestid))


# Specific actions


@APP.route('/do_fork/<repo>', methods=['POST'])
@APP.route('/do_fork/<username>/<repo>', methods=['POST'])
@cla_required
def fork_project(repo, username=None):
    """ Fork the project specified into the user's namespace
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.abort(400)

    if repo is None:
        flask.abort(404)

    try:
        message = pagure.lib.fork_project(
            session=SESSION,
            repo=repo,
            gitfolder=APP.config['GIT_FOLDER'],
            forkfolder=APP.config['FORK_FOLDER'],
            docfolder=APP.config['DOCS_FOLDER'],
            ticketfolder=APP.config['TICKETS_FOLDER'],
            requestfolder=APP.config['REQUESTS_FOLDER'],
            user=flask.g.fas_user.username)

        SESSION.commit()
        generate_gitolite_acls()
        flask.flash(message)
        return flask.redirect(
            flask.url_for(
                'view_repo',
                username=flask.g.fas_user.username,
                repo=repo.name)
        )
    except pagure.exceptions.PagureException, err:
        flask.flash(str(err), 'error')
    except SQLAlchemyError, err:  # pragma: no cover
        SESSION.rollback()
        flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for('view_repo', repo=repo.name))


@APP.route('/<repo>/diff/<branch_to>..<branch_from>',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/diff/<branch_to>..<branch_from>',
           methods=('GET', 'POST'))
@cla_required
def new_request_pull(repo, branch_to, branch_from, username=None):
    """ Request pulling the changes from the fork into the project.
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    if not repo.settings.get('pull_requests', True):
        flask.abort(404, 'No pull-requests found for this project')

    repopath = pagure.get_repo_path(repo)
    repo_obj = pygit2.Repository(repopath)

    parentpath = _get_parent_repo_path(repo)
    orig_repo = pygit2.Repository(parentpath)

    frombranch = repo_obj.lookup_branch(branch_from)
    if not frombranch:
        flask.abort(
            400,
            'Branch %s does not exist' % branch_from)

    branch = orig_repo.lookup_branch(branch_to)
    if not branch:
        flask.abort(
            400,
            'Branch %s could not be found in the target repo' % branch_to)

    branch = repo_obj.lookup_branch(branch_from)
    commitid = branch.get_object().hex

    diff_commits = []
    diff = None
    if not repo_obj.is_empty and not orig_repo.is_empty:
        orig_commit = orig_repo[
            orig_repo.lookup_branch(branch_to).get_object().hex]

        master_commits = [
            commit.oid.hex
            for commit in orig_repo.walk(
                orig_commit.oid.hex, pygit2.GIT_SORT_TIME)
        ]

        repo_commit = repo_obj[commitid]

        for commit in repo_obj.walk(
                repo_commit.oid.hex, pygit2.GIT_SORT_TIME):
            if commit.oid.hex in master_commits:
                break
            diff_commits.append(commit)

        if diff_commits:
            first_commit = repo_obj[diff_commits[-1].oid.hex]
            diff = repo_obj.diff(
                repo_obj.revparse_single(first_commit.parents[0].oid.hex),
                repo_obj.revparse_single(diff_commits[0].oid.hex)
            )

    elif orig_repo.is_empty and not repo_obj.is_empty:
        orig_commit = None
        repo_commit = repo_obj[repo_obj.head.target]
        diff = repo_commit.tree.diff_to_tree(swap=True)
    else:
        flask.flash(
            'Fork is empty, there are no commits to request pulling',
            'error')
        return flask.redirect(flask.url_for(
            'view_repo', username=username, repo=repo.name))

    form = pagure.forms.RequestPullForm()
    if form.validate_on_submit() and is_repo_admin(repo):
        try:
            if orig_commit:
                orig_commit = orig_commit.oid.hex

            parent = repo
            if repo.parent:
                parent = repo.parent

            message = pagure.lib.new_pull_request(
                SESSION,
                repo_to=parent,
                branch_to=branch_to,
                branch_from=branch_from,
                repo_from=repo,
                title=form.title.data,
                user=flask.g.fas_user.username,
                requestfolder=APP.config['REQUESTS_FOLDER'],
            )
            try:
                SESSION.commit()
                flask.flash(message)
            except SQLAlchemyError as err:  # pragma: no cover
                SESSION.rollback()
                APP.logger.exception(err)
                flask.flash(
                    'Could not register this pull-request in the database',
                    'error')

            if not parent.is_fork:
                url = flask.url_for(
                    'request_pulls', username=None, repo=parent.name)
            else:
                url = flask.url_for(
                    'request_pulls', username=parent.user, repo=parent.name)

            return flask.redirect(url)
        except pagure.exceptions.PagureException, err:  # pragma: no cover
            # There could be a PagureException thrown if the flask.g.fas_user
            # wasn't in the DB but then it shouldn't be recognized as a
            # repo admin and thus, if we ever are here, we are in trouble.
            flask.flash(str(err), 'error')
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')

    if not is_repo_admin(repo):
        form = None

    return flask.render_template(
        'pull_request.html',
        select='requests',
        repo=repo,
        username=username,
        repo_obj=repo_obj,
        orig_repo=orig_repo,
        diff_commits=diff_commits,
        diff=diff,
        form=form,
        branches=[
            branch.replace('refs/heads/', '')
            for branch in sorted(orig_repo.listall_references())
        ],
        branch_to=branch_to,
        branch_from=branch_from,
    )
