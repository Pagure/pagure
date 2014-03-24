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


import progit.doc_utils
import progit.lib
import progit.forms
from progit import APP, SESSION, LOG, __get_file_in_tree, cla_required


### Application
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
            repo_folder=APP.config['GIT_FOLDER'],
            fork_folder=APP.config['FORK_FOLDER'],
            user=flask.g.fas_user.username)

        SESSION.commit()
        flask.flash(message)
        return flask.redirect(
            flask.url_for(
                'view_fork_repo',
                username=flask.g.fas_user.username,
                repo=repo.name)
        )
    except progit.exceptions.ProgitException, err:
        flask.flash(str(err), 'error')
    except SQLAlchemyError, err:  # pragma: no cover
        SESSION.rollback()
        flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for('view_repo', repo=repo.name))


@APP.route('/fork/<username>/<repo>/request-pull/new',
           methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/request-pull/new/<commitid>',
           methods=('GET', 'POST'))
@cla_required
def new_request_pull(username, repo, commitid=None):
    """ Request pulling the changes from the fork into the project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    repopath = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    repo_obj = pygit2.Repository(repopath)

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
        orig_commit = None
        repo_commit = repo_obj[repo_obj.head.target]
        diff = repo_commit.tree.diff_to_tree(swap=True)
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

    form = progit.forms.RequestPullForm()
    if form.validate_on_submit():
        try:
            if orig_commit:
                orig_commit = orig_commit.oid.hex
            message = progit.lib.new_pull_request(
                SESSION,
                repo=repo.parent,
                repo_from=repo,
                title=form.title.data,
                start_id=orig_commit,
                stop_id=repo_commit.oid.hex,
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
        'pull_request.html',
        repo=repo,
        username=username,
        commitid=commitid,
        repo_obj=repo_obj,
        orig_repo=orig_repo,
        diff_commits=diff_commits,
        diffs=diffs,
        html_diffs=html_diffs,
        form=form,
    )
