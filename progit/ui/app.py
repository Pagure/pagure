# -*- coding: utf-8 -*-

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
import progit.ui.filters
from progit import (APP, SESSION, LOG, __get_file_in_tree, cla_required,
                    generate_gitolite_acls, generate_gitolite_key,
                    generate_authorized_key_file, authenticated)


# Application


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

    repos = progit.lib.search_projects(
        SESSION,
        fork=False,
        start=start,
        limit=limit)
    num_repos = progit.lib.search_projects(
        SESSION,
        fork=False,
        count=True)

    total_page = int(ceil(num_repos / float(limit)))

    repopage = None
    forkpage = None
    user_repos = None
    user_forks = None
    total_page_repos = None
    total_page_forks = None
    repos_obj = None
    forks_obj = None
    username = None
    user_repos_length = None
    user_forks_length = None

    if authenticated():
        username = flask.g.fas_user.username

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

        repo_start = limit * (repopage - 1)
        fork_start = limit * (forkpage - 1)

        user_repos = progit.lib.search_projects(
            SESSION,
            username=username,
            fork=False,
            start=repo_start,
            limit=limit)
        user_repos_length = progit.lib.search_projects(
            SESSION,
            username=username,
            fork=False,
            count=True)

        user_forks = progit.lib.search_projects(
            SESSION,
            username=username,
            fork=True,
            start=fork_start,
            limit=limit)
        user_forks_length = progit.lib.search_projects(
            SESSION,
            username=username,
            fork=True,
            count=True)

        total_page_repos = int(ceil(user_repos_length / float(limit)))
        total_page_forks = int(ceil(user_forks_length / float(limit)))

        repos_obj = [
            pygit2.Repository(
                os.path.join(APP.config['GIT_FOLDER'], repo.path))
            for repo in user_repos]

        forks_obj = [
            pygit2.Repository(
                os.path.join(APP.config['FORK_FOLDER'], repo.path))
            for repo in user_forks]

    return flask.render_template(
        'index.html',
        repos=repos,
        total_page=total_page,
        page=page,
        username=username,
        repopage=repopage,
        forkpage=forkpage,
        user_repos=user_repos,
        user_forks=user_forks,
        total_page_repos=total_page_repos,
        total_page_forks=total_page_forks,
        repos_obj=repos_obj,
        forks_obj=forks_obj,
        user_repos_length=user_repos_length,
        user_forks_length=user_forks_length,
        repos_length=num_repos,
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

    users = progit.lib.search_user(SESSION)

    limit = APP.config['ITEM_PER_PAGE']
    start = limit * (page - 1)
    end = limit * page
    users_length = len(users)
    users = users[start:end]

    total_page = int(ceil(users_length / float(limit)))

    return flask.render_template(
        'user_list.html',
        users=users,
        users_length=users_length,
        total_page=total_page,
        page=page,
    )


@APP.route('/user/<username>')
def view_user(username):
    """ Front page of a specific user.
    """
    user = progit.lib.search_user(SESSION, username=username)

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

    repos = progit.lib.search_projects(
        SESSION,
        username=username,
        fork=False,
        start=repo_start,
        limit=limit)
    repos_length = progit.lib.search_projects(
        SESSION,
        username=username,
        fork=False,
        count=True)

    forks = progit.lib.search_projects(
        SESSION,
        username=username,
        fork=True,
        start=fork_start,
        limit=limit)
    forks_length = progit.lib.search_projects(
        SESSION,
        username=username,
        fork=True,
        count=True)

    total_page_repos = int(ceil(repos_length / float(limit)))
    total_page_forks = int(ceil(forks_length / float(limit)))

    repos_obj = [
        pygit2.Repository(
            os.path.join(APP.config['GIT_FOLDER'], repo.path))
        for repo in repos
        if os.path.exists(
            os.path.join(APP.config['GIT_FOLDER'], repo.path))
        ]

    forks_obj = [
        pygit2.Repository(
            os.path.join(APP.config['FORK_FOLDER'], repo.path))
        for repo in forks
        if os.path.exists(
            os.path.join(APP.config['FORK_FOLDER'], repo.path))
        ]

    return flask.render_template(
        'user_info.html',
        username=username,
        user=user,
        repos=repos,
        repos_obj=repos_obj,
        total_page_repos=total_page_repos,
        forks=forks,
        forks_obj=forks_obj,
        total_page_forks=total_page_forks,
        repopage=repopage,
        forkpage=forkpage,
        repos_length=repos_length,
        forks_length=forks_length,
    )


@APP.route('/new/', methods=('GET', 'POST'))
@cla_required
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
                gitfolder=APP.config['GIT_FOLDER'],
                docfolder=APP.config['DOCS_FOLDER'],
                ticketfolder=APP.config['TICKETS_FOLDER'],
                requestfolder=APP.config['REQUESTS_FOLDER'],
            )
            SESSION.commit()
            generate_gitolite_acls()
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


@APP.route('/settings/', methods=('GET', 'POST'))
@cla_required
def user_settings():
    """ Update the user settings.
    """
    user = progit.lib.search_user(
        SESSION, username=flask.g.fas_user.username)
    if not user:
        flask.abort(404, 'User not found')

    form = progit.forms.UserSettingsForm()
    if form.validate_on_submit():
        ssh_key = form.ssh_key.data

        try:
            message = progit.lib.update_user_ssh(
                SESSION,
                user=user,
                ssh_key=ssh_key,
            )
            if message != 'Nothing to update':
                generate_gitolite_key(user.user, ssh_key)
                generate_authorized_key_file()
            SESSION.commit()
            flask.flash(message)
            return flask.redirect(
                flask.url_for('view_user', username=user.user))
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')
    elif flask.request.method == 'GET':
        form.ssh_key.data = user.public_ssh_key

    return flask.render_template(
        'user_settings.html',
        user=user,
        form=form,
    )


@APP.route('/markdown/', methods=['POST'])
def markdown_preview():
    """ Return the provided markdown text in html.

    The text has to be provided via the parameter 'content' of a POST query.
    """
    form = progit.forms.ConfirmationForm()
    if form.validate_on_submit():
        return progit.ui.filters.markdown_filter(flask.request.form['content'])
    else:
        flask.abort(400, 'Invalid request')
