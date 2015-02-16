#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import os
import shutil
import tempfile
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
                    is_repo_admin, generate_gitolite_acls)


@APP.route('/<repo>/request-pulls')
@APP.route('/fork/<username>/<repo>/request-pulls')
def request_pulls(repo, username=None):
    """ Request pulling the changes from the fork into the project.
    """
    status = flask.request.args.get('status', True)

    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if status is False or str(status).lower() == 'closed':
        requests = progit.lib.get_pull_requests(
            SESSION, project_id=repo.id, status=False)
    else:
        requests = progit.lib.get_pull_requests(
            SESSION, project_id=repo.id, status=status)

    return flask.render_template(
        'requests.html',
        select='requests',
        repo=repo,
        username=username,
        requests=requests,
        status=status,
    )


@APP.route('/<repo>/request-pull/<int:requestid>')
@APP.route('/fork/<username>/<repo>/request-pull/<int:requestid>')
def request_pull(repo, requestid, username=None):
    """ Request pulling the changes from the fork into the project.
    """

    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    request = progit.lib.get_pull_request(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    repo_from = request.repo_from

    if repo_from.is_fork:
        repopath = os.path.join(APP.config['FORK_FOLDER'], repo_from.path)
    else:
        repopath = os.path.join(APP.config['GIT_FOLDER'], repo_from.path)
    repo_obj = pygit2.Repository(repopath)

    if repo_from.parent:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo_from.parent.path)
    else:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo_from.path)
    orig_repo = pygit2.Repository(parentname)

    branch = repo_obj.lookup_branch(request.branch_from)
    commitid = branch.get_object().hex

    diff_commits = []
    diff = None
    if not repo_obj.is_empty and not orig_repo.is_empty:
        orig_commit = orig_repo[
            orig_repo.lookup_branch(request.branch).get_object().hex]

        master_commits = [
            commit.oid.hex
            for commit in orig_repo.walk(
                orig_repo.lookup_branch(request.branch).get_object().hex,
                pygit2.GIT_SORT_TIME)
        ]
        for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
            if request.status is False \
                    and commit.oid.hex == request.commit_start:
                break
            elif request.status and commit.oid.hex in master_commits:
                break
            diff_commits.append(commit)

        if diff_commits:
            first_commit = repo_obj[diff_commits[-1].oid.hex]
            diff = repo_obj.diff(
                repo_obj.revparse_single(first_commit.parents[0].oid.hex),
                repo_obj.revparse_single(diff_commits[0].oid.hex)
            )
            if request.status:
                request.commit_start = first_commit.oid.hex
                request.commit_stop = diff_commits[0].oid.hex
                SESSION.add(request)
                SESSION.commit()

    elif orig_repo.is_empty:
        orig_commit = None
        repo_commit = repo_obj[request.stop_id]
        diff = repo_commit.tree.diff_to_tree(swap=True)
    else:
        flask.flash(
            'Fork is empty, there are no commits to request pulling',
            'error')
        return flask.redirect(flask.url_for(
            'view_repo', username=username, repo=repo.name))


    form = progit.forms.ConfirmationForm()

    return flask.render_template(
        'pull_request.html',
        select='requests',
        requestid=requestid,
        repo=repo,
        username=username,
        pull_request=request,
        repo_admin=is_repo_admin(request.repo),
        diff_commits=diff_commits,
        diff=diff,
        mergeform=form,
    )


@APP.route('/<repo>/request-pull/<int:requestid>.patch')
@APP.route('/fork/<username>/<repo>/request-pull/<int:requestid>.patch')
def request_pull_patch(repo, requestid, username=None):
    """ Returns the commits from the specified pull-request as patches.
    """

    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    request = progit.lib.get_pull_request(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    repo = request.repo_from

    if repo.is_fork:
        repopath = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    else:
        repopath = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    repo_obj = pygit2.Repository(repopath)

    if repo.parent:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo.parent.path)
    else:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    orig_repo = pygit2.Repository(parentname)

    branch = repo_obj.lookup_branch(request.branch_from)
    commitid = branch.get_object().hex

    diff_commits = []
    if not repo_obj.is_empty and not orig_repo.is_empty:
        orig_commit = orig_repo[
            orig_repo.lookup_branch(request.branch).get_object().hex]

        master_commits = [
            commit.oid.hex
            for commit in orig_repo.walk(
                orig_repo.lookup_branch(request.branch).get_object().hex,
                pygit2.GIT_SORT_TIME)
        ]

        for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
            if request.status is False \
                    and commit.oid.hex == request.commit_start:
                break
            elif request.status and commit.oid.hex in master_commits:
                break
            diff_commits.append(commit)

    elif orig_repo.is_empty:
        orig_commit = None
        repo_commit = repo_obj[request.stop_id]
        diff = repo_commit.tree.diff_to_tree(swap=True)
    else:
        flask.flash(
            'Fork is empty, there are no commits to request pulling',
            'error')
        return flask.redirect(flask.url_for(
            'view_repo', username=username, repo=repo.name))

    diff_commits.reverse()
    patch = progit.lib.commit_to_patch(repo_obj, diff_commits)

    return flask.Response(patch, content_type="text/plain;charset=UTF-8")


@APP.route('/<repo>/request-pull/<int:requestid>/comment/<commit>/<row>',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/request-pull/<int:requestid>/comment/'
           '<commit>/<row>', methods=('GET', 'POST'))
def pull_request_add_comment(repo, requestid, commit, row, username=None):
    """ Add a comment to a commit in a pull-request.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    request = progit.lib.get_pull_request(
        SESSION, project_id=repo.id, requestid=requestid)
    repo = request.repo_from

    if not request:
        flask.abort(404, 'Pull-request not found')

    form = progit.forms.AddPullRequestCommentForm()
    form.commit.data = commit
    form.requestid.data = requestid
    form.row.data = row

    if form.validate_on_submit():
        comment = form.comment.data

        try:
            message = progit.lib.add_pull_request_comment(
                SESSION,
                request=request,
                commit=commit,
                row=row,
                comment=comment,
                user=flask.g.fas_user.username,
            )
            SESSION.commit()
            flask.flash(message)
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
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
        row=row,
        form=form,
    )



@APP.route('/<repo>/request-pull/merge/<int:requestid>', methods=['POST'])
@APP.route('/fork/<username>/<repo>/request-pull/merge/<int:requestid>',
           methods=['POST'])
def merge_request_pull(repo, requestid, username=None):
    """ Request pulling the changes from the fork into the project.
    """

    form = progit.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.flash('Invalid input submitted', 'error')
        return flask.redirect(flask.url_for('view_repo', repo=repo.name))

    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    request = progit.lib.get_pull_request(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to merge pull-request for this project')

    error_output = flask.url_for(
        'request_pull', repo=repo.name, requestid=requestid)
    if username:
        error_output = flask.url_for(
            'fork_request_pull',
            repo=repo.name,
            requestid=requestid,
            username=username)

    # Get the fork
    if request.repo_from.is_fork:
        repopath = os.path.join(
            APP.config['FORK_FOLDER'], request.repo_from.path)
    else:
        repopath = os.path.join(
            APP.config['GIT_FOLDER'], request.repo_from.path)
    fork_obj = pygit2.Repository(repopath)

    # Get the original repo
    parentpath = os.path.join(APP.config['GIT_FOLDER'], request.repo.path)
    orig_repo = pygit2.Repository(parentpath)

    # Clone the original repo into a temp folder
    newpath = tempfile.mkdtemp()
    new_repo = pygit2.clone_repository(parentpath, newpath)

    repo_commit = fork_obj[request.stop_id]

    ori_remote = new_repo.remotes[0]
    # Add the fork as remote repo
    reponame = '%s_%s' % (request.user.user, repo.name)
    remote = new_repo.create_remote(reponame, repopath)

    # Fetch the commits
    remote.fetch()

    merge = new_repo.merge(repo_commit.oid)
    master_ref = new_repo.lookup_reference('HEAD').resolve()

    refname = '%s:%s' % (master_ref.name, master_ref.name)
    if merge.is_uptodate:
        flask.flash('Nothing to do, changes were already merged', 'error')
        progit.lib.close_pull_request(SESSION, request)
        SESSION.commit()
        return flask.redirect(error_output)
    elif merge.is_fastforward:
        master_ref.target = merge.fastforward_oid
        ori_remote.push(refname)
        flask.flash('Changes merged!')
    else:
        new_repo.index.write()
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
        commit = new_repo[head.oid]
        sha = new_repo.create_commit(
            'refs/heads/master',
            repo_commit.author,
            repo_commit.committer,
            'Merge #%s `%s`' % (request.id, request.title),
            tree,
            [head.hex, repo_commit.oid.hex])
        ori_remote.push(refname)
        flask.flash('Changes merged!')

    # Update status
    progit.lib.close_pull_request(SESSION, request, flask.g.fas_user)
    SESSION.commit()
    shutil.rmtree(newpath)

    return flask.redirect(flask.url_for('view_repo', repo=repo.name))


@APP.route('/<repo>/request-pull/cancel/<int:requestid>',
        methods=['POST'])
@APP.route('/fork/<username>/<repo>/request-pull/cancel/<int:requestid>',
        methods=['POST'])
def cancel_request_pull(repo, requestid, username=None):
    """ Cancel request pulling request.
    """

    form = progit.forms.ConfirmationForm()
    if form.validate_on_submit():

        repo = progit.lib.get_project(SESSION, repo, user=username)

        if not repo:
            flask.abort(404, 'Project not found')

        request = progit.lib.get_pull_request(
            SESSION, project_id=repo.id, requestid=requestid)

        if not request:
            flask.abort(404, 'Pull-request not found')

        if not is_repo_admin(repo):
            flask.abort(
                403,
                'You are not allowed to cancel pull-request for this project')

        progit.lib.close_pull_request(
            SESSION, request, flask.g.fas_user, merged=False)
        SESSION.commit()
        flask.flash('Request pull canceled!')
    else:
        flask.flash('Invalid input submitted', 'error')

    return flask.redirect(flask.url_for('view_repo', repo=repo.name))


## Specific actions


@APP.route('/do_fork/<repo>')
@APP.route('/do_fork/<username>/<repo>')
@cla_required
def fork_project(repo, username=None):
    """ Fork the project specified into the user's namespace
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404)

    try:
        message = progit.lib.fork_project(
            session=SESSION,
            repo=repo,
            gitfolder=APP.config['GIT_FOLDER'],
            forkfolder=APP.config['FORK_FOLDER'],
            docfolder=APP.config['DOCS_FOLDER'],
            ticketfolder=APP.config['TICKETS_FOLDER'],
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
    except progit.exceptions.ProgitException, err:
        flask.flash(str(err), 'error')
    except SQLAlchemyError, err:  # pragma: no cover
        SESSION.rollback()
        flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for('view_repo', repo=repo.name))


@APP.route('/<repo>/request-pull/new',
           methods=('GET', 'POST'))
@APP.route('/<repo>/request-pull/new/<commitid>',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/request-pull/new',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/request-pull/new/<commitid>',
           methods=('GET', 'POST'))
@cla_required
def new_request_pull(repo, username=None, commitid=None):
    """ Request pulling the changes from the fork into the project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to create pull-requests for this project')

    if repo.is_fork:
        repopath = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    else:
        repopath = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    repo_obj = pygit2.Repository(repopath)

    if repo.parent:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo.parent.path)
    else:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    orig_repo = pygit2.Repository(parentname)

    frombranchname = flask.request.args.get('from_branch', 'master')
    frombranch = repo_obj.lookup_branch(frombranchname)
    if not frombranch:
        flask.flash('Branch %s does not exist' % frombranchname, 'error')
        frombranchname = 'master'

    branchname = flask.request.args.get('branch', 'master')
    branch = orig_repo.lookup_branch(branchname)
    if not branch:
        flask.flash('Branch %s does not exist' % branchname, 'error')
        branchname = 'master'

    if commitid is None:
        commitid = repo_obj.head.target
        if branchname:
            branch = repo_obj.lookup_branch(frombranchname)
            commitid = branch.get_object().hex

    diff_commits = []
    diffs = []
    if not repo_obj.is_empty and not orig_repo.is_empty:
        orig_commit = orig_repo[
            orig_repo.lookup_branch(branchname).get_object().hex]

        master_commits = [
            commit.oid.hex
            for commit in orig_repo.walk(
                orig_repo.lookup_branch(branchname).get_object().hex,
                pygit2.GIT_SORT_TIME)
        ]

        repo_commit = repo_obj[commitid]

        for commit in repo_obj.walk(
                repo_commit.oid.hex, pygit2.GIT_SORT_TIME):
            if commit.oid.hex in master_commits:
                break
            diff_commits.append(commit)
            diffs.append(
                repo_obj.diff(
                    repo_obj.revparse_single(commit.parents[0].oid.hex),
                    repo_obj.revparse_single(commit.oid.hex)
                )
            )

    elif orig_repo.is_empty:
        orig_commit = None
        repo_commit = repo_obj[repo_obj.head.target]
        diff = repo_commit.tree.diff_to_tree(swap=True)
    else:
        flask.flash(
            'Fork is empty, there are no commits to request pulling',
            'error')
        return flask.redirect(flask.url_for(
            'view_repo', username=username, repo=repo.name))

    html_diffs = []
    for diff in diffs:
        html_diffs.append(
            highlight(
                diff.patch,
                DiffLexer(),
                HtmlFormatter(
                    noclasses=True,
                    style="tango",)
            )
        )

    form = progit.forms.RequestPullForm()
    if form.validate_on_submit():
        try:
            if orig_commit:
                orig_commit = orig_commit.oid.hex

            parent = repo
            if repo.parent:
                parent = repo.parent

            message = progit.lib.new_pull_request(
                SESSION,
                repo=parent,
                repo_from=repo,
                branch=branchname,
                title=form.title.data,
                start_id=orig_commit,
                stop_id=repo_commit.oid.hex,
                user=flask.g.fas_user.username,
            )
            SESSION.commit()
            flask.flash(message)

            if not parent.is_fork:
                url = flask.url_for(
                    'request_pulls', username=None, repo=parent.name)
            else:
                url = flask.url_for(
                    'request_pulls', username=parent.user, repo=parent.name)

            return flask.redirect(url)
        except progit.exceptions.ProgitException, err:
            flask.flash(str(err), 'error')
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')

    return flask.render_template(
        'pull_request.html',
        select='requests',
        repo=repo,
        username=username,
        commitid=commitid,
        repo_obj=repo_obj,
        orig_repo=orig_repo,
        diff_commits=diff_commits,
        diffs=diffs,
        html_diffs=html_diffs,
        form=form,
        branches=[
            branch.replace('refs/heads/', '')
            for branch in sorted(orig_repo.listall_references())
        ],
        branchname=branchname,
    )
