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


import progit.app
import progit.exceptions
import progit.lib
import progit.forms
from progit import APP, SESSION, LOG, __get_file_in_tree


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

    repos = progit.lib.list_projects(
        SESSION,
        fork=False,
        start=start,
        limit=limit)
    num_repos = progit.lib.list_projects(
        SESSION,
        fork=False,
        count=True)

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

    repopage = flask.request.args.get('repopage', 1)
    try:
        repopage = int(repopage)
    except ValueError:
        repopage = 1

    forkpage = flask.request.args.get('forkpage', 1)
    try:
        forkpage = int(forkpage)
    except ValueError:
        forkpage = 1

    limit = APP.config['ITEM_PER_PAGE']
    repo_start = limit * (repopage - 1)
    fork_start = limit * (forkpage - 1)

    repos = progit.lib.list_projects(
        SESSION,
        username=flask.g.fas_user.username,
        fork=False,
        start=repo_start,
        limit=limit)
    repos_length = progit.lib.list_projects(
        SESSION,
        username=flask.g.fas_user.username,
        fork=False,
        count=True)

    forks = progit.lib.list_projects(
        SESSION,
        username=flask.g.fas_user.username,
        fork=True,
        start=fork_start,
        limit=limit)
    forks_length = progit.lib.list_projects(
        SESSION,
        username=flask.g.fas_user.username,
        fork=True,
        count=True)

    total_page_repos = int(ceil(repos_length / float(limit)))
    total_page_forks = int(ceil(forks_length / float(limit)))

    repos_obj = [
        pygit2.Repository(
            os.path.join(APP.config['GIT_FOLDER'], repo.path))
        for repo in repos]

    forks_obj = [
        pygit2.Repository(
            os.path.join(APP.config['FORK_FOLDER'], repo.path))
        for repo in forks]

    return flask.render_template(
        'user_info.html',
        username=username,
        repos=repos,
        repos_obj=repos_obj,
        total_page_repos=total_page_repos,
        forks=forks,
        forks_obj=forks_obj,
        total_page_forks=total_page_forks,
        repopage=repopage,
        forkpage=forkpage,
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
    return progit.app.view_repo(repo=repo)


@APP.route('/fork/<username>/<repo>')
def view_fork_repo(username, repo):
    """ Front page of a specific repo.
    """
    return progit.app.view_repo(repo=repo, username=username)


@APP.route('/<repo>/branch/<branchname>')
def view_repo_branch(repo, branchname):
    return progit.app.view_repo_branch(repo, branchname)


@APP.route('/fork/<username>/<repo>/branch/<branchname>')
def view_fork_repo_branch(username, repo, branchname):
    """ Displays the information about a specific branch.
    """
    return progit.app.view_repo_branch(repo, branchname, username=username)


@APP.route('/<repo>/log')
@APP.route('/<repo>/log/<branchname>')
def view_log(repo, branchname=None):
    """ Displays the logs of the specified repo.
    """
    return progit.app.view_log(repo, branchname)


@APP.route('/fork/<username>/<repo>/log')
@APP.route('/fork/<username>/<repo>/log/<branchname>')
def view_fork_log(username, repo, branchname=None):
    """ Displays the logs of the specified repo.
    """
    return progit.app.view_log(repo, branchname, username=username)


@APP.route('/<repo>/blob/<identifier>/<path:filename>')
@APP.route('/<repo>/blob/<identifier>/<path:filename>')
def view_file(repo, identifier, filename):
    """ Displays the content of a file or a tree for the specified repo.
    """
    return progit.app.view_file(repo, identifier, filename)


@APP.route('/fork/<username>/<repo>/blob/<identifier>/<path:filename>')
@APP.route('/fork/<username>/<repo>/blob/<identifier>/<path:filename>')
def view_fork_file(username, repo, identifier, filename):
    """ Displays the content of a file or a tree for the specified repo.
    """
    return progit.app.view_file(repo, identifier, filename, username=username)


@APP.route('/<repo>/<commitid>')
def view_commit(repo, commitid):
    """ Render a commit in a repo
    """
    return progit.app.view_commit(repo, commitid)


@APP.route('/fork/<username>/<repo>/<commitid>')
def view_fork_commit(username, repo, commitid):
    """ Render a commit in a repo
    """
    return progit.app.view_commit(repo, commitid, username=username)


@APP.route('/<repo>/tree/')
@APP.route('/<repo>/tree/<identifier>')
def view_tree(repo, identifier=None):
    """ Render the tree of the repo
    """
    return progit.app.view_tree(repo, identifier=identifier)


@APP.route('/fork/<username>/<repo>/tree/')
@APP.route('/fork/<username>/<repo>/tree/<identifier>')
def view_fork_tree(username, repo, identifier=None):
    """ Render the tree of the repo
    """
    return progit.app.view_tree(repo, identifier=identifier, username=username)


@APP.route('/<repo>/issues')
def view_issues(repo):
    """ List all issues associated to a repo
    """
    status = flask.request.args.get('status', None)
    return progit.app.view_issues(repo, status=status)


@APP.route('/fork/<username>/<repo>/issues')
def view_fork_issues(repo, username):
    """ List all issues associated to a repo
    """
    status = flask.request.args.get('status', None)
    return progit.app.view_issues(repo, username=username, status=status)


@APP.route('/<repo>/new_issue', methods=('GET', 'POST'))
def new_issue(repo):
    """ Create a new issue
    """
    return progit.app.new_issue(repo)


@APP.route('/fork/<username>/<repo>/new_issue', methods=('GET', 'POST'))
def fork_new_issue(username, repo):
    """ Create a new issue
    """
    return progit.app.new_issue(repo, username=username)


@APP.route('/<repo>/issue/<issueid>', methods=('GET', 'POST'))
def view_issue(repo, issueid):
    """ List all issues associated to a repo
    """
    return progit.app.view_issue(repo, issueid)


@APP.route('/fork/<username>/<repo>/issue/<issueid>',
           methods=('GET', 'POST'))
def view_fork_issue(username, repo, issueid):
    """ List all issues associated to a repo
    """
    return progit.app.view_issue(repo, issueid, username=username)


@APP.route('/<repo>/issue/<issueid>/edit', methods=('GET', 'POST'))
def edit_issue(repo, issueid):
    """ Edit the specified issue
    """
    return progit.app.edit_issue(repo, issueid)


@APP.route('/fork/<username>/<repo>/issue/<issueid>/edit',
           methods=('GET', 'POST'))
def fork_edit_issue(username, repo, issueid):
    """ Edit the specified issue opened against a fork
    """
    return progit.app.edit_issue(repo, issueid, username=username)


@APP.route('/<repo>/request-pulls')
def request_pulls(repo):
    """ Request pulling the changes from the fork into the project.
    """
    return progit.app.request_pulls(repo)


@APP.route('/fork/<username>/<repo>/request-pulls')
def fork_request_pulls(username, repo):
    """ Request pulling the changes from the fork into the project.
    """
    return progit.app.request_pulls(repo, username=username)


@APP.route('/<repo>/request-pull/<requestid>')
def request_pull(repo, requestid):
    """ Request pulling the changes from the fork into the project.
    """
    return progit.app.request_pull(repo, requestid)


@APP.route('/fork/<username>/<repo>/request-pull/<requestid>')
def fork_request_pull(username, repo, requestid):
    """ Request pulling the changes from the fork into the project.
    """
    return progit.app.request_pull(repo, requestid, username=username)


@APP.route('/<repo>/request-pull/merge/<requestid>')
def merge_request_pull(repo, requestid):
    """ Request pulling the changes from the fork into the project.
    """
    return progit.app.merge_request_pull(repo, requestid)


@APP.route('/fork/<username>/<repo>/request-pull/merge/<requestid>')
def fork_merge_request_pull(username, repo, requestid):
    """ Request pulling the changes from the fork into the project.
    """
    return progit.app.merge_request_pull(repo, requestid, username=username)


@APP.route('/<repo>/forks')
def view_forks(repo):
    """ Presents all the forks of the project.
    """
    return progit.app.view_forks(repo)


@APP.route('/fork/<username>/<repo>/forks')
def fork_view_forks(username, repo):
    """ Presents all the forks of the fork.
    """
    return progit.app.view_forks(repo, username=username)
