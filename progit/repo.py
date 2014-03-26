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


import progit.exceptions
import progit.lib
import progit.forms
from progit import APP, SESSION, LOG, __get_file_in_tree, cla_required


### Application
def do_view_repo(repo, username=None):
    """ Front page of a specific repo.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        reponame = os.path.join(APP.config['FORK_FOLDER'], repo.path)
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

    readme = None
    for i in tree:
        name, ext = os.path.splitext(i.name)
        if name == 'README':
            content = repo_obj[i.oid].data
            readme = progit.doc_utils.convert_readme(content, ext)

    diff_commits = []
    if repo.is_fork:
        parentname = os.path.join(
            APP.config['GIT_FOLDER'], repo.parent.path)
        orig_repo = pygit2.Repository(parentname)

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
        readme=readme,
        branches=sorted(repo_obj.listall_branches()),
        branchname='master',
        last_commits=last_commits,
        tree=tree,
        diff_commits=diff_commits,
    )


def do_view_repo_branch(repo, branchname, username=None):
    """ Displays the information about a specific branch.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        reponame = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    repo_obj = pygit2.Repository(reponame)

    if not branchname in repo_obj.listall_branches():
        flask.abort(404, 'Branch no found')

    branch = repo_obj.lookup_branch(branchname)

    cnt = 0
    last_commits = []
    for commit in repo_obj.walk(branch.get_object().hex, pygit2.GIT_SORT_TIME):
        last_commits.append(commit)
        cnt += 1
        if cnt == 10:
            break

    diff_commits = []
    if repo.is_fork:
        parentname = os.path.join(
            APP.config['GIT_FOLDER'], repo.parent.path)
        orig_repo = pygit2.Repository(parentname)

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


def do_view_log(repo, branchname=None, username=None):
    """ Displays the logs of the specified repo.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        reponame = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    repo_obj = pygit2.Repository(reponame)

    if branchname and not branchname in repo_obj.listall_branches():
        flask.abort(404, 'Branch no found')

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
    if branch:
        for commit in repo_obj.walk(
                branch.get_object().hex, pygit2.GIT_SORT_TIME):
            if n_commits >= start and n_commits <= end:
                last_commits.append(commit)
            n_commits += 1

    total_page = int(ceil(n_commits / float(limit)))

    diff_commits = []
    if repo.is_fork:
        parentname = os.path.join(
            APP.config['GIT_FOLDER'], repo.parent.path)
        orig_repo = pygit2.Repository(parentname)
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

    origin = 'view_log'

    return flask.render_template(
        'repo_info.html',
        select='logs',
        origin=origin,
        repo_obj=repo_obj,
        repo=repo,
        username=username,
        branches=sorted(repo_obj.listall_branches()),
        branchname=branchname,
        last_commits=last_commits,
        diff_commits=diff_commits,
        page=page,
        total_page=total_page,
    )


def do_view_file(repo, identifier, filename, username=None):
    """ Displays the content of a file or a tree for the specified repo.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        reponame = os.path.join(APP.config['FORK_FOLDER'], repo.path)
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


def do_view_commit(repo, commitid, username=None):
    """ Render a commit in a repo
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        reponame = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    repo_obj = pygit2.Repository(reponame)

    try:
        commit = repo_obj.get(commitid)
    except ValueError:
        flask.abort(404, 'Commit not found')

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


def do_view_tree(repo, identifier=None, username=None):
    """ Render the tree of the repo
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        reponame = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    repo_obj = pygit2.Repository(reponame)

    branchname = None
    content = None
    output_type = None
    if not repo_obj.is_empty:
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
        repo_obj=repo_obj,
        repo=repo,
        username=username,
        branchname=branchname,
        filename='',
        content=content,
        output_type=output_type,
    )


def do_view_forks(repo, username=None):
    """ Return the list of forks of a project.
    """

    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    return flask.render_template(
        'forks.html',
        select='forks',
        username=username,
        repo=repo,
    )


## URLs


@APP.route('/<repo>')
@APP.route('/fork/<username>/<repo>')
def view_repo(repo, username=None):
    """ Front page of a specific repo.
    """
    return do_view_repo(repo=repo, username=username)


@APP.route('/<repo>/branch/<branchname>')
@APP.route('/fork/<username>/<repo>/branch/<branchname>')
def view_repo_branch(repo, branchname, username=None):
    return do_view_repo_branch(repo, branchname, username=username)


@APP.route('/<repo>/log')
@APP.route('/<repo>/log/<branchname>')
@APP.route('/fork/<username>/<repo>/log')
@APP.route('/fork/<username>/<repo>/log/<branchname>')
def view_log(repo, branchname=None, username=None):
    """ Displays the logs of the specified repo.
    """
    return do_view_log(repo, branchname, username=username)


@APP.route('/<repo>/blob/<identifier>/<path:filename>')
@APP.route('/<repo>/blob/<identifier>/<path:filename>')
@APP.route('/fork/<username>/<repo>/blob/<identifier>/<path:filename>')
@APP.route('/fork/<username>/<repo>/blob/<identifier>/<path:filename>')
def view_file(repo, identifier, filename, username=None):
    """ Displays the content of a file or a tree for the specified repo.
    """
    return do_view_file(repo, identifier, filename, username=username)


@APP.route('/<repo>/<commitid>')
@APP.route('/fork/<username>/<repo>/<commitid>')
def view_commit(repo, commitid, username=None):
    """ Render a commit in a repo
    """
    return do_view_commit(repo, commitid, username=username)


@APP.route('/<repo>/tree/')
@APP.route('/<repo>/tree/<identifier>')
@APP.route('/fork/<username>/<repo>/tree/')
@APP.route('/fork/<username>/<repo>/tree/<identifier>')
def view_tree(repo, identifier=None, username=None):
    """ Render the tree of the repo
    """
    return do_view_tree(repo, identifier=identifier, username=username)


@APP.route('/<repo>/forks')
@APP.route('/fork/<username>/<repo>/forks')
def view_forks(repo, username=None):
    """ Presents all the forks of the project.
    """
    return do_view_forks(repo, username=username)
