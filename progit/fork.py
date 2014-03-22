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


import progit.lib
from progit import APP, SESSION, LOG, __get_file_in_tree


### Application
@APP.route('/do_fork/<repo>')
@APP.route('/do_fork/<username>/<repo>')
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
            repo_folder=APP.config['GIT_FOLDER'],
            fork_folder=APP.config['FORK_FOLDER'],
            user=flask.g.fas_user.username)


        SESSION.commit()
        flask.flash(message)
        return flask.redirect(
            flask.url_for('view_fork_repo',
                username=flask.g.fas_user.username, repo=repo.name)
        )
    except progit.exceptions.ProgitException, err:
        flask.flash(str(err), 'error')
    except SQLAlchemyError, err:  # pragma: no cover
        SESSION.rollback()
        flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for('view_repo',repo=repo.name))


@APP.route('/fork/<username>/<repo>')
def view_fork_repo(username, repo):
    """ Front page of a specific repo.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo.path)
    repo_obj = pygit2.Repository(reponame)

    cnt = 0
    last_commits = []
    tree = []
    if not repo_obj.is_empty:
        for commit in repo_obj.walk(
                repo_obj.head.target, pygit2.GIT_SORT_TIME):
            last_commits.append(commit)
            cnt += 1
            if cnt == 10:
                break
        tree = sorted(last_commits[0].tree, key=lambda x: x.filemode)

    parentname = os.path.join(APP.config['GIT_FOLDER'], repo.parent.path)
    orig_repo = pygit2.Repository(parentname)

    diff_commits = []
    if not repo_obj.is_empty and not orig_repo.is_empty:
        orig_commit = orig_repo[orig_repo.head.target]
        repo_commit = repo_obj[repo_obj.head.target]
        diff = repo_obj.diff(
            repo_obj.revparse_single(orig_commit.oid.hex),
            repo_obj.revparse_single(repo_commit.oid.hex))
        for commit in repo_obj.walk(
                repo_obj.head.target, pygit2.GIT_SORT_TIME):
            if commit.oid.hex == orig_commit.oid.hex:
                break
            diff_commits.append(commit.oid.hex)

    return flask.render_template(
        'repo_info.html',
        select='overview',
        repo=repo,
        repo_obj=repo_obj,
        username=username,
        branches=sorted(repo_obj.listall_branches()),
        branchname='master',
        last_commits=last_commits,
        tree=tree,
        diff_commits=diff_commits,
    )


@APP.route('/fork/<username>/<repo>/branch/<branchname>')
def view_fork_repo_branch(username, repo, branchname):
    """ Displays the information about a specific branch.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo.path)
    repo_obj = pygit2.Repository(reponame)

    if not branchname in repo_obj.listall_branches():
        flask.abort(404)

    branch = repo_obj.lookup_branch(branchname)

    cnt = 0
    last_commits = []
    for commit in repo_obj.walk(branch.get_object().hex, pygit2.GIT_SORT_TIME):
        last_commits.append(commit)
        cnt += 1
        if cnt == 10:
            break

    parentname = os.path.join(APP.config['GIT_FOLDER'], repo.parent.path)
    orig_repo = pygit2.Repository(parentname)

    diff_commits = []
    if not repo_obj.is_empty and not orig_repo.is_empty:
        orig_commit = orig_repo[orig_repo.head.target]
        repo_commit = repo_obj[branch.get_object().hex]
        diff = repo_obj.diff(
            repo_obj.revparse_single(orig_commit.oid.hex),
            repo_obj.revparse_single(repo_commit.oid.hex))
        for commit in repo_obj.walk(
                repo_obj.head.target, pygit2.GIT_SORT_TIME):
            if commit.oid.hex == orig_commit.oid.hex:
                break
            diff_commits.append(commit.oid.hex)

    return flask.render_template(
        'repo_info.html',
        select='overview',
        repo=repo,
        username=username,
        branches=sorted(repo_obj.listall_branches()),
        branchname=branchname,
        last_commits=last_commits,
        tree=sorted(last_commits[0].tree, key=lambda x: x.filemode),
        diff_commits=diff_commits,
    )


@APP.route('/fork/<username>/<repo>/log')
@APP.route('/fork/<username>/<repo>/log/<branchname>')
def view_fork_log(username, repo, branchname=None):
    """ Displays the logs of the specified repo.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo.path)
    repo_obj = pygit2.Repository(reponame)

    if branchname and not branchname in repo_obj.listall_branches():
        flask.abort(404)

    if branchname:
        branch = repo_obj.lookup_branch(branchname)
    else:
        branch = repo_obj.lookup_branch('master')

    try:
        page = int(flask.request.args.get('page', 1))
    except ValueError:
        page = 1

    limit = APP.config['ITEM_PER_PAGE']
    start = limit * (page - 1)
    end = limit * page

    n_commits = 0
    last_commits = []
    for commit in repo_obj.walk(
            branch.get_object().hex, pygit2.GIT_SORT_TIME):
        if n_commits >= start and n_commits <= end:
            last_commits.append(commit)
        n_commits += 1

    total_page = int(ceil(n_commits / float(limit)))

    parentname = os.path.join(APP.config['GIT_FOLDER'], repo.parent.path)
    orig_repo = pygit2.Repository(parentname)

    diff_commits = []
    if not repo_obj.is_empty and not orig_repo.is_empty:
        orig_commit = orig_repo[orig_repo.head.target]
        repo_commit = repo_obj[branch.get_object().hex]
        diff = repo_obj.diff(
            repo_obj.revparse_single(orig_commit.oid.hex),
            repo_obj.revparse_single(repo_commit.oid.hex))
        for commit in repo_obj.walk(
                repo_obj.head.target, pygit2.GIT_SORT_TIME):
            if commit.oid.hex == orig_commit.oid.hex:
                break
            diff_commits.append(commit.oid.hex)

    return flask.render_template(
        'repo_info.html',
        select='logs',
        origin='view_fork_log',
        repo=repo,
        username=username,
        branches=sorted(repo_obj.listall_branches()),
        branchname=branchname,
        last_commits=last_commits,
        diff_commits=diff_commits,
        page=page,
        total_page=total_page,
    )


@APP.route('/fork/<username>/<repo>/blob/<identifier>/<path:filename>')
@APP.route('/fork/<username>/<repo>/blob/<identifier>/<path:filename>')
def view_fork_file(username, repo, identifier, filename):
    """ Displays the content of a file or a tree for the specified repo.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo.path)
    repo_obj = pygit2.Repository(reponame)

    if identifier in repo_obj.listall_branches():
        branchname = identifier
        branch = repo_obj.lookup_branch(identifier)
        commit = branch.get_object()
    else:
        try:
            commit = repo_obj.get(identifier)
            branchname = identifier
        except ValueError:
            # If it's not a commit id then it's part of the filename
            commit = repo_obj[repo_obj.head.target]
            branchname = 'master'

    content = __get_file_in_tree(repo_obj, commit.tree, filename.split('/'))
    if not content:
        flask.abort(404, 'File not found')

    content = repo_obj[content.oid]
    if isinstance(content, pygit2.Blob):
        content = highlight(
            content.data,
            guess_lexer(content.data),
            HtmlFormatter(
                noclasses=True,
                style="tango",)
        )
        output_type = 'file'
    else:
        content = sorted(content, key=lambda x: x.filemode)
        output_type = 'tree'

    return flask.render_template(
        'file.html',
        select='tree',
        repo=repo,
        username=username,
        branchname=branchname,
        filename=filename,
        content=content,
        output_type=output_type,
    )


@APP.route('/fork/<username>/<repo>/<commitid>')
def view_fork_commit(username, repo, commitid):
    """ Render a commit in a repo
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo.path)
    repo_obj = pygit2.Repository(reponame)

    try:
        commit = repo_obj.get(commitid)
    except ValueError:
        flask.abort(404)

    if commit.parents:
        diff = commit.tree.diff_to_tree()

        parent = repo_obj.revparse_single('%s^' % commitid)
        diff = repo_obj.diff(parent, commit)
    else:
        # First commit in the repo
        diff = commit.tree.diff_to_tree(swap=True)

    html_diff = highlight(
        diff.patch,
        DiffLexer(),
        HtmlFormatter(
            noclasses=True,
            style="tango",)
    )

    return flask.render_template(
        'commit.html',
        select='logs',
        repo=repo,
        username=username,
        commitid=commitid,
        commit=commit,
        diff=diff,
        html_diff=html_diff,
    )


@APP.route('/fork/<username>/<repo>/tree/')
@APP.route('/fork/<username>/<repo>/tree/<identifier>')
def view_fork_tree(username, repo, identifier=None):
    """ Render the tree of the repo
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo.path)
    repo_obj = pygit2.Repository(reponame)

    if identifier in repo_obj.listall_branches():
        branchname = identifier
        branch = repo_obj.lookup_branch(identifier)
        commit = branch.get_object()
    else:
        try:
            commit = repo_obj.get(identifier)
            branchname = identifier
        except (ValueError, TypeError):
            # If it's not a commit id then it's part of the filename
            commit = repo_obj[repo_obj.head.target]
            branchname = 'master'

    content = sorted(commit.tree, key=lambda x: x.filemode)
    output_type = 'tree'

    return flask.render_template(
        'file.html',
        select='tree',
        repo=repo,
        username=username,
        branchname=branchname,
        filename='',
        content=content,
        output_type=output_type,
    )


@APP.route('/fork/<username>/<repo>/issues')
def view_fork_issues(repo, username):
    """ List all issues associated to a repo
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404)

    issues = progit.lib.get_issues(SESSION, repo)

    return flask.render_template(
        'issues.html',
        select='issues',
        repo=repo,
        username=username,
        issues=issues,
    )


@APP.route('/fork/<username>/<repo>/new_issue', methods=('GET', 'POST'))
def fork_new_issue(username, repo):
    """ Create a new issue
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    form = progit.forms.IssueForm()
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data

        try:
            message = progit.lib.new_issue(
                SESSION,
                repo=repo,
                title=title,
                content=content,
                user=flask.g.fas_user.username,
            )
            SESSION.commit()
            flask.flash(message)
            return flask.redirect(flask.url_for(
                'view_fork_issues', username=username, repo=repo.name))
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


@APP.route('/fork/<username>/<repo>/issue/<issueid>')
def view_fork_issue(username, repo, issueid):
    """ List all issues associated to a repo
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    issue = progit.lib.get_issue(SESSION, issueid)

    if issue is None:
        flask.abort(404, 'Issue not found')

    return flask.render_template(
        'issue.html',
        select='issues',
        repo=repo,
        issue=issue,
        username=username,
    )


@APP.route('/fork/<username>/<repo>/issue/<issueid>/edit',
           methods=('GET', 'POST'))
def fork_edit_issue(username, repo, issueid):
    """ Edit the specified issue opened against a fork
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    issue = progit.lib.get_issue(SESSION, issueid)

    if issue is None:
        flask.abort(404, 'Issue not found')

    form = progit.forms.IssueForm()
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data

        try:
            message = progit.lib.edit_issue(
                SESSION,
                issue=issue,
                title=title,
                content=content,
            )
            SESSION.commit()
            flask.flash(message)
            return flask.redirect(flask.url_for(
                'view_fork_issues', username=username, repo=repo.name))
        except progit.exceptions.ProgitException, err:
            flask.flash(str(err), 'error')
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')
    elif flask.request.method == 'GET':
        form.title.data = issue.title
        form.content.data = issue.content

    return flask.render_template(
        'new_issue.html',
        select='issues',
        type='edit',
        form=form,
        repo=repo,
        username=username,
        issue=issue,
    )


@APP.route('/fork/<username>/<repo>/request-pull')
@APP.route('/fork/<username>/<repo>/request-pull/<commitid>')
def request_pull(username, repo, commitid=None):
    """ Request pulling the changes from the fork into the project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    reponame = os.path.join(APP.config['FORK_FOLDER'], username, repo.path)
    repo_obj = pygit2.Repository(reponame)

    parentname = os.path.join(APP.config['GIT_FOLDER'], repo.parent.path)
    orig_repo = pygit2.Repository(parentname)

    if commitid is None:
        commitid = repo_obj.head.target

    diff_commits = []
    diffs = []
    if not repo_obj.is_empty and not orig_repo.is_empty:
        orig_commit = orig_repo[orig_repo.head.target]
        repo_commit = repo_obj[commitid]

        for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
            if commit.oid.hex == orig_commit.oid.hex:
                break
            diff_commits.append(commit)
            diffs.append(
                repo_obj.diff(
                    repo_obj.revparse_single(commit.parents[0].oid.hex),
                    repo_obj.revparse_single(commit.oid.hex)
                )
            )

    elif orig_repo.is_empty:
        repo_obj = repo_obj[repo_obj.head.target]
        diff = repo_obj.tree.diff_to_tree(swap=True)
    else:
        flask.flash(
            'Fork is empty, there are no commits to request pulling',
            'error')
        return flask.redirect(flask.url_for(
            'view_fork_repo', username=username, repo=repo.name))


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

    return flask.render_template(
        'pull_request.html',
        repo=repo,
        username=username,
        repo_obj=repo_obj,
        orig_repo=orig_repo,
        diff_commits=diff_commits,
        diffs=diffs,
        html_diffs=html_diffs,
    )
