# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import datetime
import shutil
import os
from math import ceil

import flask
import pygit2
import kitchen.text.converters as ktc
import werkzeug

from cStringIO import StringIO
from PIL import Image
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import guess_lexer_for_filename
from pygments.lexers.special import TextLexer
from pygments.util import ClassNotFound
from sqlalchemy.exc import SQLAlchemyError

import mimetypes
import chardet

from binaryornot.helpers import is_binary_string

import pagure.exceptions
import pagure.lib
import pagure.lib.git
import pagure.forms
import pagure
import pagure.ui.plugins
from pagure import (APP, SESSION, LOG, __get_file_in_tree, login_required,
                    is_repo_admin, admin_session_timedout)


# pylint: disable=E1101


@APP.route('/<repo:repo>/')
@APP.route('/<repo:repo>')
@APP.route('/fork/<username>/<repo:repo>/')
@APP.route('/fork/<username>/<repo:repo>')
def view_repo(repo, username=None):
    """ Front page of a specific repo.
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    reponame = pagure.get_repo_path(repo)

    repo_obj = pygit2.Repository(reponame)

    if not repo_obj.is_empty and not repo_obj.head_is_unborn:
        head = repo_obj.head.shorthand
    else:
        head = None

    cnt = 0
    last_commits = []
    tree = []
    if not repo_obj.is_empty:
        try:
            for commit in repo_obj.walk(
                    repo_obj.head.target, pygit2.GIT_SORT_TIME):
                last_commits.append(commit)
                cnt += 1
                if cnt == 3:
                    break
            tree = sorted(last_commits[0].tree, key=lambda x: x.filemode)
        except pygit2.GitError:
            pass

    readme = None
    safe = False

    if not repo_obj.is_empty and not repo_obj.head_is_unborn:
        branchname = repo_obj.head.shorthand
    else:
        branchname = None
    for i in tree:
        name, ext = os.path.splitext(i.name)
        if name == 'README':
            content = __get_file_in_tree(
                repo_obj, last_commits[0].tree, [i.name]).data

            readme, safe = pagure.doc_utils.convert_readme(
                content, ext,
                view_file_url=flask.url_for(
                    'view_raw_file', username=username,
                    repo=repo.name, identifier=branchname, filename=''))

    diff_commits = []
    if repo.is_fork:
        parentname = os.path.join(
            APP.config['GIT_FOLDER'], repo.parent.path)
        if repo.parent.is_fork:
            parentname = os.path.join(
                APP.config['FORK_FOLDER'], repo.parent.path)
    else:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo.path)

    orig_repo = pygit2.Repository(parentname)

    if not repo_obj.is_empty and not orig_repo.is_empty:

        orig_branch = orig_repo.lookup_branch('master')
        branch = repo_obj.lookup_branch('master')
        if orig_branch and branch:

            master_commits = [
                commit.oid.hex
                for commit in orig_repo.walk(
                    orig_branch.get_object().hex,
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
        repo_obj=repo_obj,
        username=username,
        head=head,
        readme=readme,
        safe=safe,
        origin='view_repo',
        branches=sorted(repo_obj.listall_branches()),
        branchname=branchname,
        last_commits=last_commits,
        tree=tree,
        diff_commits=diff_commits,
        repo_admin=is_repo_admin(repo),
        form=pagure.forms.ConfirmationForm(),
    )


@APP.route('/<repo:repo>/branch/<path:branchname>')
@APP.route('/fork/<username>/<repo:repo>/branch/<path:branchname>')
def view_repo_branch(repo, branchname, username=None):
    ''' Returns the list of branches in the repo. '''

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = pagure.get_repo_path(repo)

    repo_obj = pygit2.Repository(reponame)

    if branchname not in repo_obj.listall_branches():
        flask.abort(404, 'Branch no found')

    branch = repo_obj.lookup_branch(branchname)
    if not repo_obj.is_empty and not repo_obj.head_is_unborn:
        head = repo_obj.head.shorthand
    else:
        head = None
    cnt = 0
    last_commits = []
    for commit in repo_obj.walk(branch.get_object().hex, pygit2.GIT_SORT_TIME):
        last_commits.append(commit)
        cnt += 1
        if cnt == 3:
            break

    diff_commits = []
    if repo.is_fork:
        parentname = os.path.join(
            APP.config['GIT_FOLDER'], repo.parent.path)
        if repo.parent.is_fork:
            parentname = os.path.join(
                APP.config['FORK_FOLDER'], repo.parent.path)
    else:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo.path)

    orig_repo = pygit2.Repository(parentname)

    tree = None
    safe=False
    readme = None
    if not repo_obj.is_empty and not orig_repo.is_empty:

        if not orig_repo.head_is_unborn:
            compare_branch = orig_repo.lookup_branch(orig_repo.head.shorthand)
        else:
            compare_branch = None

        compare_commits = []

        if compare_branch:
            compare_commits = [
                commit.oid.hex
                for commit in orig_repo.walk(
                    compare_branch.get_object().hex,
                    pygit2.GIT_SORT_TIME)
            ]

        repo_commit = repo_obj[branch.get_object().hex]

        for commit in repo_obj.walk(
                repo_commit.oid.hex, pygit2.GIT_SORT_TIME):
            if commit.oid.hex in compare_commits:
                break
            diff_commits.append(commit.oid.hex)

        tree=sorted(last_commits[0].tree, key=lambda x: x.filemode)
        for i in tree:
            name, ext = os.path.splitext(i.name)
            if name == 'README':
                content = __get_file_in_tree(
                    repo_obj, last_commits[0].tree, [i.name]).data

                readme, safe = pagure.doc_utils.convert_readme(
                    content, ext,
                    view_file_url=flask.url_for(
                        'view_raw_file', username=username,
                        repo=repo.name, identifier=branchname, filename=''))

    return flask.render_template(
        'repo_info.html',
        select='overview',
        repo=repo,
        head=head,
        username=username,
        branches=sorted(repo_obj.listall_branches()),
        branchname=branchname,
        origin='view_repo_branch',
        last_commits=last_commits,
        tree=tree,
        safe=safe,
        readme=readme,
        diff_commits=diff_commits,
        repo_admin=is_repo_admin(repo),
        form=pagure.forms.ConfirmationForm(),
    )


@APP.route('/<repo:repo>/commits/')
@APP.route('/<repo:repo>/commits')
@APP.route('/<repo:repo>/commits/<path:branchname>')
@APP.route('/fork/<username>/<repo:repo>/commits/')
@APP.route('/fork/<username>/<repo:repo>/commits')
@APP.route('/fork/<username>/<repo:repo>/commits/<path:branchname>')
def view_commits(repo, branchname=None, username=None):
    """ Displays the commits of the specified repo.
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = pagure.get_repo_path(repo)

    repo_obj = pygit2.Repository(reponame)

    if branchname and branchname not in repo_obj.listall_branches():
        flask.abort(404, 'Branch no found')

    if branchname:
        branch = repo_obj.lookup_branch(branchname)
    elif not repo_obj.is_empty and not repo_obj.head_is_unborn:
        branch = repo_obj.lookup_branch(repo_obj.head.shorthand)
        branchname = branch.branch_name
    else:
        branch = None

    if not repo_obj.is_empty and not repo_obj.head_is_unborn:
        head = repo_obj.head.shorthand
    else:
        head = None

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
    diff_commits_full = []
    if repo.is_fork:
        parentname = os.path.join(
            APP.config['GIT_FOLDER'], repo.parent.path)
        if repo.parent.is_fork:
            parentname = os.path.join(
                APP.config['FORK_FOLDER'], repo.parent.path)
    else:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo.path)

    orig_repo = pygit2.Repository(parentname)

    if not repo_obj.is_empty and not orig_repo.is_empty \
            and repo_obj.listall_branches() > 1:

        if not orig_repo.head_is_unborn:
            compare_branch = orig_repo.lookup_branch(
                orig_repo.head.shorthand)
        else:
            compare_branch = None

        compare_commits = []

        if compare_branch:
            compare_commits = [
                commit.oid.hex
                for commit in orig_repo.walk(
                    compare_branch.get_object().hex,
                    pygit2.GIT_SORT_TIME)
            ]

        if branch:
            repo_commit = repo_obj[branch.get_object().hex]

            for commit in repo_obj.walk(
                    repo_commit.oid.hex, pygit2.GIT_SORT_TIME):
                if commit.oid.hex in compare_commits:
                    break
                diff_commits.append(commit.oid.hex)
                diff_commits_full.append(commit)

    return flask.render_template(
        'repo_info.html',
        select='logs',
        origin='view_commits',
        repo_obj=repo_obj,
        repo=repo,
        username=username,
        head=head,
        branches=sorted(repo_obj.listall_branches()),
        branchname=branchname,
        last_commits=last_commits,
        diff_commits=diff_commits,
        diff_commits_full=diff_commits_full,
        number_of_commits=n_commits,
        page=page,
        total_page=total_page,
        repo_admin=is_repo_admin(repo),
        form=pagure.forms.ConfirmationForm(),
    )


@APP.route('/<repo:repo>/blob/<path:identifier>/f/<path:filename>')
@APP.route('/fork/<username>/<repo:repo>/blob/<path:identifier>/f/<path:filename>')
def view_file(repo, identifier, filename, username=None):
    """ Displays the content of a file or a tree for the specified repo.
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = pagure.get_repo_path(repo)

    repo_obj = pygit2.Repository(reponame)

    if repo_obj.is_empty:
        flask.abort(404, 'Empty repo cannot have a file')

    if identifier in repo_obj.listall_branches():
        branchname = identifier
        branch = repo_obj.lookup_branch(identifier)
        commit = branch.get_object()
    else:
        try:
            commit = repo_obj.get(identifier)
            branchname = identifier
        except ValueError:
            if 'master' not in repo_obj.listall_branches():
                flask.abort(404, 'Branch no found')
            # If it's not a commit id then it's part of the filename
            commit = repo_obj[repo_obj.head.target]
            branchname = 'master'

    if isinstance(commit, pygit2.Tag):
        commit = commit.get_object()

    if commit and not isinstance(commit, pygit2.Blob):
        content = __get_file_in_tree(
            repo_obj, commit.tree, filename.split('/'), bail_on_tree=True)
        if not content:
            flask.abort(404, 'File not found')
        content = repo_obj[content.oid]
    else:
        content = commit

    if not content:
        flask.abort(404, 'File not found')

    if isinstance(content, pygit2.Blob):
        rawtext = str(flask.request.args.get('text')).lower() in ['1', 'true']
        ext = filename[filename.rfind('.'):]
        if ext in (
                '.gif', '.png', '.bmp', '.tif', '.tiff', '.jpg',
                '.jpeg', '.ppm', '.pnm', '.pbm', '.pgm', '.webp', '.ico'):
            try:
                Image.open(StringIO(content.data))
                output_type = 'image'
            except IOError as err:
                LOG.debug(
                    'Failed to load image %s, error: %s', filename, err
                )
                output_type = 'binary'
        elif ext in ('.rst', '.mk', '.md', '.markdown') and not rawtext:
            content, safe = pagure.doc_utils.convert_readme(content.data, ext)
            output_type = 'markup'
        elif not is_binary_string(content.data):
            file_content = content.data
            if not isinstance(file_content, basestring):
                file_content = content.data.decode('utf-8')
            try:
                lexer = guess_lexer_for_filename(
                    filename,
                    file_content
                )
            except (ClassNotFound, TypeError):
                lexer = TextLexer()

            content = highlight(
                file_content,
                lexer,
                HtmlFormatter(
                    noclasses=True,
                    style="tango",)
            )
            output_type = 'file'
        else:
            output_type = 'binary'
    else:
        content = sorted(content, key=lambda x: x.filemode)
        output_type = 'tree'

    return flask.render_template(
        'file.html',
        select='tree',
        repo=repo,
        origin='view_file',
        username=username,
        branches=sorted(repo_obj.listall_branches()),
        branchname=branchname,
        filename=filename,
        content=content,
        output_type=output_type,
        repo_admin=is_repo_admin(repo),
    )


@APP.route('/<repo:repo>/raw/<path:identifier>', defaults={'filename': None})
@APP.route('/<repo:repo>/raw/<path:identifier>/f/<path:filename>')
@APP.route('/fork/<username>/<repo:repo>/raw/<path:identifier>',
           defaults={'filename': None})
@APP.route('/fork/<username>/<repo>/raw/<path:identifier>/f/<path:filename>')
def view_raw_file(repo, identifier, filename=None, username=None):
    """ Displays the raw content of a file of a commit for the specified repo.
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = pagure.get_repo_path(repo)

    repo_obj = pygit2.Repository(reponame)

    if repo_obj.is_empty:
        flask.abort(404, 'Empty repo cannot have a file')

    if identifier in repo_obj.listall_branches():
        branch = repo_obj.lookup_branch(identifier)
        commit = branch.get_object()
    else:
        try:
            commit = repo_obj.get(identifier)
        except ValueError:
            if 'master' not in repo_obj.listall_branches():
                flask.abort(404, 'Branch no found')
            # If it's not a commit id then it's part of the filename
            commit = repo_obj[repo_obj.head.target]

    if not commit:
        flask.abort(400, 'Commit %s not found' % (identifier))

    if isinstance(commit, pygit2.Tag):
        commit = commit.get_object()

    mimetype = None
    encoding = None
    if filename:
        content = __get_file_in_tree(
            repo_obj, commit.tree, filename.split('/'), bail_on_tree=True)
        if not content or isinstance(content, pygit2.Tree):
            flask.abort(404, 'File not found')

        mimetype, encoding = mimetypes.guess_type(filename)
        data = repo_obj[content.oid].data
    else:
        if commit.parents:
            diff = commit.tree.diff_to_tree()

            try:
                parent = repo_obj.revparse_single('%s^' % identifier)
                diff = repo_obj.diff(parent, commit)
            except (KeyError, ValueError):
                flask.abort(404, 'Identifier not found')
        else:
            # First commit in the repo
            diff = commit.tree.diff_to_tree(swap=True)
        data = diff.patch

    if not data:
        flask.abort(404, 'No content found')

    if not mimetype and data[:2] == '#!':
        mimetype = 'text/plain'

    if not mimetype:
        if '\0' in data:
            mimetype = 'application/octet-stream'
        else:
            mimetype = 'text/plain'

    if mimetype.startswith('text/') and not encoding:
        encoding = chardet.detect(ktc.to_bytes(data))['encoding']

    headers = {'Content-Type': mimetype}
    if encoding:
        headers['Content-Encoding'] = encoding

    return (data, 200, headers)


#@APP.route('/<repo>/<commitid>/')
#@APP.route('/<repo>/<commitid>')
#@APP.route('/fork/<username>/<repo>/<commitid>/')
#@APP.route('/fork/<username>/<repo>/<commitid>')
#def view_commit_old(repo, commitid, username=None):
    #""" Render a commit in a repo
    #"""
    #print repo, commitid, username
    #tmp = '%s/%s' % (repo, commitid)
    #if not pagure.lib.get_project(SESSION, tmp, user=username):
        #return flask.redirect(flask.url_for(
            #'view_commit', repo=repo, commitid=commitid, username=username))
    #else:
        #return view_repo(tmp, username=username)


@APP.route('/<repo:repo>/c/<commitid>/')
@APP.route('/<repo:repo>/c/<commitid>')
@APP.route('/fork/<username>/<repo>/c/<commitid>/')
@APP.route('/fork/<username>/<repo>/c/<commitid>')
def view_commit(repo, commitid, username=None):
    """ Render a commit in a repo
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = pagure.get_repo_path(repo)

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
        repo_admin=is_repo_admin(repo),
        commitid=commitid,
        commit=commit,
        diff=diff,
    )


@APP.route('/<repo:repo>/c/<commitid>.patch')
@APP.route('/fork/<username>/<repo:repo>/c/<commitid>.patch')
def view_commit_patch(repo, commitid, username=None):
    """ Render a commit in a repo as patch
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = pagure.get_repo_path(repo)

    repo_obj = pygit2.Repository(reponame)

    try:
        commit = repo_obj.get(commitid)
    except ValueError:
        flask.abort(404, 'Commit not found')

    if commit is None:
        flask.abort(404, 'Commit not found')

    patch = pagure.lib.git.commit_to_patch(repo_obj, commit)

    return flask.Response(patch, content_type="text/plain;charset=UTF-8")


@APP.route('/<repo:repo>/tree/')
@APP.route('/<repo:repo>/tree')
@APP.route('/<repo:repo>/tree/<path:identifier>')
@APP.route('/fork/<username>/<repo:repo>/tree/')
@APP.route('/fork/<username>/<repo:repo>/tree')
@APP.route('/fork/<username>/<repo:repo>/tree/<path:identifier>')
def view_tree(repo, identifier=None, username=None):
    """ Render the tree of the repo
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    reponame = pagure.get_repo_path(repo)

    repo_obj = pygit2.Repository(reponame)

    branchname = None
    content = None
    output_type = None
    commit = None
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
                if 'master' in repo_obj.listall_branches():
                    commit = repo_obj[repo_obj.head.target]
                    branchname = 'master'
        # If we're arriving here from the release page, we may have a Tag
        # where we expected a commit, in this case, get the actual commit
        if isinstance(commit, pygit2.Tag):
            commit = commit.get_object()

        if commit:
            content = sorted(commit.tree, key=lambda x: x.filemode)
        output_type = 'tree'

    return flask.render_template(
        'file.html',
        select='tree',
        repo_obj=repo_obj,
        origin='view_tree',
        repo=repo,
        username=username,
        branchname=branchname,
        branches=sorted(repo_obj.listall_branches()),
        filename='',
        content=content,
        output_type=output_type,
        repo_admin=is_repo_admin(repo),
    )


@APP.route('/<repo:repo>/forks/')
@APP.route('/<repo:repo>/forks')
@APP.route('/fork/<username>/<repo:repo>/forks/')
@APP.route('/fork/<username>/<repo:repo>/forks')
def view_forks(repo, username=None):
    """ Presents all the forks of the project.
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    return flask.render_template(
        'forks.html',
        select='forks',
        username=username,
        repo=repo,
        repo_admin=is_repo_admin(repo),
    )


@APP.route('/<repo:repo>/releases/')
@APP.route('/<repo:repo>/releases')
@APP.route('/fork/<username>/<repo:repo>/releases/')
@APP.route('/fork/<username>/<repo:repo>/releases')
def view_tags(repo, username=None):
    """ Presents all the tags of the project.
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    reponame = pagure.get_repo_path(repo)
    repo_obj = pygit2.Repository(reponame)

    tags = pagure.lib.git.get_git_tags_objects(repo)
    return flask.render_template(
        'releases.html',
        select='tags',
        username=username,
        repo=repo,
        tags=tags,
        repo_admin=is_repo_admin(repo),
        repo_obj=repo_obj,
    )


@APP.route('/<repo:repo>/upload/', methods=('GET', 'POST'))
@APP.route('/<repo:repo>/upload', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/upload/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/upload', methods=('GET', 'POST'))
@login_required
def new_release(repo, username=None):
    """ Upload a new release.
    """
    if not APP.config.get('UPLOAD_FOLDER_PATH') \
            and not APP.config.get('UPLOAD_FOLDER'):
        flask.abort(404)

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    form = pagure.forms.UploadFileForm()

    if form.validate_on_submit():
        for filestream in flask.request.files.getlist('filestream'):
            filename = werkzeug.secure_filename(filestream.filename)
            try:
                folder = os.path.join(
                    APP.config['UPLOAD_FOLDER_PATH'],
                    werkzeug.secure_filename(repo.fullname))
                if not os.path.exists(folder):
                    os.mkdir(folder)
                filestream.save(os.path.join(folder, filename))
                flask.flash('File "%s" uploaded' % filename)
            except Exception as err:  # pragma: no cover
                APP.logger.exception(err)
                flask.flash('Upload failed', 'error')
        return flask.redirect(
            flask.url_for('view_tags', repo=repo.name, username=username))

    return flask.render_template(
        'new_release.html',
        select='tags',
        username=username,
        repo=repo,
        form=form,
    )


@APP.route('/<repo:repo>/settings/', methods=('GET', 'POST'))
@APP.route('/<repo:repo>/settings', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/settings/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/settings', methods=('GET', 'POST'))
@login_required
def view_settings(repo, username=None):
    """ Presents the settings of the project.
    """
    if admin_session_timedout():
        if flask.request.method == 'POST':
            flask.flash('Action canceled, try it again', 'error')
        return flask.redirect(
            flask.url_for('auth_login', next=flask.request.url))

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    repo_admin = is_repo_admin(repo)
    if not repo_admin:
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    reponame = pagure.get_repo_path(repo)
    repo_obj = pygit2.Repository(reponame)

    plugins = pagure.ui.plugins.get_plugin_names(
        APP.config.get('DISABLED_PLUGINS'))
    tags = pagure.lib.get_tags_of_project(SESSION, repo)

    form = pagure.forms.ConfirmationForm()
    tag_form = pagure.forms.AddIssueTagForm()

    branches = repo_obj.listall_branches()
    branches_form = pagure.forms.DefaultBranchForm(branches=branches)
    if form.validate_on_submit():
        settings = {}
        for key in flask.request.form:
            if key == 'csrf_token':
                continue
            settings[key] = flask.request.form[key]

        try:
            message = pagure.lib.update_project_settings(
                SESSION,
                repo=repo,
                settings=settings,
                user=flask.g.fas_user.username,
            )
            SESSION.commit()
            flask.flash(message)
            return flask.redirect(flask.url_for(
                'view_repo', username=username, repo=repo.name))
        except pagure.exceptions.PagureException as msg:
            SESSION.rollback()
            flask.flash(msg, 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')

    if not repo_obj.is_empty and not repo_obj.head_is_unborn:
        branchname = repo_obj.head.shorthand
    else:
        branchname = None

    if flask.request.method == 'GET' and branchname:
        branches_form.branches.data = branchname

    return flask.render_template(
        'settings.html',
        select='settings',
        username=username,
        repo=repo,
        repo_obj=repo_obj,
        form=form,
        tag_form=tag_form,
        branches_form=branches_form,
        tags=tags,
        plugins=plugins,
        repo_admin=repo_admin,
        branchname = branchname,
    )


@APP.route('/<repo:repo>/update', methods=['POST'])
@APP.route('/fork/<username>/<repo:repo>/update', methods=['POST'])
@login_required
def update_project(repo, username=None):
    """ Update the description of a project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    form = pagure.forms.ProjectFormSimplified()

    if form.validate_on_submit():
        try:
            repo.description = form.description.data
            repo.avatar_email = form.avatar_email.data.strip()
            repo.url = form.url.data.strip()
            pagure.lib.update_tags(
                SESSION, repo,
                tags=[t.strip() for t in form.tags.data.split(',')],
                username=flask.g.fas_user.username,
                ticketfolder=None,
            )
            SESSION.add(repo)
            SESSION.commit()
            flask.flash('Project updated')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_settings', username=username, repo=repo.name))


@APP.route('/<repo>/update/priorities', methods=['POST'])
@APP.route('/fork/<username>/<repo>/update/priorities', methods=['POST'])
@login_required
def update_priorities(repo, username=None):
    """ Update the priorities of a project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    form = pagure.forms.ConfirmationForm()

    error = False
    if form.validate_on_submit():
        weights = [
            w.strip() for w in flask.request.form.getlist('priority_weigth')
            if w.strip()
        ]
        try:
            weights = [int(w) for w in weights]
        except:
            flask.flash(
                'Priorities weights must be numbers',
                'error')
            error = True

        titles = [
            p.strip() for p in flask.request.form.getlist('priority_title')
            if p.strip()
        ]

        if len(weights) != len(titles):
            flask.flash(
                'Priorities weights and titles are not of the same length',
                'error')
            error = True

        for weight in weights:
            if weights.count(weight) != 1:
                flask.flash(
                    'Priority weight %s is present %s times' % (
                        weight, weights.count(weight)
                    ),
                    'error')
                error = True
                break

        for title in titles:
            if titles.count(title) != 1:
                flask.flash(
                    'Priority %s is present %s times' % (
                        title, titles.count(title)
                    ),
                    'error')
                error = True
                break

        if not error:
            priorities = {}
            for cnt in range(len(weights)):
                priorities[weights[cnt]] = titles[cnt]
            try:
                repo.priorities = priorities
                SESSION.add(repo)
                SESSION.commit()
                flask.flash('Priorities updated')
            except SQLAlchemyError as err:  # pragma: no cover
                SESSION.rollback()
                flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_settings', username=username, repo=repo.name))


@APP.route('/<repo:repo>/default/branch/', methods=['POST'])
@APP.route('/fork/<username>/<repo:repo>/default/branch/', methods=['POST'])
@login_required
def change_ref_head(repo, username=None):
    """ Change HEAD reference
    """

    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = pagure.lib.get_project(SESSION, repo, user=username)
    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')
    repopath = pagure.get_repo_path(repo)
    repo_obj = pygit2.Repository(repopath)
    branches = repo_obj.listall_branches()
    form = pagure.forms.DefaultBranchForm(branches=branches)

    if form.validate_on_submit():
        branchname = form.branches.data
        try:
            reference = repo_obj.lookup_reference('refs/heads/%s'%branchname).resolve()
            repo_obj.set_head(reference.name)
            flask.flash('Default branch updated to %s'%branchname)
        except Exception as err:  # pragma: no cover
            APP.logger.exception(err)

    return flask.redirect(flask.url_for(
                'view_settings', username=username, repo=repo.name))


@APP.route('/<repo:repo>/delete', methods=['POST'])
@APP.route('/fork/<username>/<repo:repo>/delete', methods=['POST'])
@login_required
def delete_repo(repo, username=None):
    """ Delete the present project.
    """
    if not pagure.APP.config.get('ENABLE_DEL_PROJECTS', True):
        flask.abort(404)

    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    try:
        for issue in repo.issues:
            for comment in issue.comments:
                SESSION.delete(comment)
            SESSION.commit()
            SESSION.delete(issue)
        SESSION.delete(repo)
        SESSION.commit()
    except SQLAlchemyError as err:  # pragma: no cover
        SESSION.rollback()
        APP.logger.exception(err)
        flask.flash('Could not delete the project', 'error')

    repopath = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        repopath = os.path.join(APP.config['FORK_FOLDER'], repo.path)
    docpath = os.path.join(APP.config['DOCS_FOLDER'], repo.path)
    ticketpath = os.path.join(APP.config['TICKETS_FOLDER'], repo.path)
    requestpath = os.path.join(APP.config['REQUESTS_FOLDER'], repo.path)

    try:
        shutil.rmtree(repopath)
        shutil.rmtree(docpath)
        shutil.rmtree(ticketpath)
        shutil.rmtree(requestpath)
    except (OSError, IOError) as err:
        APP.logger.exception(err)
        flask.flash(
            'Could not delete all the repos from the system', 'error')

    return flask.redirect(
        flask.url_for('view_user', username=flask.g.fas_user.username))


@APP.route('/<repo:repo>/hook_token', methods=['POST'])
@APP.route('/fork/<username>/<repo:repo>/hook_token', methods=['POST'])
@login_required
def new_repo_hook_token(repo, username=None):
    """ Re-generate a hook token for the present project.
    """
    if not pagure.APP.config.get('WEBHOOK', False):
        flask.abort(404)

    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.abort(400, 'Invalid request')

    try:
        repo.hook_token = pagure.lib.login.id_generator(40)
        SESSION.commit()
        flask.flash('New hook token generated')
    except SQLAlchemyError as err:  # pragma: no cover
        SESSION.rollback()
        APP.logger.exception(err)
        flask.flash('Could not generate a new token for this project', 'error')

    return flask.redirect(
        flask.url_for('view_settings', repo=repo.name, username=username))


@APP.route('/<repo:repo>/dropuser/<userid>', methods=['POST'])
@APP.route('/fork/<username>/<repo:repo>/dropuser/<userid>', methods=['POST'])
@login_required
def remove_user(repo, userid, username=None):
    """ Remove the specified user from the project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the users for this project')

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        userids = [str(user.id) for user in repo.users]

        if str(userid) not in userids:
            flask.flash(
                'User does not have commit or cannot loose it right', 'error')
            return flask.redirect(
                flask.url_for(
                    '.view_settings', repo=repo.name, username=username)
            )

        for user in repo.users:
            if str(user.id) == str(userid):
                repo.users.remove(user)
                break
        try:
            SESSION.commit()
            pagure.lib.git.generate_gitolite_acls()
            flask.flash('User removed')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash('User could not be removed', 'error')

    return flask.redirect(
        flask.url_for('.view_settings', repo=repo.name, username=username)
    )


@APP.route('/<repo:repo>/adduser/', methods=('GET', 'POST'))
@APP.route('/<repo:repo>/adduser', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/adduser/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/adduser', methods=('GET', 'POST'))
@login_required
def add_user(repo, username=None):
    """ Add the specified user from the project.
    """
    if not pagure.APP.config.get('ENABLE_USER_MNGT', True):
        flask.abort(404)

    if admin_session_timedout():
        if flask.request.method == 'POST':
            flask.flash('Action canceled, try it again', 'error')
        return flask.redirect(
            flask.url_for('auth_login', next=flask.request.url))

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to add users to this project')

    form = pagure.forms.AddUserForm()

    if form.validate_on_submit():
        try:
            msg = pagure.lib.add_user_to_project(
                SESSION, repo,
                new_user=form.user.data,
                user=flask.g.fas_user.username,
            )
            SESSION.commit()
            pagure.lib.git.generate_gitolite_acls()
            flask.flash(msg)
            return flask.redirect(
                flask.url_for(
                    '.view_settings', repo=repo.name, username=username)
            )
        except pagure.exceptions.PagureException as msg:
            SESSION.rollback()
            flask.flash(msg, 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash('User could not be added', 'error')

    return flask.render_template(
        'add_user.html',
        form=form,
        username=username,
        repo=repo,
    )


@APP.route('/<repo:repo>/addgroup/', methods=('GET', 'POST'))
@APP.route('/<repo:repo>/addgroup', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/addgroup/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/addgroup', methods=('GET', 'POST'))
@login_required
def add_group_project(repo, username=None):
    """ Add the specified group from the project.
    """
    if not pagure.APP.config.get('ENABLE_USER_MNGT', True):
        flask.abort(404)

    if admin_session_timedout():
        if flask.request.method == 'POST':
            flask.flash('Action canceled, try it again', 'error')
        return flask.redirect(
            flask.url_for('auth_login', next=flask.request.url))

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to add groups to this project')

    form = pagure.forms.AddGroupForm()

    if form.validate_on_submit():
        try:
            msg = pagure.lib.add_group_to_project(
                SESSION, repo,
                new_group=form.group.data,
                user=flask.g.fas_user.username,
            )
            SESSION.commit()
            pagure.lib.git.generate_gitolite_acls()
            flask.flash(msg)
            return flask.redirect(
                flask.url_for(
                    '.view_settings', repo=repo.name, username=username)
            )
        except pagure.exceptions.PagureException as msg:
            SESSION.rollback()
            flask.flash(msg, 'error')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash('Group could not be added', 'error')

    return flask.render_template(
        'add_group_project.html',
        form=form,
        username=username,
        repo=repo,
    )


@APP.route('/<repo:repo>/regenerate', methods=['POST'])
@APP.route('/fork/<username>/<repo:repo>/regenerate', methods=['POST'])
@login_required
def regenerate_git(repo, username=None):
    """ Regenerate the specified git repo with the content in the project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(403, 'You are not allowed to regenerate the git repos')

    regenerate = flask.request.form.get('regenerate')
    if not regenerate or regenerate.lower() not in ['tickets', 'requests']:
        flask.abort(400, 'You can only regenerate tickest or requests repos')

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        if regenerate.lower() == 'requests':
            for request in repo.requests:
                pagure.lib.git.update_git(
                    request, repo=repo,
                    repofolder=APP.config['REQUESTS_FOLDER'])
            flask.flash('Requests git repo updated')
        elif regenerate.lower() == 'tickets':
            for ticket in repo.issues:
                # Do not store private issues in the git
                if ticket.private:
                    continue
                pagure.lib.git.update_git(
                    ticket, repo=repo,
                    repofolder=APP.config['TICKETS_FOLDER'])
            flask.flash('Tickets git repo updated')

    return flask.redirect(
        flask.url_for('.view_settings', repo=repo.name, username=username)
    )


@APP.route('/<repo:repo>/token/new/', methods=('GET', 'POST'))
@APP.route('/<repo:repo>/token/new', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/token/new/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo:repo>/token/new', methods=('GET', 'POST'))
@login_required
def add_token(repo, username=None):
    """ Add a token to a specified project.
    """
    if admin_session_timedout():
        if flask.request.method == 'POST':
            flask.flash('Action canceled, try it again', 'error')
        return flask.redirect(
            flask.url_for('auth_login', next=flask.request.url))

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    repo_admin = is_repo_admin(repo)
    if not repo_admin:
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    acls = pagure.lib.get_acls(SESSION)
    form = pagure.forms.NewTokenForm(acls=acls)

    if form.validate_on_submit():
        try:
            msg = pagure.lib.add_token_to_user(
                SESSION,
                repo,
                acls=form.acls.data,
                username=flask.g.fas_user.username,
            )
            SESSION.commit()
            flask.flash(msg)
            return flask.redirect(
                flask.url_for(
                    '.view_settings', repo=repo.name, username=username)
            )
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash('User could not be added', 'error')

    return flask.render_template(
        'add_token.html',
        select='settings',
        form=form,
        acls=acls,
        repo_admin=repo_admin,
        username=username,
        repo=repo,
    )


@APP.route('/<repo:repo>/token/revoke/<token_id>', methods=['POST'])
@APP.route('/fork/<username>/<repo:repo>/token/revoke/<token_id>',
           methods=['POST'])
@login_required
def revoke_api_token(repo, token_id, username=None):
    """ Revokie a token to a specified project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    token = pagure.lib.get_api_token(SESSION, token_id)

    if not token \
            or token.project.fullname != repo.fullname \
            or token.user.username != flask.g.fas_user.username:
        flask.abort(404, 'Token not found')

    form = pagure.forms.ConfirmationForm()

    if form.validate_on_submit():
        try:
            token.expiration = datetime.datetime.utcnow()
            SESSION.commit()
            flask.flash('Token revoked')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash(
                'Token could not be revoked, please contact an admin',
                'error')

    return flask.redirect(
        flask.url_for(
            '.view_settings', repo=repo.name, username=username)
    )


@APP.route(
    '/<repo:repo>/edit/<path:branchname>/f/<path:filename>',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<repo:repo>/edit/<path:branchname>/f/<path:filename>',
    methods=('GET', 'POST'))
@login_required
def edit_file(repo, branchname, filename, username=None):
    """ Edit a file online.
    """
    repo = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo):
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    user = pagure.lib.search_user(
        SESSION, username=flask.g.fas_user.username)

    reponame = pagure.get_repo_path(repo)

    repo_obj = pygit2.Repository(reponame)

    if repo_obj.is_empty:
        flask.abort(404, 'Empty repo cannot have a file')

    form = pagure.forms.EditFileForm(emails=user.emails)

    branch = None
    if branchname in repo_obj.listall_branches():
        branch = repo_obj.lookup_branch(branchname)
        commit = branch.get_object()
    else:
        flask.abort(400, 'Invalid branch specified')

    if form.validate_on_submit():
        try:
            pagure.lib.git.update_file_in_git(
                repo,
                branch=branchname,
                branchto=form.branch.data,
                filename=filename,
                content=form.content.data,
                message='%s\n\n%s' % (
                    form.commit_title.data.strip(),
                    form.commit_message.data.strip()
                ),
                user=flask.g.fas_user,
                email=form.email.data,
            )
            flask.flash('Changes committed')
            return flask.redirect(
                flask.url_for(
                    '.view_commits', repo=repo.name, username=username,
                    branchname=form.branch.data)
            )
        except pagure.exceptions.PagureException as err:  # pragma: no cover
            APP.logger.exception(err)
            flask.flash('Commit could not be done', 'error')
            data = form.content.data
    elif flask.request.method == 'GET':
        content = __get_file_in_tree(
            repo_obj, commit.tree, filename.split('/'))
        if not content or isinstance(content, pygit2.Tree):
            flask.abort(404, 'File not found')

        if is_binary_string(content.data):
            flask.abort(400, 'Cannot edit binary files')

        data = repo_obj[content.oid].data.decode('utf-8')
    else:
        data = form.content.data.decode('utf-8')

    return flask.render_template(
        'edit_file.html',
        select='tree',
        repo=repo,
        username=username,
        branchname=branchname,
        data=data,
        filename=filename,
        form=form,
        user=user,
        branches=repo_obj.listall_branches(),
    )


@APP.route('/<repo:repo>/b/<path:branchname>/delete', methods=['POST'])
@APP.route('/fork/<username>/<repo:repo>/b/<path:branchname>/delete',
           methods=['POST'])
@login_required
def delete_branch(repo, branchname, username=None):
    """ Delete the branch of a project.
    """
    repo_obj = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo_obj:
        flask.abort(404, 'Project not found')

    if not is_repo_admin(repo_obj):
        flask.abort(
            403,
            'You are not allowed to delete branch for this project')

    if branchname == 'master':
        flask.abort(403, 'You are not allowed to delete the master branch')

    reponame = pagure.get_repo_path(repo_obj)
    repo_git = pygit2.Repository(reponame)

    if branchname not in repo_git.listall_branches():
        flask.abort(404, 'Branch no found')

    try:
        branch = repo_git.lookup_branch(branchname)
        branch.delete()
        flask.flash('Branch `%s` deleted' % branchname)
    except pygit2.GitError as err:
        APP.logger.exception(err)
        flask.flash('Could not delete `%s`' % branchname, 'error')

    return flask.redirect(
        flask.url_for('view_repo', repo=repo, username=username))


@APP.route('/docs/<repo:repo>/')
@APP.route('/docs/<repo:repo>/<path:filename>')
@APP.route('/docs/fork/<username>/<repo:repo>/')
@APP.route('/docs/fork/<username>/<repo:repo>/<path:filename>')
def view_docs(repo, username=None, filename=None):
    """ Display the documentation
    """
    repo_obj = pagure.lib.get_project(SESSION, repo, user=username)

    if not repo_obj:
        flask.abort(404, 'Project not found')

    if not APP.config.get('DOC_APP_URL'):
        flask.abort(404, 'This pagure instance has no doc server')

    return flask.render_template(
        'docs.html',
        repo=repo_obj,
        username=username,
        filename=filename,
        endpoint='view_docs',
        select='docs',
    )

@APP.route('/<repo>/activity/')
@APP.route('/<repo>/activity')
def view_project_activity(repo):
    """ Display the activity feed
    """

    if not APP.config.get('DATAGREPPER_URL'):
        flask.abort(404)

    repo_obj = pagure.lib.get_project(SESSION, repo, user=None)

    if not repo_obj:
        flask.abort(404, 'Project not found')

    return flask.render_template(
        'activity.html',
        repo=repo_obj,
    )
