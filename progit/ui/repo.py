#-*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import shutil
import os
from math import ceil

import pygit2
from cStringIO import StringIO
from sqlalchemy.exc import SQLAlchemyError
from PIL import Image
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import guess_lexer_for_filename
from pygments.lexers.text import DiffLexer
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound

import mimetypes
import chardet

import progit.exceptions
import progit.lib
import progit.lib.git
import progit.forms
import progit.ui.plugins
from progit import (APP, SESSION, LOG, __get_file_in_tree, cla_required,
                    is_repo_admin)


@APP.route('/<repo>')
@APP.route('/fork/<username>/<repo>')
def view_repo(repo, username=None):
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
        if repo.parent.is_fork:
            parentname = os.path.join(
                APP.config['FORK_FOLDER'], repo.parent.path)
    elif repo.parent:
        parentname = os.path.join(
            APP.config['GIT_FOLDER'], repo.parent.path)
    else:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo.path)

    orig_repo = pygit2.Repository(parentname)

    if not repo_obj.is_empty and not orig_repo.is_empty:
        orig_commit = orig_repo[
            orig_repo.lookup_branch('master').get_object().hex]

        master_commits = [
            commit.oid.hex
            for commit in orig_repo.walk(
                orig_repo.lookup_branch('master').get_object().hex,
                pygit2.GIT_SORT_TIME)
        ]

        repo_commit = repo_obj[
            repo_obj.lookup_branch('master').get_object().hex]

        for commit in repo_obj.walk(
                repo_commit.oid.hex, pygit2.GIT_SORT_TIME):
            if commit.oid.hex in master_commits:
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


@APP.route('/<repo>/branch/<branchname>')
@APP.route('/fork/<username>/<repo>/branch/<branchname>')
def view_repo_branch(repo, branchname, username=None):
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        reponame = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    repo_obj = pygit2.Repository(reponame)

    if branchname not in repo_obj.listall_branches():
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
        if repo.parent.is_fork:
            parentname = os.path.join(
                APP.config['FORK_FOLDER'], repo.parent.path)
    elif repo.parent:
        parentname = os.path.join(
            APP.config['GIT_FOLDER'], repo.parent.path)
    else:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo.path)

    orig_repo = pygit2.Repository(parentname)

    if not repo_obj.is_empty and not orig_repo.is_empty:
        orig_commit = orig_repo[
            orig_repo.lookup_branch('master').get_object().hex]

        master_commits = [
            commit.oid.hex
            for commit in orig_repo.walk(
                orig_repo.lookup_branch('master').get_object().hex,
                pygit2.GIT_SORT_TIME)
        ]

        repo_commit = repo_obj[branch.get_object().hex]

        for commit in repo_obj.walk(
                repo_commit.oid.hex, pygit2.GIT_SORT_TIME):
            if commit.oid.hex in master_commits:
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


@APP.route('/<repo>/log')
@APP.route('/<repo>/log/<branchname>')
@APP.route('/fork/<username>/<repo>/log')
@APP.route('/fork/<username>/<repo>/log/<branchname>')
def view_log(repo, branchname=None, username=None):
    """ Displays the logs of the specified repo.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        reponame = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    repo_obj = pygit2.Repository(reponame)

    if branchname and branchname not in repo_obj.listall_branches():
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
        if repo.parent.is_fork:
            parentname = os.path.join(
                APP.config['FORK_FOLDER'], repo.parent.path)
    elif repo.parent:
        parentname = os.path.join(
            APP.config['GIT_FOLDER'], repo.parent.path)
    else:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo.path)

    orig_repo = pygit2.Repository(parentname)

    if not repo_obj.is_empty and not orig_repo.is_empty:
        orig_commit = orig_repo[
            orig_repo.lookup_branch('master').get_object().hex]

        master_commits = [
            commit.oid.hex
            for commit in orig_repo.walk(
                orig_repo.lookup_branch('master').get_object().hex,
                pygit2.GIT_SORT_TIME)
        ]

        repo_commit = repo_obj[branch.get_object().hex]

        for commit in repo_obj.walk(
                repo_commit.oid.hex, pygit2.GIT_SORT_TIME):
            if commit.oid.hex in master_commits:
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


@APP.route('/<repo>/blob/<identifier>/<path:filename>')
@APP.route('/fork/<username>/<repo>/blob/<identifier>/<path:filename>')
def view_file(repo, identifier, filename, username=None):
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

    if commit and not isinstance(commit, pygit2.Blob):
        content = __get_file_in_tree(
            repo_obj, commit.tree, filename.split('/'))
        if not content:
            flask.abort(404, 'File not found')
        content = repo_obj[content.oid]
    else:
        content = commit

    if not content:
            flask.abort(404, 'File not found')

    if isinstance(content, pygit2.Blob):
        if content.is_binary:
            ext = filename[filename.rfind('.'):]
            if ext in ('.gif', '.png', '.bmp', '.tif', '.tiff', '.jpg',
                    '.jpeg', '.ppm', '.pnm', '.pbm', '.pgm', '.webp', '.ico'):
                try:
                    Image.open(StringIO(content.data))
                    output_type = 'image'
                except IOError as err:
                    LOG.debug(
                        'Failed to load image %s, error: %s', filename, err
                    )
                    output_type = 'binary'
            else:
                output_type = 'binary'
        else:
            try:
                lexer = guess_lexer_for_filename(
                    filename,
                    content.data
                )
            except ClassNotFound:
                lexer = TextLexer()

            content = highlight(
                content.data,
                lexer,
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


@APP.route('/<repo>/raw/<identifier>', defaults={'filename': None})
@APP.route('/<repo>/raw/<identifier>/<path:filename>')
@APP.route('/fork/<username>/<repo>/raw/<identifier>', defaults={'filename': None})
@APP.route('/fork/<username>/<repo>/raw/<identifier>/<path:filename>')
def view_raw_file(repo, identifier, filename=None, username=None):
    """ Displays the raw content of a file of a commit for the specified repo.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        reponame = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    repo_obj = pygit2.Repository(reponame)

    if identifier in repo_obj.listall_branches():
        branch = repo_obj.lookup_branch(identifier)
        commit = branch.get_object()
    else:
        try:
            commit = repo_obj.get(identifier)
        except ValueError:
            # If it's not a commit id then it's part of the filename
            commit = repo_obj[repo_obj.head.target]

    mimetype = None
    encoding = None
    if filename:
        content = __get_file_in_tree(repo_obj, commit.tree, filename.split('/'))
        if not content:
            flask.abort(404, 'File not found')

        mimetype, encoding = mimetypes.guess_type(filename)
        data = repo_obj[content.oid].data
    else:
        if commit.parents:
            diff = commit.tree.diff_to_tree()

            parent = repo_obj.revparse_single('%s^' % identifier)
            diff = repo_obj.diff(parent, commit)
        else:
            # First commit in the repo
            diff = commit.tree.diff_to_tree(swap=True)
        data = diff.patch

    if not mimetype and data[:2] == '#!':
        mimetype = 'text/plain'

    if not mimetype:
        if '\0' in data:
            mimetype = 'application/octet-stream'
        else:
            mimetype = 'text/plain'

    if mimetype.startswith('text/') and not encoding:
        encoding = chardet.detect(bytes(data))['encoding']

    headers = {'Content-Type': mimetype}
    if encoding:
        headers['Content-Encoding'] = encoding

    return (data, 200, headers)


@APP.route('/<repo>/<commitid>')
@APP.route('/fork/<username>/<repo>/<commitid>')
def view_commit(repo, commitid, username=None):
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

    if commit is None:
        flask.abort(404, 'Commit not found')

    if commit.parents:
        diff = commit.tree.diff_to_tree()

        parent = repo_obj.revparse_single('%s^' % commitid)
        diff = repo_obj.diff(parent, commit)
    else:
        # First commit in the repo
        diff = commit.tree.diff_to_tree(swap=True)

    return flask.render_template(
        'commit.html',
        select='logs',
        repo=repo,
        username=username,
        commitid=commitid,
        commit=commit,
        diff=diff,
    )


@APP.route('/<repo>/<commitid>.patch')
@APP.route('/fork/<username>/<repo>/<commitid>.patch')
def view_commit_patch(repo, commitid, username=None):
    """ Render a commit in a repo as patch
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

    patch = progit.lib.git.commit_to_patch(repo_obj, commit)

    return flask.Response(patch, content_type="text/plain;charset=UTF-8")


@APP.route('/<repo>/tree/')
@APP.route('/<repo>/tree/<identifier>')
@APP.route('/fork/<username>/<repo>/tree/')
@APP.route('/fork/<username>/<repo>/tree/<identifier>')
def view_tree(repo, identifier=None, username=None):
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


@APP.route('/<repo>/forks')
@APP.route('/fork/<username>/<repo>/forks')
def view_forks(repo, username=None):
    """ Presents all the forks of the project.
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


@APP.route('/<repo>/settings', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/settings', methods=('GET', 'POST'))
@cla_required
def view_settings(repo, username=None):
    """ Presents the settings of the project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    plugins = progit.ui.plugins.get_plugin_names()
    tags = progit.lib.get_tags_of_project(SESSION, repo)

    form = progit.forms.ProjectSettingsForm()
    tag_form = progit.forms.AddIssueTagForm()

    if form.validate_on_submit():
        issue_tracker = form.issue_tracker.data
        project_docs = form.project_docs.data

        try:
            message = progit.lib.update_project_settings(
                SESSION,
                repo=repo,
                issue_tracker=issue_tracker,
                project_docs=project_docs,
            )
            SESSION.commit()
            flask.flash(message)
            return flask.redirect(flask.url_for(
                'view_repo', username=username, repo=repo.name))
        except progit.exceptions.ProgitException, err:
            flask.flash(str(err), 'error')
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')
    elif flask.request.method == 'GET':
        form = progit.forms.ProjectSettingsForm(project=repo)

    return flask.render_template(
        'settings.html',
        select='settings',
        username=username,
        repo=repo,
        form=form,
        tag_form=tag_form,
        tags=tags,
        plugins=plugins,
    )


@APP.route('/<repo>/updatedesc', methods=['POST'])
@APP.route('/fork/<username>/<repo>/updatedesc', methods=['POST'])
@cla_required
def update_description(repo, username=None):
    """ Update the description of a project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    form = progit.forms.DescriptionForm()

    if form.validate_on_submit():
        try:
            repo.description = form.description.data
            SESSION.add(repo)
            SESSION.commit()
            flask.flash('Description updated')
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_settings', username=username, repo=repo.name))


@APP.route('/<repo>/delete', methods=['POST'])
@APP.route('/fork/<username>/<repo>/delete', methods=['POST'])
@cla_required
def delete_repo(repo, username=None):
    """ Delete the present project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    SESSION.delete(repo)

    repopath = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        repopath = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    docpath = os.path.join(APP.config['DOCS_FOLDER'], repo.path)
    ticketpath = os.path.join(APP.config['TICKETS_FOLDER'], repo.path)

    try:
        shutil.rmtree(repopath)
        shutil.rmtree(docpath)
        shutil.rmtree(ticketpath)
        SESSION.commit()
    except (OSError, IOError), err:
        APP.logger.exception(err)
        flask.flash('Could not delete the project from the system', 'error')
    except SQLAlchemyError, err:  # pragma: no cover
        SESSION.rollback()
        APP.logger.exception(err)
        flask.flash('Could not delete the project', 'error')

    return flask.redirect(
        flask.url_for('view_user', username=flask.g.fas_user.username))


@APP.route('/<repo>/dropuser/<userid>', methods=['POST'])
@APP.route('/fork/<username>/<repo>/dropuser/<userid>', methods=['POST'])
@cla_required
def remove_user(repo, userid, username=None):
    """ Remove the specified user from the project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the users for this project')

    userids = [str(user.user.id) for user in repo.users]

    if str(userid) not in userids:
        flask.flash(
            'User does not have commit or cannot loose it right', 'error')
        return flask.redirect(
            flask.url_for(
                '.view_settings', repo=repo.name, username=username)
        )

    for user in repo.users:
        if str(user.user.id) == str(userid):
            SESSION.delete(user)
            break
    try:
        SESSION.commit()
        progit.generate_gitolite_acls()
        flask.flash('User removed')
    except SQLAlchemyError as err:
        SESSION.rollback()
        APP.logger.exception(err)
        flask.flash('User could not be removed', 'error')

    return flask.redirect(
        flask.url_for('.view_settings', repo=repo.name, username=username)
    )


@APP.route('/<repo>/adduser', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/adduser', methods=('GET', 'POST'))
@cla_required
def add_user(repo, username=None):
    """ Add the specified user from the project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to add users to this project')

    form = progit.forms.AddUserForm()

    if form.validate_on_submit():
        try:
            msg = progit.lib.add_user_to_project(
                SESSION, repo, form.user.data)
            SESSION.commit()
            progit.generate_gitolite_acls()
            flask.flash(msg)
            return flask.redirect(
                flask.url_for(
                    '.view_settings', repo=repo.name, username=username)
            )
        except progit.exceptions.ProgitException as msg:
            SESSION.rollback()
            flask.flash(msg, 'error')
        except SQLAlchemyError as err:
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash('User could not be added', 'error')

    return flask.render_template(
        'add_user.html',
        form=form,
        username=username,
        repo=repo,
    )
