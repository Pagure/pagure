# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-branches
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# pylint: disable=bare-except
# pylint: disable=broad-except


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

from binaryornot.helpers import is_binary_string

import pagure.exceptions
import pagure.lib
import pagure.lib.git
import pagure.lib.plugins
import pagure.forms
import pagure
import pagure.ui.plugins
from pagure import (APP, SESSION, LOG, __get_file_in_tree, login_required,
                    admin_session_timedout)
from pagure.lib import encoding_utils


@APP.route('/<repo>.git')
@APP.route('/<namespace>/<repo>.git')
@APP.route('/fork/<username>/<repo>.git')
@APP.route('/fork/<username>/<namespace>/<repo>.git')
def view_repo_git(repo, username=None, namespace=None):
    ''' Redirect to the project index page when user wants to view
    the git repo of the project
    '''
    return flask.redirect(flask.url_for(
        'view_repo', repo=repo, username=username, namespace=namespace))


@APP.route('/<repo>/')
@APP.route('/<repo>')
@APP.route('/<namespace>/<repo>/')
@APP.route('/<namespace>/<repo>')
@APP.route('/fork/<username>/<repo>/')
@APP.route('/fork/<username>/<repo>')
@APP.route('/fork/<username>/<namespace>/<repo>/')
@APP.route('/fork/<username>/<namespace>/<repo>')
def view_repo(repo, username=None, namespace=None):
    """ Front page of a specific repo.
    """
    repo_db = flask.g.repo
    reponame = flask.g.reponame
    repo_obj = flask.g.repo_obj

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
                    repo=repo_db.name, identifier=branchname, filename=''))

    diff_commits = []
    if repo_db.is_fork and repo_db.parent:
        parentname = os.path.join(
            APP.config['GIT_FOLDER'], repo_db.parent.path)
    else:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo_db.path)

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
        repo=repo_db,
        username=username,
        head=head,
        readme=readme,
        safe=safe,
        origin='view_repo',
        branchname=branchname,
        last_commits=last_commits,
        tree=tree,
        diff_commits=diff_commits,
        form=pagure.forms.ConfirmationForm(),
    )


@APP.route('/<repo>/branch/<path:branchname>')
@APP.route('/<namespace>/<repo>/branch/<path:branchname>')
@APP.route('/fork/<username>/<repo>/branch/<path:branchname>')
@APP.route('/fork/<username>/<namespace>/<repo>/branch/<path:branchname>')
def view_repo_branch(repo, branchname, username=None, namespace=None):
    ''' Returns the list of branches in the repo. '''

    repo = flask.g.repo
    reponame = flask.g.reponame
    repo_obj = flask.g.repo_obj

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

    if repo.is_fork and repo.parent:
        parentname = os.path.join(
            APP.config['GIT_FOLDER'], repo.parent.path)
    else:
        parentname = os.path.join(APP.config['GIT_FOLDER'], repo.path)

    orig_repo = pygit2.Repository(parentname)

    tree = None
    safe = False
    readme = None
    if not repo_obj.is_empty and not orig_repo.is_empty:

        if not orig_repo.head_is_unborn:
            compare_branch = orig_repo.lookup_branch(orig_repo.head.shorthand)
        else:
            compare_branch = None

        commit_list = []

        if compare_branch:
            commit_list = [
                commit.oid.hex
                for commit in orig_repo.walk(
                    compare_branch.get_object().hex,
                    pygit2.GIT_SORT_TIME)
            ]

        repo_commit = repo_obj[branch.get_object().hex]

        for commit in repo_obj.walk(
                repo_commit.oid.hex, pygit2.GIT_SORT_TIME):
            if commit.oid.hex in commit_list:
                break
            diff_commits.append(commit.oid.hex)

        tree = sorted(last_commits[0].tree, key=lambda x: x.filemode)
        for i in tree:
            name, ext = os.path.splitext(i.name)
            if name == 'README':
                content = __get_file_in_tree(
                    repo_obj, last_commits[0].tree, [i.name]).data

                readme, safe = pagure.doc_utils.convert_readme(
                    content, ext,
                    view_file_url=flask.url_for(
                        'view_raw_file', username=username,
                        namespace=repo.namespace,
                        repo=repo.name, identifier=branchname, filename=''))

    return flask.render_template(
        'repo_info.html',
        select='overview',
        repo=repo,
        head=head,
        username=username,
        branchname=branchname,
        origin='view_repo_branch',
        last_commits=last_commits,
        tree=tree,
        safe=safe,
        readme=readme,
        diff_commits=diff_commits,
        form=pagure.forms.ConfirmationForm(),
    )


@APP.route('/<repo>/commits/')
@APP.route('/<repo>/commits')
@APP.route('/<repo>/commits/<path:branchname>')
@APP.route('/<namespace>/<repo>/commits/')
@APP.route('/<namespace>/<repo>/commits')
@APP.route('/<namespace>/<repo>/commits/<path:branchname>')
@APP.route('/fork/<username>/<repo>/commits/')
@APP.route('/fork/<username>/<repo>/commits')
@APP.route('/fork/<username>/<repo>/commits/<path:branchname>')
@APP.route('/fork/<username>/<namespace>/<repo>/commits/')
@APP.route('/fork/<username>/<namespace>/<repo>/commits')
@APP.route('/fork/<username>/<namespace>/<repo>/commits/<path:branchname>')
def view_commits(repo, branchname=None, username=None, namespace=None):
    """ Displays the commits of the specified repo.
    """
    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

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

    author = flask.request.args.get('author', None)
    author_obj = None
    if author:
        try:
            author_obj = pagure.lib.get_user(SESSION, author)
        except:
            pass
        if not author_obj:
            flask.flash(
                'No user found for the author: %s' % author, 'error')

    limit = APP.config['ITEM_PER_PAGE']
    start = limit * (page - 1)
    end = limit * page

    n_commits = 0
    last_commits = []
    if branch:
        for commit in repo_obj.walk(
                branch.get_object().hex, pygit2.GIT_SORT_TIME):

            # Filters the commits for an user
            filters = None
            if author_obj:
                filters = True
                tmp = False
                for email in author_obj.emails:
                    if email.email == commit.author.email:
                        tmp = True
                        break
                if not tmp:
                    continue

            if n_commits >= start and n_commits <= end:
                last_commits.append(commit)
            n_commits += 1

    total_page = int(ceil(n_commits / float(limit)) if n_commits > 0 else 1)

    diff_commits = []
    diff_commits_full = []
    if repo.is_fork and repo.parent:
        parentname = os.path.join(
            APP.config['GIT_FOLDER'], repo.parent.path)
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

        commit_list = []

        if compare_branch:
            commit_list = [
                commit.oid.hex
                for commit in orig_repo.walk(
                    compare_branch.get_object().hex,
                    pygit2.GIT_SORT_TIME)
            ]

        if head and branch:
            repo_commit = repo_obj[branch.get_object().hex]

            for commit in repo_obj.walk(
                    repo_commit.oid.hex, pygit2.GIT_SORT_TIME):
                if commit.oid.hex in commit_list:
                    break
                diff_commits.append(commit.oid.hex)
                diff_commits_full.append(commit)

    return flask.render_template(
        'commits.html',
        select='commits',
        origin='view_commits',
        repo=repo,
        username=username,
        head=head,
        branchname=branchname,
        last_commits=last_commits,
        diff_commits=diff_commits,
        diff_commits_full=diff_commits_full,
        number_of_commits=n_commits,
        page=page,
        total_page=total_page,
        form=pagure.forms.ConfirmationForm(),
    )


@APP.route('/<repo>/c/<commit1>..<commit2>/')
@APP.route('/<repo>/c/<commit1>..<commit2>')
@APP.route('/<namespace>/<repo>/c/<commit1>..<commit2>/')
@APP.route('/<namespace>/<repo>/c/<commit1>..<commit2>')
@APP.route('/fork/<username>/<repo>/c/<commit1>..<commit2>/')
@APP.route('/fork/<username>/<repo>/c/<commit1>..<commit2>')
@APP.route('/fork/<username>/<namespace>/<repo>/c/<commit1>..<commit2>/')
@APP.route('/fork/<username>/<namespace>/<repo>/c/<commit1>..<commit2>')
def compare_commits(repo, commit1, commit2, username=None, namespace=None):
    """ Compares two commits for specified repo
    """
    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

    if not repo_obj.is_empty and not repo_obj.head_is_unborn:
        head = repo_obj.head.shorthand
    else:
        head = None

    # Check commit1 and commit2 existence
    commit1_obj = repo_obj.get(commit1)
    commit2_obj = repo_obj.get(commit2)
    if commit1_obj is None:
        flask.abort(404, 'First commit does not exist')
    if commit2_obj is None:
        flask.abort(404, 'Last commit does not exist')

    # Get commits diff data
    diff = repo_obj.diff(commit1, commit2)

    # Get commits list
    diff_commits = []
    order = pygit2.GIT_SORT_TIME
    first_commit = commit1
    last_commit = commit2

    commits = [
        commit.oid.hex[:len(first_commit)]
        for commit in repo_obj.walk(last_commit, pygit2.GIT_SORT_TIME)
    ]

    if first_commit not in commits:
        first_commit = commit2
        last_commit = commit1

    for commit in repo_obj.walk(last_commit, order):
        diff_commits.append(commit)

        if commit.oid.hex == first_commit \
                or commit.oid.hex.startswith(first_commit):
            break

    if first_commit == commit2:
        diff_commits.reverse()

    return flask.render_template(
        'pull_request.html',
        select='logs',
        origin='compare_commits',
        repo=repo,
        username=username,
        head=head,
        commit1=commit1,
        commit2=commit2,
        diff=diff,
        diff_commits=diff_commits,
    )


@APP.route('/<repo>/blob/<path:identifier>/f/<path:filename>')
@APP.route('/<namespace>/<repo>/blob/<path:identifier>/f/<path:filename>')
@APP.route(
    '/fork/<username>/<repo>/blob/<path:identifier>/f/<path:filename>')
@APP.route(
    '/fork/<username>/<namespace>/<repo>/blob/<path:identifier>/f/<path:filename>')
def view_file(repo, identifier, filename, username=None, namespace=None):
    """ Displays the content of a file or a tree for the specified repo.
    """
    repo = flask.g.repo
    reponame = flask.g.reponame
    repo_obj = flask.g.repo_obj

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

    encoding = None
    readme = None
    safe = False
    readme_ext = None

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
            file_content = encoding_utils.decode(ktc.to_bytes(content.data))
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
        for i in content:
            name, ext = os.path.splitext(i.name)
            if name == 'README':
                readme_file = __get_file_in_tree(
                    repo_obj, content, [i.name]).data

                readme, safe = pagure.doc_utils.convert_readme(
                    readme_file, ext)

                readme_ext = ext
        output_type = 'tree'

    headers = {}

    return (
        flask.render_template(
            'file.html',
            select='tree',
            repo=repo,
            origin='view_file',
            username=username,
            branchname=branchname,
            filename=filename,
            content=content,
            output_type=output_type,
            readme=readme,
            readme_ext=readme_ext,
            safe=safe,
        ),
        200,
        headers
    )


@APP.route('/<repo>/raw/<path:identifier>',)
@APP.route('/<namespace>/<repo>/raw/<path:identifier>',)
@APP.route('/<repo>/raw/<path:identifier>/f/<path:filename>')
@APP.route('/<namespace>/<repo>/raw/<path:identifier>/f/<path:filename>')
@APP.route('/fork/<username>/<repo>/raw/<path:identifier>')
@APP.route('/fork/<username>/<namespace>/<repo>/raw/<path:identifier>')
@APP.route(
    '/fork/<username>/<repo>/raw/<path:identifier>/f/<path:filename>')
@APP.route(
    '/fork/<username>/<namespace>/<repo>/raw/<path:identifier>/f/<path:filename>')
def view_raw_file(
        repo, identifier, filename=None, username=None, namespace=None):
    """ Displays the raw content of a file of a commit for the specified repo.
    """
    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

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
        flask.abort(404, 'Commit %s not found' % (identifier))

    if isinstance(commit, pygit2.Tag):
        commit = commit.get_object()

    mimetype = None
    encoding = None
    if filename:
        if isinstance(commit, pygit2.Blob):
            content = commit
        else:
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

    headers = {}
    if not mimetype:
        if '\0' in data:
            mimetype = 'application/octet-stream'
        else:
            mimetype = 'text/plain'
    elif 'html' in mimetype:
        mimetype = 'application/octet-stream'
        headers['Content-Disposition'] = 'attachment'

    if mimetype.startswith('text/') and not encoding:
        encoding = encoding_utils.guess_encoding(ktc.to_bytes(data))

    if encoding:
        mimetype += '; charset={encoding}'.format(encoding=encoding)
    headers['Content-Type'] = mimetype

    return (data, 200, headers)


@APP.route('/<repo>/blame/<path:filename>')
@APP.route('/<namespace>/<repo>/blame/<path:filename>')
@APP.route(
    '/fork/<username>/<repo>/blame/<path:filename>')
@APP.route(
    '/fork/<username>/<namespace>/<repo>/blame/<path:filename>')
def view_blame_file(repo, filename, username=None, namespace=None):
    """ Displays the blame of a file or a tree for the specified repo.
    """
    repo = flask.g.repo
    reponame = flask.g.reponame
    repo_obj = flask.g.repo_obj

    branchname = flask.request.args.get('identifier', 'master')

    if repo_obj.is_empty:
        flask.abort(404, 'Empty repo cannot have a file')

    commit = repo_obj[repo_obj.head.target]
    content = __get_file_in_tree(
        repo_obj, commit.tree, filename.split('/'), bail_on_tree=True)
    if not content:
        flask.abort(404, 'File not found')

    if not isinstance(content, pygit2.Blob):
        flask.abort(404, 'File not found')
    if is_binary_string(content.data):
        flask.abort(400, 'Binary files cannot be blamed')

    content = ktc.to_bytes(content.data)
    blame = repo_obj.blame(filename)

    return flask.render_template(
        'blame.html',
        select='tree',
        repo=repo,
        origin='view_file',
        username=username,
        filename=filename,
        branchname=branchname,
        content=content,
        output_type='blame',
        blame=blame,
    )


@APP.route('/<repo>/c/<commitid>/')
@APP.route('/<repo>/c/<commitid>')
@APP.route('/<namespace>/<repo>/c/<commitid>/')
@APP.route('/<namespace>/<repo>/c/<commitid>')
@APP.route('/fork/<username>/<repo>/c/<commitid>/')
@APP.route('/fork/<username>/<repo>/c/<commitid>')
@APP.route('/fork/<username>/<namespace>/<repo>/c/<commitid>/')
@APP.route('/fork/<username>/<namespace>/<repo>/c/<commitid>')
def view_commit(repo, commitid, username=None, namespace=None):
    """ Render a commit in a repo
    """
    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

    branchname = flask.request.args.get('branch', None)

    if branchname and branchname not in repo_obj.listall_branches():
        branchname = None

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
        select='commits',
        repo=repo,
        branchname=branchname,
        username=username,
        commitid=commitid,
        commit=commit,
        diff=diff,
        form=pagure.forms.ConfirmationForm(),
    )


@APP.route('/<repo>/c/<commitid>.patch')
@APP.route('/<namespace>/<repo>/c/<commitid>.patch')
@APP.route('/fork/<username>/<repo>/c/<commitid>.patch')
@APP.route('/fork/<username>/<namespace>/<repo>/c/<commitid>.patch')
def view_commit_patch(repo, commitid, username=None, namespace=None):
    """ Render a commit in a repo as patch
    """
    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

    try:
        commit = repo_obj.get(commitid)
    except ValueError:
        flask.abort(404, 'Commit not found')

    if commit is None:
        flask.abort(404, 'Commit not found')

    patch = pagure.lib.git.commit_to_patch(repo_obj, commit)

    return flask.Response(patch, content_type="text/plain;charset=UTF-8")


@APP.route('/<repo>/tree/')
@APP.route('/<repo>/tree')
@APP.route('/<namespace>/<repo>/tree/')
@APP.route('/<namespace>/<repo>/tree')
@APP.route('/<repo>/tree/<path:identifier>')
@APP.route('/<namespace>/<repo>/tree/<path:identifier>')
@APP.route('/fork/<username>/<repo>/tree/')
@APP.route('/fork/<username>/<repo>/tree')
@APP.route('/fork/<username>/<namespace>/<repo>/tree/')
@APP.route('/fork/<username>/<namespace>/<repo>/tree')
@APP.route('/fork/<username>/<repo>/tree/<path:identifier>')
@APP.route('/fork/<username>/<namespace>/<repo>/tree/<path:identifier>')
def view_tree(repo, identifier=None, username=None, namespace=None):
    """ Render the tree of the repo
    """
    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

    branchname = None
    content = None
    output_type = None
    commit = None
    readme = None
    safe = False
    readme_ext = None
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
                if not repo_obj.head_is_unborn:
                    commit = repo_obj[repo_obj.head.target]
                    branchname = repo_obj.head.shorthand
        # If we're arriving here from the release page, we may have a Tag
        # where we expected a commit, in this case, get the actual commit
        if isinstance(commit, pygit2.Tag):
            commit = commit.get_object()

        if commit and not isinstance(commit, pygit2.Blob):
            content = sorted(commit.tree, key=lambda x: x.filemode)
            for i in commit.tree:
                name, ext = os.path.splitext(i.name)
                if name == 'README':
                    readme_file = __get_file_in_tree(
                        repo_obj, commit.tree, [i.name]).data

                    readme, safe = pagure.doc_utils.convert_readme(
                        readme_file, ext)

                    readme_ext = ext
        output_type = 'tree'

    return flask.render_template(
        'file.html',
        select='tree',
        origin='view_tree',
        repo=repo,
        username=username,
        branchname=branchname,
        filename='',
        content=content,
        output_type=output_type,
        readme=readme,
        readme_ext=readme_ext,
        safe=safe,
    )


@APP.route('/<repo>/forks/')
@APP.route('/<repo>/forks')
@APP.route('/<namespace>/<repo>/forks/')
@APP.route('/<namespace>/<repo>/forks')
@APP.route('/fork/<username>/<repo>/forks/')
@APP.route('/fork/<username>/<repo>/forks')
@APP.route('/fork/<username>/<namespace>/<repo>/forks/')
@APP.route('/fork/<username>/<namespace>/<repo>/forks')
def view_forks(repo, username=None, namespace=None):
    """ Presents all the forks of the project.
    """
    repo = flask.g.repo

    return flask.render_template(
        'forks.html',
        select='forks',
        username=username,
        repo=repo,
    )


@APP.route('/<repo>/releases/')
@APP.route('/<repo>/releases')
@APP.route('/<namespace>/<repo>/releases/')
@APP.route('/<namespace>/<repo>/releases')
@APP.route('/fork/<username>/<repo>/releases/')
@APP.route('/fork/<username>/<repo>/releases')
@APP.route('/fork/<username>/<namespace>/<repo>/releases/')
@APP.route('/fork/<username>/<namespace>/<repo>/releases')
def view_tags(repo, username=None, namespace=None):
    """ Presents all the tags of the project.
    """
    repo = flask.g.repo
    tags = pagure.lib.git.get_git_tags_objects(repo)

    return flask.render_template(
        'releases.html',
        select='tags',
        username=username,
        repo=repo,
        tags=tags,
    )


@APP.route('/<repo>/upload/', methods=('GET', 'POST'))
@APP.route('/<repo>/upload', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/upload/', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/upload', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/upload/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/upload', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/upload/', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/upload', methods=('GET', 'POST'))
@login_required
def new_release(repo, username=None, namespace=None):
    """ Upload a new release.
    """
    if not APP.config.get('UPLOAD_FOLDER_PATH') \
            and not APP.config.get('UPLOAD_FOLDER'):
        flask.abort(404)

    repo = flask.g.repo

    if not flask.g.repo_admin:
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
                    repo.fullname)
                if not os.path.exists(folder):
                    os.makedirs(folder)
                filestream.save(os.path.join(folder, filename))
                flask.flash('File "%s" uploaded' % filename)
            except Exception as err:  # pragma: no cover
                APP.logger.exception(err)
                flask.flash('Upload failed', 'error')
        return flask.redirect(flask.url_for(
            'view_tags', repo=repo.name, username=username,
            namespace=repo.namespace))

    return flask.render_template(
        'new_release.html',
        select='tags',
        username=username,
        repo=repo,
        form=form,
    )


@APP.route('/<repo>/settings/', methods=('GET', 'POST'))
@APP.route('/<repo>/settings', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/settings/', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/settings', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/settings/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/settings', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/settings/', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/settings', methods=('GET', 'POST'))
@login_required
def view_settings(repo, username=None, namespace=None):
    """ Presents the settings of the project.
    """
    if admin_session_timedout():
        if flask.request.method == 'POST':
            flask.flash('Action canceled, try it again', 'error')
        return flask.redirect(
            flask.url_for('auth_login', next=flask.request.url))

    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    plugins = pagure.lib.plugins.get_plugin_names(
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
                'view_repo', username=username, repo=repo.name,
                namespace=repo.namespace))
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
        form=form,
        tag_form=tag_form,
        branches_form=branches_form,
        tags=tags,
        plugins=plugins,
        branchname=branchname,
    )


@APP.route('/<repo>/update', methods=['POST'])
@APP.route('/<namespace>/<repo>/update', methods=['POST'])
@APP.route('/fork/<username>/<repo>/update', methods=['POST'])
@APP.route('/fork/<username>/<namespace>/<repo>/update', methods=['POST'])
@login_required
def update_project(repo, username=None, namespace=None):
    """ Update the description of a project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo

    if not flask.g.repo_admin:
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
        'view_settings', username=username, repo=repo.name,
        namespace=repo.namespace))


@APP.route('/<repo>/update/priorities', methods=['POST'])
@APP.route('/<namespace>/<repo>/update/priorities', methods=['POST'])
@APP.route('/fork/<username>/<repo>/update/priorities', methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/update/priorities',
    methods=['POST'])
@login_required
def update_priorities(repo, username=None, namespace=None):
    """ Update the priorities of a project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    if not flask.g.repo_admin:
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
            priorities[''] = ''
            try:
                repo.priorities = priorities
                SESSION.add(repo)
                SESSION.commit()
                flask.flash('Priorities updated')
            except SQLAlchemyError as err:  # pragma: no cover
                SESSION.rollback()
                flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_settings', username=username, repo=repo.name,
        namespace=repo.namespace))


@APP.route('/<repo>/update/milestones', methods=['POST'])
@APP.route('/<namespace>/<repo>/update/milestones', methods=['POST'])
@APP.route('/fork/<username>/<repo>/update/milestones', methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/update/milestones',
    methods=['POST'])
@login_required
def update_milestones(repo, username=None, namespace=None):
    """ Update the milestones of a project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    form = pagure.forms.ConfirmationForm()

    error = False
    if form.validate_on_submit():
        milestones = [
            w.strip() for w in flask.request.form.getlist('milestones')
        ]

        milestone_dates = [
            p.strip() for p in flask.request.form.getlist('milestone_dates')
        ]

        if len(milestones) != len(milestone_dates):
            flask.flash(
                'Milestones and dates are not of the same length',
                'error')
            error = True

        for milestone in milestones:
            if milestone.strip() and milestones.count(milestone) != 1:
                flask.flash(
                    'Milestone %s is present %s times' % (
                        milestone, milestones.count(milestone)
                    ),
                    'error')
                error = True
                break

        for milestone_date in milestone_dates:
            if milestone_date.strip() and milestone_dates.count(milestone_date) != 1:
                flask.flash(
                    'Date %s is present %s times' % (
                        milestone_date, milestone_dates.count(milestone_date)
                    ),
                    'error')
                error = True
                break

        if not error:
            miles = {}
            for cnt in range(len(milestones)):
                if milestones[cnt].strip():
                    miles[milestones[cnt]] = milestone_dates[cnt]
            try:
                repo.milestones = miles
                SESSION.add(repo)
                SESSION.commit()
                flask.flash('Milestones updated')
            except SQLAlchemyError as err:  # pragma: no cover
                SESSION.rollback()
                flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_settings', username=username, repo=repo.name,
        namespace=namespace))


@APP.route('/<repo>/default/branch/', methods=['POST'])
@APP.route('/<namespace>/<repo>/default/branch/', methods=['POST'])
@APP.route('/fork/<username>/<repo>/default/branch/', methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/default/branch/', methods=['POST'])
@login_required
def change_ref_head(repo, username=None, namespace=None):
    """ Change HEAD reference
    """

    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo
    reponame = flask.g.reponame
    repo_obj = flask.g.repo_obj

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    branches = repo_obj.listall_branches()
    form = pagure.forms.DefaultBranchForm(branches=branches)

    if form.validate_on_submit():
        branchname = form.branches.data
        try:
            reference = repo_obj.lookup_reference(
                'refs/heads/%s' % branchname).resolve()
            repo_obj.set_head(reference.name)
            flask.flash('Default branch updated to %s' % branchname)
        except Exception as err:  # pragma: no cover
            APP.logger.exception(err)

    return flask.redirect(flask.url_for(
        'view_settings', username=username, repo=repo.name,
        namespace=namespace))


@APP.route('/<repo>/delete', methods=['POST'])
@APP.route('/<namespace>/<repo>/delete', methods=['POST'])
@APP.route('/fork/<username>/<repo>/delete', methods=['POST'])
@APP.route('/fork/<username>/<namespace>/<repo>/delete', methods=['POST'])
@login_required
def delete_repo(repo, username=None, namespace=None):
    """ Delete the present project.
    """
    if not pagure.APP.config.get('ENABLE_DEL_PROJECTS', True):
        flask.abort(404)

    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo

    if not flask.g.repo_admin:
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


@APP.route('/<repo>/hook_token', methods=['POST'])
@APP.route('/<namespace>/<repo>/hook_token', methods=['POST'])
@APP.route('/fork/<username>/<repo>/hook_token', methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/hook_token', methods=['POST'])
@login_required
def new_repo_hook_token(repo, username=None, namespace=None):
    """ Re-generate a hook token for the present project.
    """
    if not pagure.APP.config.get('WEBHOOK', False):
        flask.abort(404)

    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo

    if not flask.g.repo_admin:
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

    return flask.redirect(flask.url_for(
        'view_settings', repo=repo.name, username=username,
        namespace=namespace))


@APP.route('/<repo>/dropuser/<int:userid>', methods=['POST'])
@APP.route('/<namespace>/<repo>/dropuser/<int:userid>', methods=['POST'])
@APP.route('/fork/<username>/<repo>/dropuser/<int:userid>',
           methods=['POST'])
@APP.route('/fork/<username>/<namespace>/<repo>/dropuser/<int:userid>',
           methods=['POST'])
@login_required
def remove_user(repo, userid, username=None, namespace=None):
    """ Remove the specified user from the project.
    """

    if not pagure.APP.config.get('ENABLE_USER_MNGT', True):
        flask.abort(404, 'User management not allowed in the pagure instance')

    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to change the users for this project')

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        userids = [str(user.id) for user in repo.users]

        if str(userid) not in userids:
            flask.flash(
                'User does not have commit rights, or cannot have them removed', 'error')
            return flask.redirect(flask.url_for(
                '.view_settings', repo=repo.name, username=username,
                namespace=repo.namespace,)
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

    return flask.redirect(flask.url_for(
        '.view_settings', repo=repo.name, username=username,
        namespace=namespace))


@APP.route('/<repo>/adduser/', methods=('GET', 'POST'))
@APP.route('/<repo>/adduser', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/adduser/', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/adduser', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/adduser/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/adduser', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/adduser/', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/adduser', methods=('GET', 'POST'))
@login_required
def add_user(repo, username=None, namespace=None):
    """ Add the specified user from the project.
    """

    if not pagure.APP.config.get('ENABLE_USER_MNGT', True):
        flask.abort(
            404, 'User management is not allowed in this pagure instance')

    if admin_session_timedout():
        if flask.request.method == 'POST':
            flask.flash('Action canceled, try it again', 'error')
        return flask.redirect(
            flask.url_for('auth_login', next=flask.request.url))

    repo = flask.g.repo

    if not flask.g.repo_admin:
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
            return flask.redirect(flask.url_for(
                '.view_settings', repo=repo.name, username=username,
                namespace=namespace))
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


@APP.route('/<repo>/dropgroup/<int:groupid>', methods=['POST'])
@APP.route('/<namespace>/<repo>/dropgroup/<int:groupid>', methods=['POST'])
@APP.route(
    '/fork/<username>/<repo>/dropgroup/<int:groupid>', methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/dropgroup/<int:groupid>',
    methods=['POST'])
@login_required
def remove_group_project(repo, groupid, username=None, namespace=None):
    """ Remove the specified group from the project.
    """

    if not pagure.APP.config.get('ENABLE_USER_MNGT', True):
        flask.abort(
            404, 'User management is not allowed in this pagure instance')

    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to change the users for this project')

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        grpids = [grp.id for grp in repo.groups]

        if groupid not in grpids:
            flask.flash(
                'Group does not seem to be part of this project', 'error')
            return flask.redirect(flask.url_for(
                '.view_settings', repo=repo.name, username=username,
                namespace=namespace))

        for grp in repo.groups:
            if grp.id == groupid:
                repo.groups.remove(grp)
                break
        try:
            SESSION.commit()
            pagure.lib.git.generate_gitolite_acls()
            flask.flash('Group removed')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash('Group could not be removed', 'error')

    return flask.redirect(flask.url_for(
        '.view_settings', repo=repo.name, username=username,
        namespace=namespace))


@APP.route('/<repo>/addgroup/', methods=('GET', 'POST'))
@APP.route('/<repo>/addgroup', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/addgroup/', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/addgroup', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/addgroup/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/addgroup', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/addgroup/', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/addgroup', methods=('GET', 'POST'))
@login_required
def add_group_project(repo, username=None, namespace=None):
    """ Add the specified group from the project.
    """

    if not pagure.APP.config.get('ENABLE_USER_MNGT', True):
        flask.abort(
            404, 'User management is not allowed in this pagure instance')

    if admin_session_timedout():
        if flask.request.method == 'POST':
            flask.flash('Action canceled, try it again', 'error')
        return flask.redirect(
            flask.url_for('auth_login', next=flask.request.url))

    repo = flask.g.repo

    if not flask.g.repo_admin:
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
                create=not pagure.APP.config.get('ENABLE_GROUP_MNGT', False),
                is_admin=pagure.is_admin(),
            )
            SESSION.commit()
            pagure.lib.git.generate_gitolite_acls()
            flask.flash(msg)
            return flask.redirect(flask.url_for(
                '.view_settings', repo=repo.name, username=username,
                namespace=namespace))
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


@APP.route('/<repo>/regenerate', methods=['POST'])
@APP.route('/<namespace>/<repo>/regenerate', methods=['POST'])
@APP.route('/fork/<username>/<repo>/regenerate', methods=['POST'])
@APP.route('/fork/<username>/<namespace>/<repo>/regenerate', methods=['POST'])
@login_required
def regenerate_git(repo, username=None, namespace=None):
    """ Regenerate the specified git repo with the content in the project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo

    if not flask.g.repo_admin:
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

    return flask.redirect(flask.url_for(
        '.view_settings', repo=repo.name, username=username,
        namespace=namespace))


@APP.route('/<repo>/token/new/', methods=('GET', 'POST'))
@APP.route('/<repo>/token/new', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/token/new/', methods=('GET', 'POST'))
@APP.route('/<namespace>/<repo>/token/new', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/token/new/', methods=('GET', 'POST'))
@APP.route('/fork/<username>/<repo>/token/new', methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/token/new/',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/token/new',
    methods=('GET', 'POST'))
@login_required
def add_token(repo, username=None, namespace=None):
    """ Add a token to a specified project.
    """
    if admin_session_timedout():
        if flask.request.method == 'POST':
            flask.flash('Action canceled, try it again', 'error')
        return flask.redirect(
            flask.url_for('auth_login', next=flask.request.url))

    repo = flask.g.repo

    if not flask.g.repo_admin:
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
            return flask.redirect(flask.url_for(
                '.view_settings', repo=repo.name, username=username,
                namespace=namespace))
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            APP.logger.exception(err)
            flask.flash('User could not be added', 'error')

    return flask.render_template(
        'add_token.html',
        select='settings',
        form=form,
        acls=acls,
        username=username,
        repo=repo,
    )


@APP.route('/<repo>/token/revoke/<token_id>', methods=['POST'])
@APP.route('/<namespace>/<repo>/token/revoke/<token_id>', methods=['POST'])
@APP.route(
    '/fork/<username>/<repo>/token/revoke/<token_id>', methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/token/revoke/<token_id>',
    methods=['POST'])
@login_required
def revoke_api_token(repo, token_id, username=None, namespace=None):
    """ Revokie a token to a specified project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo

    if not flask.g.repo_admin:
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

    return flask.redirect(flask.url_for(
        '.view_settings', repo=repo.name, username=username,
        namespace=namespace))


@APP.route(
    '/<repo>/edit/<path:branchname>/f/<path:filename>',
    methods=('GET', 'POST'))
@APP.route(
    '/<namespace>/<repo>/edit/<path:branchname>/f/<path:filename>',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<repo>/edit/<path:branchname>/f/<path:filename>',
    methods=('GET', 'POST'))
@APP.route(
    '/fork/<username>/<namespace>/<repo>/edit/<path:branchname>/f/<path:filename>',
    methods=('GET', 'POST'))
@login_required
def edit_file(repo, branchname, filename, username=None, namespace=None):
    """ Edit a file online.
    """
    repo = flask.g.repo
    reponame = flask.g.reponame
    repo_obj = flask.g.repo_obj

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    user = pagure.lib.search_user(
        SESSION, username=flask.g.fas_user.username)

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
                    namespace=namespace, branchname=form.branch.data)
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
    )


@APP.route('/<repo>/b/<path:branchname>/delete', methods=['POST'])
@APP.route('/<namespace>/<repo>/b/<path:branchname>/delete', methods=['POST'])
@APP.route('/fork/<username>/<repo>/b/<path:branchname>/delete',
           methods=['POST'])
@APP.route('/fork/<username>/<namespace>/<repo>/b/<path:branchname>/delete',
           methods=['POST'])
@login_required
def delete_branch(repo, branchname, username=None, namespace=None):
    """ Delete the branch of a project.
    """
    reponame = flask.g.reponame
    repo_obj = flask.g.repo_obj

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to delete branch for this project')

    if branchname == 'master':
        flask.abort(403, 'You are not allowed to delete the master branch')

    if branchname not in repo_obj.listall_branches():
        flask.abort(404, 'Branch no found')

    try:
        branch = repo_obj.lookup_branch(branchname)
        branch.delete()
        flask.flash('Branch `%s` deleted' % branchname)
    except pygit2.GitError as err:
        APP.logger.exception(err)
        flask.flash('Could not delete `%s`' % branchname, 'error')

    return flask.redirect(flask.url_for(
        'view_repo', repo=repo, username=username, namespace=namespace))


@APP.route('/docs/<repo>/')
@APP.route('/docs/<repo>/<path:filename>')
@APP.route('/docs/<namespace>/<repo>/')
@APP.route('/docs/<namespace>/<repo>/<path:filename>')
@APP.route('/docs/fork/<username>/<repo>/')
@APP.route('/docs/fork/<username>/<namespace>/<repo>/<path:filename>')
@APP.route('/docs/fork/<username>/<repo>/')
@APP.route('/docs/fork/<username>/<namespace>/<repo>/<path:filename>')
def view_docs(repo, username=None, filename=None, namespace=None):
    """ Display the documentation
    """
    repo = flask.g.repo

    if not APP.config.get('DOC_APP_URL'):
        flask.abort(404, 'This pagure instance has no doc server')

    return flask.render_template(
        'docs.html',
        select='docs',
        repo=repo,
        username=username,
        filename=filename,
        endpoint='view_docs',
    )


@APP.route('/<repo>/activity/')
@APP.route('/<repo>/activity')
@APP.route('/<namespace>/<repo>/activity/')
@APP.route('/<namespace>/<repo>/activity')
def view_project_activity(repo, namespace=None):
    """ Display the activity feed
    """

    if not APP.config.get('DATAGREPPER_URL'):
        flask.abort(404)

    repo = flask.g.repo

    return flask.render_template(
        'activity.html',
        repo=repo,
    )


@APP.route('/<repo>/watch/settings/<watch>', methods=['POST'])
@APP.route('/<namespace>/<repo>/watch/settings/<watch>', methods=['POST'])
@APP.route(
    '/fork/<username>/<repo>/watch/settings/<watch>', methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/watch/settings/<watch>',
    methods=['POST'])
@login_required
def watch_repo(repo, watch, username=None, namespace=None):
    """ Marked for watching or Unwatching
    """

    return_point = flask.url_for('index')
    if pagure.is_safe_url(flask.request.referrer):
        return_point = flask.request.referrer

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.abort(400)

    if str(watch) not in ['0', '1']:
        flask.abort(400)

    try:
        msg = pagure.lib.update_watch_status(
            SESSION,
            flask.g.repo,
            flask.g.fas_user.username,
            watch)
        SESSION.commit()
        flask.flash(msg)
    except pagure.exceptions.PagureException as msg:
        flask.flash(msg, 'error')

    return flask.redirect(return_point)


@APP.route('/<repo>/update/public_notif', methods=['POST'])
@APP.route('/<namespace>/<repo>/public_notif', methods=['POST'])
@APP.route('/fork/<username>/<repo>/public_notif', methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/public_notif', methods=['POST'])
@login_required
def update_public_notifications(repo, username=None, namespace=None):
    """ Update the public notification settings of a project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    form = pagure.forms.PublicNotificationForm()

    error = False
    if form.validate_on_submit():
        issue_notifs = [
            w.strip()
            for w in form.issue_notifs.data.split(',')
            if w.strip()
        ]
        pr_notifs = [
            w.strip()
            for w in form.pr_notifs.data.split(',')
            if w.strip()
        ]

        try:
            notifs = repo.notifications
            notifs['issues'] = issue_notifs
            notifs['requests'] = pr_notifs
            repo.notifications = notifs

            SESSION.add(repo)
            SESSION.commit()
            flask.flash('Project updated')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')
    else:
        flask.flash(
            'Unable to adjust one or more of the email provided', 'error')

    return flask.redirect(flask.url_for(
        'view_settings', username=username, repo=repo.name,
        namespace=repo.namespace))


@APP.route('/<repo>/update/close_status', methods=['POST'])
@APP.route('/<namespace>/<repo>/update/close_status', methods=['POST'])
@APP.route('/fork/<username>/<repo>/update/close_status', methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/update/close_status',
    methods=['POST'])
@login_required
def update_close_status(repo, username=None, namespace=None):
    """ Update the close_status of a project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    form = pagure.forms.ConfirmationForm()

    error = False
    if form.validate_on_submit():
        close_status = [
            w.strip() for w in flask.request.form.getlist('close_status')
            if w.strip()
        ]
        try:
            repo.close_status = close_status
            SESSION.add(repo)
            SESSION.commit()
            flask.flash('List of close status updated')
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_settings', username=username, repo=repo.name,
        namespace=namespace))


@APP.route('/<repo>/update/custom_keys', methods=['POST'])
@APP.route('/<namespace>/<repo>/update/custom_keys', methods=['POST'])
@APP.route('/fork/<username>/<repo>/update/custom_keys', methods=['POST'])
@APP.route(
    '/fork/<username>/<namespace>/<repo>/update/custom_keys',
    methods=['POST'])
@login_required
def update_custom_keys(repo, username=None, namespace=None):
    """ Update the custom_keys of a project.
    """
    if admin_session_timedout():
        flask.flash('Action canceled, try it again', 'error')
        url = flask.url_for(
            'view_settings', username=username, repo=repo,
            namespace=namespace)
        return flask.redirect(
            flask.url_for('auth_login', next=url))

    repo = flask.g.repo

    if not repo.settings.get('issue_tracker', True):
        flask.abort(404, 'No issue tracker found for this project')

    if not flask.g.repo_admin:
        flask.abort(
            403,
            'You are not allowed to change the settings for this project')

    form = pagure.forms.ConfirmationForm()

    error = False
    if form.validate_on_submit():
        custom_keys = [
            w.strip() for w in flask.request.form.getlist('custom_keys')
            if w.strip()
        ]
        custom_keys_type = [
            w.strip() for w in flask.request.form.getlist('custom_keys_type')
            if w.strip()
        ]

        try:
            msg = pagure.lib.set_custom_key_fields(
                SESSION, repo, custom_keys, custom_keys_type)
            SESSION.commit()
            flask.flash(msg)
        except SQLAlchemyError as err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')

    return flask.redirect(flask.url_for(
        'view_settings', username=username, repo=repo.name,
        namespace=namespace))
