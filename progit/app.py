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
from progit import APP, SESSION, LOG


### Application
@APP.route('/')
def index():
    """ Front page of the application.
    """
    page = flask.request.args.get('page', 1)
    try:
        page = int(page)
    except ValueError:
        page = 1

    limit = APP.config['ITEM_PER_PAGE']
    start = limit * (page - 1)

    repos = progit.lib.list_projects(SESSION, start=start, limit=limit)
    num_repos = progit.lib.count_projects(SESSION)

    total_page = int(ceil(num_repos / float(limit)))

    return flask.render_template(
        'index.html',
        repos=repos,
        total_page=total_page,
        page=page,
    )


@APP.route('/users/')
def view_users():
    """ Present the list of users.
    """
    page = flask.request.args.get('page', 1)
    try:
        page = int(page)
    except ValueError:
        page = 1

    ## TODO: retrieve this from the DB
    users = ['pingou']

    limit = APP.config['ITEM_PER_PAGE']
    start = limit * (page - 1)
    end = limit * page
    users_length = len(users)
    users = users[start:end]

    total_page = int(ceil(users_length / float(limit)))

    return flask.render_template(
        'user_list.html',
        users=users,
        total_page=total_page,
        page=page,
    )


@APP.route('/user/<username>')
def view_user(username):
    """ Front page of a specific user.
    """
    user_folder = os.path.join(APP.config['FORK_FOLDER'], username)
    if not os.path.exists(user_folder):
        flask.abort(404)

    page = flask.request.args.get('page', 1)
    try:
        page = int(page)
    except ValueError:
        page = 1

    repos = sorted(os.listdir(user_folder))

    limit = APP.config['ITEM_PER_PAGE']
    start = limit * (page - 1)
    end = limit * page
    repos_length = len(repos)
    repos = repos[start:end]

    total_page = int(ceil(repos_length / float(limit)))

    repos_obj = [
        pygit2.Repository(
            os.path.join(APP.config['FORK_FOLDER'], username, repo))
        for repo in repos]

    return flask.render_template(
        'user_info.html',
        username=username,
        repos=repos,
        repos_obj=repos_obj,
        total_page=total_page,
        page=page,
    )


@APP.route('/new/', methods=('GET', 'POST'))
def new_project():
    """ Form to create a new project.
    """
    form = progit.forms.ProjectForm()
    if form.validate_on_submit():
        name = form.name.data
        description = form.description.data

        try:
            message = progit.lib.new_project(
                SESSION,
                name=name,
                description=description,
                user=flask.g.fas_user.username,
                folder=APP.config['GIT_FOLDER'],
            )
            SESSION.commit()
            flask.flash(message)
            return flask.redirect(flask.url_for('view_repo', repo=name))
        except progit.exceptions.ProgitException, err:
            flask.flash(str(err), 'error')
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')

    return flask.render_template(
        'new_project.html',
        form=form,
    )


@APP.route('/<repo>')
def view_repo(repo):
    """ Front page of a specific repo.
    """
    repo = progit.lib.get_project(SESSION, repo)

    if repo is None:
        flask.abort(404)

    repo_obj = pygit2.Repository(os.path.join(APP.config["GIT_FOLDER"],
                                 repo.path))

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

    return flask.render_template(
        'repo_info.html',
        repo=repo,
        branches=sorted(repo_obj.listall_branches()),
        branchname='master',
        last_commits=last_commits,
        tree=tree,
    )


@APP.route('/<repo>/branch/<branchname>')
def view_repo_branch(repo, branchname):
    """ Displays the information about a specific branch.
    """
    repo = progit.lib.get_project(SESSION, repo)

    if repo is None:
        flask.abort(404)

    repo_obj = pygit2.Repository(os.path.join(APP.config["GIT_FOLDER"],
                                 repo.path))


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

    return flask.render_template(
        'repo_info.html',
        repo=repo,
        branches=sorted(repo_obj.listall_branches()),
        branchname=branchname,
        last_commits=last_commits,
        tree=sorted(last_commits[0].tree, key=lambda x: x.filemode),
    )


@APP.route('/<repo>/log')
@APP.route('/<repo>/log/<branchname>')
def view_log(repo, branchname=None):
    """ Displays the logs of the specified repo.
    """
    repo = progit.lib.get_project(SESSION, repo)

    if repo is None:
        flask.abort(404)

    repo_obj = pygit2.Repository(os.path.join(APP.config["GIT_FOLDER"],
                                 repo.path))

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

    return flask.render_template(
        'repo_info.html',
        origin='view_log',
        repo=repo,
        branches=sorted(repo_obj.listall_branches()),
        branchname=branchname,
        last_commits=last_commits,
        page=page,
        total_page=total_page,
    )


@APP.route('/<repo>/blob/<identifier>/<path:filename>')
@APP.route('/<repo>/blob/<identifier>/<path:filename>')
def view_file(repo, identifier, filename):
    """ Displays the content of a file or a tree for the specified repo.
    """
    repo = progit.lib.get_project(SESSION, repo)

    if repo is None:
        flask.abort(404)

    repo_obj = pygit2.Repository(os.path.join(APP.config["GIT_FOLDER"],
                                 repo.path))

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

    def __get_file_in_tree(tree, filepath):
        ''' Retrieve the entry corresponding to the provided filename in a
        given tree.
        '''
        filename = filepath[0]
        if isinstance(tree, pygit2.Blob):
            return
        for el in tree:
            if el.name == filename:
                if len(filepath) == 1:
                    return repo_obj[el.oid]
                else:
                    return __get_file_in_tree(repo_obj[el.oid], filepath[1:])

    content = __get_file_in_tree(commit.tree, filename.split('/'))
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
        repo=repo,
        branchname=branchname,
        filename=filename,
        content=content,
        output_type=output_type,
    )


@APP.route('/<repo>/<commitid>')
def view_commit(repo, commitid):
    """ Render a commit in a repo
    """
    repo = progit.lib.get_project(SESSION, repo)

    if repo is None:
        flask.abort(404)

    repo_obj = pygit2.Repository(os.path.join(APP.config["GIT_FOLDER"],
                                 repo.path))

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
        repo=repo,
        commitid=commitid,
        commit=commit,
        diff=diff,
        html_diff=html_diff,
    )


@APP.route('/<repo>/tree/')
@APP.route('/<repo>/tree/<identifier>')
def view_tree(repo, identifier=None):
    """ Render the tree of the repo
    """
    repo = progit.lib.get_project(SESSION, repo)

    if repo is None:
        flask.abort(404)

    repo_obj = pygit2.Repository(os.path.join(APP.config["GIT_FOLDER"],
                                 repo.path))

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
        repo=repo,
        branchname=branchname,
        filename='',
        content=content,
        output_type=output_type,
    )
