# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Farhaan Bukhsh <farhaan.bukhsh@gmail.com>

"""

# pylint: disable=too-many-lines
# pylint: disable=too-many-branches
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# pylint: disable=bare-except
# pylint: disable=broad-except


from __future__ import unicode_literals

import datetime
import json
import logging
import os
import re
from math import ceil

import flask
import pygit2
import kitchen.text.converters as ktc
import six
import werkzeug

from six import BytesIO
from PIL import Image
from sqlalchemy.exc import SQLAlchemyError

from binaryornot.helpers import is_binary_string

import pagure.exceptions
import pagure.lib
import pagure.lib.git
import pagure.lib.mimetype
import pagure.lib.plugins
import pagure.lib.tasks
import pagure.forms
import pagure.ui.plugins
from pagure.config import config as pagure_config
from pagure.lib import encoding_utils
from pagure.ui import UI_NS
from pagure.utils import (
    __get_file_in_tree,
    login_required,
    is_true,
    stream_template,
)
from pagure.decorators import (
    is_repo_admin,
    is_admin_sess_timedout,
    has_issue_tracker,
    has_trackers,
)

_log = logging.getLogger(__name__)


def get_preferred_readme(tree):
    """ Establish some order about which README gets displayed
    if there are several in the repository. If none of the listed
    README files is availabe, display either the next file that
    starts with 'README' or nothing at all.
    """
    order = ["README.md", "README.rst", "README", "README.txt"]
    readmes = [x for x in tree if x.name.startswith("README")]
    if len(readmes) > 1:
        for i in order:
            for j in readmes:
                if i == j.name:
                    return j
    elif len(readmes) == 1:
        return readmes[0]
    return None


@UI_NS.route("/<repo>.git")
@UI_NS.route("/<namespace>/<repo>.git")
@UI_NS.route("/fork/<username>/<repo>.git")
@UI_NS.route("/fork/<username>/<namespace>/<repo>.git")
def view_repo_git(repo, username=None, namespace=None):
    """ Redirect to the project index page when user wants to view
    the git repo of the project
    """
    return flask.redirect(
        flask.url_for(
            "ui_ns.view_repo",
            repo=repo,
            username=username,
            namespace=namespace,
        )
    )


@UI_NS.route("/<repo>/")
@UI_NS.route("/<repo>")
@UI_NS.route("/<namespace>/<repo>/")
@UI_NS.route("/<namespace>/<repo>")
@UI_NS.route("/fork/<username>/<repo>/")
@UI_NS.route("/fork/<username>/<repo>")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/")
@UI_NS.route("/fork/<username>/<namespace>/<repo>")
def view_repo(repo, username=None, namespace=None):
    """ Front page of a specific repo.
    """
    repo_db = flask.g.repo
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
                repo_obj.head.target, pygit2.GIT_SORT_TIME
            ):
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
    project = pagure.lib.get_authorized_project(
        flask.g.session, repo, user=username, namespace=namespace
    )
    watch_users = set()
    watch_users.add(project.user.username)
    for access_type in project.access_users.keys():
        for user in project.access_users[access_type]:
            watch_users.add(user.username)
    for watcher in project.watchers:
        if watcher.watch_issues or watcher.watch_commits:
            watch_users.add(watcher.user.username)
    readmefile = get_preferred_readme(tree)
    if readmefile:
        name, ext = os.path.splitext(readmefile.name)
        content = __get_file_in_tree(
            repo_obj, last_commits[0].tree, [readmefile.name]
        ).data
        readme, safe = pagure.doc_utils.convert_readme(
            content,
            ext,
            view_file_url=flask.url_for(
                "ui_ns.view_raw_file",
                username=username,
                repo=repo_db.name,
                identifier=branchname,
                filename="",
            ),
        )
    return flask.render_template(
        "repo_info.html",
        select="overview",
        repo=repo_db,
        username=username,
        head=head,
        readme=readme,
        safe=safe,
        origin="view_repo",
        branchname=branchname,
        last_commits=last_commits,
        tree=tree,
        num_watchers=len(watch_users),
    )


"""
@UI_NS.route('/<repo>/branch/<path:branchname>')
@UI_NS.route('/<namespace>/<repo>/branch/<path:branchname>')
@UI_NS.route('/fork/<username>/<repo>/branch/<path:branchname>')
@UI_NS.route('/fork/<username>/<namespace>/<repo>/branch/<path:branchname>')
def view_repo_branch(repo, branchname, username=None, namespace=None):
    ''' Returns the list of branches in the repo. '''

    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

    if branchname not in repo_obj.listall_branches():
        flask.abort(404, 'Branch not found')

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
        parentname = repo.parent.repopath('main')
    else:
        parentname = repo.repopath('main')

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
                        'ui_ns.view_raw_file', username=username,
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
    )
"""


@UI_NS.route("/<repo>/commits/")
@UI_NS.route("/<repo>/commits")
@UI_NS.route("/<repo>/commits/<path:branchname>")
@UI_NS.route("/<namespace>/<repo>/commits/")
@UI_NS.route("/<namespace>/<repo>/commits")
@UI_NS.route("/<namespace>/<repo>/commits/<path:branchname>")
@UI_NS.route("/fork/<username>/<repo>/commits/")
@UI_NS.route("/fork/<username>/<repo>/commits")
@UI_NS.route("/fork/<username>/<repo>/commits/<path:branchname>")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/commits/")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/commits")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/commits/<path:branchname>")
def view_commits(repo, branchname=None, username=None, namespace=None):
    """ Displays the commits of the specified repo.
    """
    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

    commit = None
    branch = None
    if branchname and branchname in repo_obj.listall_branches():
        branch = repo_obj.lookup_branch(branchname)
        commit = branch.get_object()
    elif branchname:
        try:
            commit = repo_obj.get(branchname)
        except (ValueError, TypeError):
            pass

        if "refs/tags/%s" % branchname in list(repo_obj.references):
            ref = repo_obj.lookup_reference("refs/tags/%s" % branchname)
            commit = ref.get_object()

        # If we're arriving here from the release page, we may have a Tag
        # where we expected a commit, in this case, get the actual commit
        if isinstance(commit, pygit2.Tag):
            commit = commit.get_object()
            branchname = commit.oid.hex
    elif not repo_obj.is_empty and not repo_obj.head_is_unborn:
        branch = repo_obj.lookup_branch(repo_obj.head.shorthand)
        commit = branch.get_object()
        branchname = branch.branch_name

    if not repo_obj.is_empty and not repo_obj.head_is_unborn:
        head = repo_obj.head.shorthand
    else:
        head = None

    try:
        page = int(flask.request.args.get("page", 1))
    except (ValueError, TypeError):
        page = 1

    author = flask.request.args.get("author", None)
    author_obj = None
    if author:
        try:
            author_obj = pagure.lib.get_user(flask.g.session, author)
        except pagure.exceptions.PagureException:
            pass
        if not author_obj:
            flask.flash("No user found for the author: %s" % author, "error")

    limit = pagure_config["ITEM_PER_PAGE"]
    start = limit * (page - 1)
    end = limit * page

    n_commits = 0
    last_commits = []
    if commit:
        for commit in repo_obj.walk(commit.hex, pygit2.GIT_SORT_TIME):

            # Filters the commits for a user
            if author_obj:
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
        parentname = repo.parent.repopath("main")
    else:
        parentname = repo.repopath("main")

    orig_repo = pygit2.Repository(parentname)

    if (
        not repo_obj.is_empty
        and not orig_repo.is_empty
        and len(repo_obj.listall_branches()) > 1
    ):

        if not orig_repo.head_is_unborn:
            compare_branch = orig_repo.lookup_branch(orig_repo.head.shorthand)
        else:
            compare_branch = None

        if compare_branch and branch:
            (
                diff,
                diff_commits_full,
                orig_commit,
            ) = pagure.lib.git.get_diff_info(
                repo_obj,
                orig_repo,
                branch.branch_name,
                compare_branch.branch_name,
            )

            for commit in diff_commits_full:
                diff_commits.append(commit.oid.hex)

    return flask.render_template(
        "commits.html",
        select="commits",
        origin="view_commits",
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
        flag_statuses_labels=json.dumps(pagure_config["FLAG_STATUSES_LABELS"]),
    )


@UI_NS.route("/<repo>/c/<commit1>..<commit2>/")
@UI_NS.route("/<repo>/c/<commit1>..<commit2>")
@UI_NS.route("/<namespace>/<repo>/c/<commit1>..<commit2>/")
@UI_NS.route("/<namespace>/<repo>/c/<commit1>..<commit2>")
@UI_NS.route("/fork/<username>/<repo>/c/<commit1>..<commit2>/")
@UI_NS.route("/fork/<username>/<repo>/c/<commit1>..<commit2>")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/c/<commit1>..<commit2>/")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/c/<commit1>..<commit2>")
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
        flask.abort(404, "First commit does not exist")
    if commit2_obj is None:
        flask.abort(404, "Last commit does not exist")

    # Get commits diff data
    diff = repo_obj.diff(commit1, commit2)

    # Get commits list
    diff_commits = []
    order = pygit2.GIT_SORT_TIME
    first_commit = commit1
    last_commit = commit2

    commits = [
        commit.oid.hex[: len(first_commit)]
        for commit in repo_obj.walk(last_commit, pygit2.GIT_SORT_TIME)
    ]

    if first_commit not in commits:
        first_commit = commit2
        last_commit = commit1

    for commit in repo_obj.walk(last_commit, order):
        diff_commits.append(commit)

        if commit.oid.hex == first_commit or commit.oid.hex.startswith(
            first_commit
        ):
            break

    if first_commit == commit2:
        diff_commits.reverse()

    return flask.render_template(
        "repo_comparecommits.html",
        select="commits",
        origin="compare_commits",
        repo=repo,
        username=username,
        head=head,
        commit1=commit1,
        commit2=commit2,
        diff=diff,
        diff_commits=diff_commits,
    )


@UI_NS.route("/<repo>/blob/<path:identifier>/f/<path:filename>")
@UI_NS.route("/<namespace>/<repo>/blob/<path:identifier>/f/<path:filename>")
@UI_NS.route(
    "/fork/<username>/<repo>/blob/<path:identifier>/f/<path:filename>"
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/blob/<path:identifier>/f/"
    "<path:filename>"
)
def view_file(repo, identifier, filename, username=None, namespace=None):
    """ Displays the content of a file or a tree for the specified repo.
    """
    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

    if repo_obj.is_empty:
        flask.abort(404, "Empty repo cannot have a file")

    if identifier in repo_obj.listall_branches():
        branchname = identifier
        branch = repo_obj.lookup_branch(identifier)
        commit = branch.get_object()
    else:
        try:
            commit = repo_obj.get(identifier)
            branchname = identifier
        except ValueError:
            if "master" not in repo_obj.listall_branches():
                flask.abort(404, "Branch not found")
            # If it's not a commit id then it's part of the filename
            commit = repo_obj[repo_obj.head.target]
            branchname = "master"

    if isinstance(commit, pygit2.Tag):
        commit = commit.get_object()

    tree = None
    if isinstance(commit, pygit2.Tree):
        tree = commit
    elif isinstance(commit, pygit2.Commit):
        tree = commit.tree

    if tree and commit and not isinstance(commit, pygit2.Blob):
        content = __get_file_in_tree(
            repo_obj, tree, filename.split("/"), bail_on_tree=True
        )
        if not content:
            flask.abort(404, "File not found")
        content = repo_obj[content.oid]
    else:
        content = commit

    if not content:
        flask.abort(404, "File not found")

    readme = None
    safe = False
    readme_ext = None
    headers = {}
    huge = False

    isbinary = False
    if "data" in dir(content):
        isbinary = is_binary_string(content.data)

    if isinstance(content, pygit2.Blob):
        rawtext = is_true(flask.request.args.get("text"))
        ext = filename[filename.rfind(".") :]
        if ext in (
            ".gif",
            ".png",
            ".bmp",
            ".tif",
            ".tiff",
            ".jpg",
            ".jpeg",
            ".ppm",
            ".pnm",
            ".pbm",
            ".pgm",
            ".webp",
            ".ico",
        ):
            try:
                Image.open(BytesIO(content.data))
                output_type = "image"
            except IOError as err:
                _log.debug("Failed to load image %s, error: %s", filename, err)
                output_type = "binary"
        elif ext in (".rst", ".mk", ".md", ".markdown") and not rawtext:
            content, safe = pagure.doc_utils.convert_readme(content.data, ext)
            output_type = "markup"
        elif "data" in dir(content) and not isbinary:
            file_content = None
            try:
                file_content = encoding_utils.decode(
                    ktc.to_bytes(content.data)
                )
            except pagure.exceptions.PagureException:
                # We cannot decode the file, so let's pretend it's a binary
                # file and let the user download it instead of displaying
                # it.
                output_type = "binary"
            if file_content is not None:
                output_type = "file"
                content = content.data.decode("utf-8")
            else:
                output_type = "binary"
        elif not isbinary:
            output_type = "file"
            huge = True
            safe = False
            content = content.data.decode("utf-8")
        else:
            output_type = "binary"
    elif isinstance(content, pygit2.Commit):
        flask.abort(404, "File not found")
    else:
        content = sorted(content, key=lambda x: x.filemode)
        for i in content:
            name, ext = os.path.splitext(i.name)
            if not isinstance(name, six.text_type):
                name = name.decode("utf-8")
            if name == "README":
                readme_file = __get_file_in_tree(
                    repo_obj, content, [i.name]
                ).data

                readme, safe = pagure.doc_utils.convert_readme(
                    readme_file, ext
                )

                readme_ext = ext
        output_type = "tree"

    if output_type == "binary":
        headers[str("Content-Disposition")] = "attachment"

    return flask.Response(
        flask.stream_with_context(
            stream_template(
                flask.current_app,
                "file.html",
                select="tree",
                repo=repo,
                origin="view_file",
                username=username,
                branchname=branchname,
                filename=filename,
                content=content,
                output_type=output_type,
                readme=readme,
                readme_ext=readme_ext,
                safe=safe,
                huge=huge,
            )
        ),
        200,
        headers,
    )


@UI_NS.route("/<repo>/raw/<path:identifier>")
@UI_NS.route("/<namespace>/<repo>/raw/<path:identifier>")
@UI_NS.route("/<repo>/raw/<path:identifier>/f/<path:filename>")
@UI_NS.route("/<namespace>/<repo>/raw/<path:identifier>/f/<path:filename>")
@UI_NS.route("/fork/<username>/<repo>/raw/<path:identifier>")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/raw/<path:identifier>")
@UI_NS.route("/fork/<username>/<repo>/raw/<path:identifier>/f/<path:filename>")
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/raw/<path:identifier>/f/"
    "<path:filename>"
)
def view_raw_file(
    repo, identifier, filename=None, username=None, namespace=None
):
    """ Displays the raw content of a file of a commit for the specified repo.
    """
    repo_obj = flask.g.repo_obj

    if repo_obj.is_empty:
        flask.abort(404, "Empty repo cannot have a file")

    if identifier in repo_obj.listall_branches():
        branch = repo_obj.lookup_branch(identifier)
        commit = branch.get_object()
    else:
        try:
            commit = repo_obj.get(identifier)
        except ValueError:
            if "master" not in repo_obj.listall_branches():
                flask.abort(404, "Branch not found")
            # If it's not a commit id then it's part of the filename
            commit = repo_obj[repo_obj.head.target]

    if not commit:
        flask.abort(404, "Commit %s not found" % (identifier))

    if isinstance(commit, pygit2.Tag):
        commit = commit.get_object()

    if filename:
        if isinstance(commit, pygit2.Blob):
            content = commit
        else:
            content = __get_file_in_tree(
                repo_obj, commit.tree, filename.split("/"), bail_on_tree=True
            )
        if not content or isinstance(content, pygit2.Tree):
            flask.abort(404, "File not found")

        data = repo_obj[content.oid].data
    else:
        if commit.parents:
            # We need to take this not so nice road to ensure that the
            # identifier retrieved from the URL is actually valid
            try:
                parent = repo_obj.revparse_single("%s^" % identifier)
                diff = repo_obj.diff(parent, commit)
            except (KeyError, ValueError):
                flask.abort(404, "Identifier not found")
        else:
            # First commit in the repo
            diff = commit.tree.diff_to_tree(swap=True)
        data = diff.patch

    if not data:
        flask.abort(404, "No content found")

    return (data, 200, pagure.lib.mimetype.get_type_headers(filename, data))


@UI_NS.route("/<repo>/blame/<path:filename>")
@UI_NS.route("/<namespace>/<repo>/blame/<path:filename>")
@UI_NS.route("/fork/<username>/<repo>/blame/<path:filename>")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/blame/<path:filename>")
def view_blame_file(repo, filename, username=None, namespace=None):
    """ Displays the blame of a file or a tree for the specified repo.
    """
    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

    branchname = flask.request.args.get("identifier", "master")

    if repo_obj.is_empty or repo_obj.head_is_unborn:
        flask.abort(404, "Empty repo cannot have a file")

    if branchname in repo_obj.listall_branches():
        branch = repo_obj.lookup_branch(branchname)
        commit = branch.get_object()
    else:
        try:
            commit = repo_obj[branchname]
        except ValueError:
            commit = repo_obj[repo_obj.head.target]

    if isinstance(commit, pygit2.Tag):
        commit = commit.get_object()

    content = __get_file_in_tree(
        repo_obj, commit.tree, filename.split("/"), bail_on_tree=True
    )
    if not content:
        flask.abort(404, "File not found")

    if not isinstance(content, pygit2.Blob):
        flask.abort(404, "File not found")
    if is_binary_string(content.data):
        flask.abort(400, "Binary files cannot be blamed")

    try:
        content = encoding_utils.decode(content.data)
    except pagure.exceptions.PagureException:
        # We cannot decode the file, so bail but warn the admins
        _log.exception("File could not be decoded")
        flask.abort(500, "File could not be decoded")

    blame = repo_obj.blame(filename, newest_commit=commit.oid.hex)

    return flask.render_template(
        "blame.html",
        select="tree",
        repo=repo,
        origin="view_file",
        username=username,
        filename=filename,
        branchname=branchname,
        content=content,
        output_type="blame",
        blame=blame,
    )


@UI_NS.route("/<repo>/c/<commitid>/")
@UI_NS.route("/<repo>/c/<commitid>")
@UI_NS.route("/<namespace>/<repo>/c/<commitid>/")
@UI_NS.route("/<namespace>/<repo>/c/<commitid>")
@UI_NS.route("/fork/<username>/<repo>/c/<commitid>/")
@UI_NS.route("/fork/<username>/<repo>/c/<commitid>")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/c/<commitid>/")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/c/<commitid>")
def view_commit(repo, commitid, username=None, namespace=None):
    """ Render a commit in a repo
    """
    repo = flask.g.repo
    if not repo:
        flask.abort(404, "Project not found")

    repo_obj = flask.g.repo_obj

    branchname = flask.request.args.get("branch", None)

    splitview = flask.request.args.get("splitview", False)

    if "splitview" in flask.request.args:
        splitview = True
    else:
        splitview = False

    if branchname and branchname not in repo_obj.listall_branches():
        branchname = None

    try:
        commit = repo_obj.get(commitid)
    except ValueError:
        flask.abort(404, "Commit not found")

    if commit is None:
        flask.abort(404, "Commit not found")

    if isinstance(commit, pygit2.Blob):
        flask.abort(404, "Commit not found")

    if commit.parents:
        diff = repo_obj.diff(commit.parents[0], commit)
    else:
        # First commit in the repo
        diff = commit.tree.diff_to_tree(swap=True)

    if diff:
        diff.find_similar()

    return flask.render_template(
        "commit.html",
        select="commits",
        repo=repo,
        branchname=branchname,
        username=username,
        commitid=commitid,
        commit=commit,
        diff=diff,
        splitview=splitview,
        flags=pagure.lib.get_commit_flag(flask.g.session, repo, commitid),
    )


@UI_NS.route("/<repo>/c/<commitid>.patch")
@UI_NS.route("/<namespace>/<repo>/c/<commitid>.patch")
@UI_NS.route("/fork/<username>/<repo>/c/<commitid>.patch")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/c/<commitid>.patch")
def view_commit_patch(repo, commitid, username=None, namespace=None):
    """ Render a commit in a repo as patch
    """
    return view_commit_patch_or_diff(
        repo, commitid, username, namespace, diff=False
    )


@UI_NS.route("/<repo>/c/<commitid>.diff")
@UI_NS.route("/<namespace>/<repo>/c/<commitid>.diff")
@UI_NS.route("/fork/<username>/<repo>/c/<commitid>.diff")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/c/<commitid>.diff")
def view_commit_diff(repo, commitid, username=None, namespace=None):
    """ Render a commit in a repo as diff
    """

    is_js = is_true(flask.request.args.get("js"))

    return view_commit_patch_or_diff(
        repo, commitid, username, namespace, diff=True, is_js=is_js
    )


def view_commit_patch_or_diff(
    repo, commitid, username=None, namespace=None, diff=False, is_js=False
):
    """ Renders a commit either as a patch or as a diff. """

    repo_obj = flask.g.repo_obj

    if is_js:
        errorresponse = flask.jsonify(
            {"code": "ERROR", "message": "Commit not found"}
        )
        errorresponse.status_code = 404

    try:
        commit = repo_obj.get(commitid)
    except ValueError:
        if is_js:
            return errorresponse
        else:
            flask.abort(404, "Commit not found")

    if commit is None:
        if is_js:
            return errorresponse
        else:
            flask.abort(404, "Commit not found")

    if is_js:
        patches = pagure.lib.git.commit_to_patch(
            repo_obj, commit, diff_view=True, find_similar=True, separated=True
        )

        diffs = {}
        for idx, patch in enumerate(patches):
            diffs[idx + 1] = patch

        return flask.jsonify(diffs)
    else:
        patch = pagure.lib.git.commit_to_patch(
            repo_obj, commit, diff_view=diff
        )
        return flask.Response(patch, content_type="text/plain;charset=UTF-8")


@UI_NS.route("/<repo>/tree/")
@UI_NS.route("/<repo>/tree")
@UI_NS.route("/<namespace>/<repo>/tree/")
@UI_NS.route("/<namespace>/<repo>/tree")
@UI_NS.route("/<repo>/tree/<path:identifier>")
@UI_NS.route("/<namespace>/<repo>/tree/<path:identifier>")
@UI_NS.route("/fork/<username>/<repo>/tree/")
@UI_NS.route("/fork/<username>/<repo>/tree")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/tree/")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/tree")
@UI_NS.route("/fork/<username>/<repo>/tree/<path:identifier>")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/tree/<path:identifier>")
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
            branchname = commit.oid.hex

        if commit and not isinstance(commit, pygit2.Blob):
            content = sorted(commit.tree, key=lambda x: x.filemode)
            for i in commit.tree:
                name, ext = os.path.splitext(i.name)
                if name == "README":
                    readme_file = __get_file_in_tree(
                        repo_obj, commit.tree, [i.name]
                    ).data

                    readme, safe = pagure.doc_utils.convert_readme(
                        readme_file, ext
                    )

                    readme_ext = ext
        output_type = "tree"

    return flask.render_template(
        "file.html",
        select="tree",
        origin="view_tree",
        repo=repo,
        username=username,
        branchname=branchname,
        filename="",
        content=content,
        output_type=output_type,
        readme=readme,
        readme_ext=readme_ext,
        safe=safe,
    )


@UI_NS.route("/<repo>/releases/")
@UI_NS.route("/<repo>/releases")
@UI_NS.route("/<namespace>/<repo>/releases/")
@UI_NS.route("/<namespace>/<repo>/releases")
@UI_NS.route("/fork/<username>/<repo>/releases/")
@UI_NS.route("/fork/<username>/<repo>/releases")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/releases/")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/releases")
def view_tags(repo, username=None, namespace=None):
    """ Presents all the tags of the project.
    """
    repo = flask.g.repo
    tags = pagure.lib.git.get_git_tags_objects(repo)

    upload_folder_path = pagure_config["UPLOAD_FOLDER_PATH"] or ""
    pagure_checksum = os.path.exists(
        os.path.join(upload_folder_path, repo.fullname, "CHECKSUMS")
    )

    return flask.render_template(
        "releases.html",
        select="tags",
        username=username,
        repo=repo,
        tags=tags,
        pagure_checksum=pagure_checksum,
    )


@UI_NS.route("/<repo>/branches/")
@UI_NS.route("/<repo>/branches")
@UI_NS.route("/<namespace>/<repo>/branches/")
@UI_NS.route("/<namespace>/<repo>/branches")
@UI_NS.route("/fork/<username>/<repo>/branches/")
@UI_NS.route("/fork/<username>/<repo>/branches")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/branches/")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/branches")
def view_branches(repo, username=None, namespace=None):
    """ Branches
    """
    repo_db = flask.g.repo
    repo_obj = flask.g.repo_obj

    if not repo_obj.is_empty and not repo_obj.head_is_unborn:
        head = repo_obj.head.shorthand
    else:
        head = None

    if not repo_obj.is_empty and not repo_obj.head_is_unborn:
        branchname = repo_obj.head.shorthand
    else:
        branchname = None

    return flask.render_template(
        "repo_branches.html",
        select="branches",
        repo=repo_db,
        username=username,
        head=head,
        origin="view_repo",
        branchname=branchname,
    )


@UI_NS.route("/<repo>/forks/")
@UI_NS.route("/<repo>/forks")
@UI_NS.route("/<namespace>/<repo>/forks/")
@UI_NS.route("/<namespace>/<repo>/forks")
@UI_NS.route("/fork/<username>/<repo>/forks/")
@UI_NS.route("/fork/<username>/<repo>/forks")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/forks/")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/forks")
def view_forks(repo, username=None, namespace=None):
    """ Forks
    """

    return flask.render_template(
        "repo_forks.html", select="forks", username=username, repo=flask.g.repo
    )


@UI_NS.route("/<repo>/upload/", methods=("GET", "POST"))
@UI_NS.route("/<repo>/upload", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/upload/", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/upload", methods=("GET", "POST"))
@UI_NS.route("/fork/<username>/<repo>/upload/", methods=("GET", "POST"))
@UI_NS.route("/fork/<username>/<repo>/upload", methods=("GET", "POST"))
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/upload/", methods=("GET", "POST")
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/upload", methods=("GET", "POST")
)
@login_required
@is_repo_admin
def new_release(repo, username=None, namespace=None):
    """ Upload a new release.
    """
    if not pagure_config.get("UPLOAD_FOLDER_PATH") or not pagure_config.get(
        "UPLOAD_FOLDER_URL"
    ):
        flask.abort(404)

    repo = flask.g.repo

    form = pagure.forms.UploadFileForm()

    if form.validate_on_submit():
        filenames = []
        error = False
        for filestream in flask.request.files.getlist("filestream"):
            filename = werkzeug.secure_filename(filestream.filename)
            filenames.append(filename)
            try:
                folder = os.path.join(
                    pagure_config["UPLOAD_FOLDER_PATH"], repo.fullname
                )
                if not os.path.exists(folder):
                    os.makedirs(folder)
                dest = os.path.join(folder, filename)
                if os.path.exists(dest):
                    raise pagure.exceptions.PagureException(
                        "This tarball has already been uploaded"
                    )

                filestream.save(dest)
                flask.flash('File "%s" uploaded' % filename)
            except pagure.exceptions.PagureException as err:
                _log.debug(err)
                flask.flash(str(err), "error")
                error = True
            except Exception as err:  # pragma: no cover
                _log.exception(err)
                flask.flash("Upload failed", "error")
                error = True

        if not error:
            task = pagure.lib.tasks.update_checksums_file.delay(
                folder=folder, filenames=filenames
            )
            _log.info(
                "Updating checksums for %s of project %s in task: %s"
                % (filenames, repo.fullname, task.id)
            )

        return flask.redirect(
            flask.url_for(
                "ui_ns.view_tags",
                repo=repo.name,
                username=username,
                namespace=repo.namespace,
            )
        )

    return flask.render_template(
        "new_release.html",
        select="tags",
        username=username,
        repo=repo,
        form=form,
    )


@UI_NS.route("/<repo>/settings/", methods=("GET", "POST"))
@UI_NS.route("/<repo>/settings", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/settings/", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/settings", methods=("GET", "POST"))
@UI_NS.route("/fork/<username>/<repo>/settings/", methods=("GET", "POST"))
@UI_NS.route("/fork/<username>/<repo>/settings", methods=("GET", "POST"))
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/settings/", methods=("GET", "POST")
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/settings", methods=("GET", "POST")
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def view_settings(repo, username=None, namespace=None):
    """ Presents the settings of the project.
    """

    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

    plugins = pagure.lib.plugins.get_plugin_names(
        pagure_config.get("DISABLED_PLUGINS")
    )
    tags = pagure.lib.get_tags_of_project(flask.g.session, repo)

    form = pagure.forms.ConfirmationForm()
    tag_form = pagure.forms.AddIssueTagForm()

    branches = repo_obj.listall_branches()
    branches_form = pagure.forms.DefaultBranchForm(branches=branches)
    priority_form = pagure.forms.DefaultPriorityForm(
        priorities=repo.priorities.values()
    )

    if form.validate_on_submit():
        settings = {}
        for key in flask.request.form:
            if key == "csrf_token":
                continue
            settings[key] = flask.request.form[key]

        try:
            message = pagure.lib.update_project_settings(
                flask.g.session,
                repo=repo,
                settings=settings,
                user=flask.g.fas_user.username,
            )
            flask.g.session.commit()
            flask.flash(message)
            return flask.redirect(
                flask.url_for(
                    "ui_ns.view_repo",
                    username=username,
                    repo=repo.name,
                    namespace=repo.namespace,
                )
            )
        except pagure.exceptions.PagureException as msg:
            flask.g.session.rollback()
            _log.debug(msg)
            flask.flash(str(msg), "error")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(str(err), "error")

    if not repo_obj.is_empty and not repo_obj.head_is_unborn:
        branchname = repo_obj.head.shorthand
    else:
        branchname = None

    if flask.request.method == "GET" and branchname:
        branches_form.branches.data = branchname
        priority_form.priority.data = repo.default_priority

    return flask.render_template(
        "settings.html",
        select="settings",
        username=username,
        repo=repo,
        access_users=repo.access_users,
        access_groups=repo.access_groups,
        form=form,
        tag_form=tag_form,
        branches_form=branches_form,
        priority_form=priority_form,
        tags=tags,
        plugins=plugins,
        branchname=branchname,
        pagure_admin=pagure.utils.is_admin(),
    )


@UI_NS.route("/<repo>/settings/test_hook", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/settings/test_hook", methods=("GET", "POST"))
@UI_NS.route(
    "/fork/<username>/<repo>/settings/test_hook", methods=("GET", "POST")
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/settings/test_hook",
    methods=("GET", "POST"),
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def test_web_hook(repo, username=None, namespace=None):
    """ Endpoint that can be called to send a test message to the web-hook
    service allowing to test the web-hooks set.
    """

    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():

        pagure.lib.notify.log(
            project=repo,
            topic="Test.notification",
            msg={"content": "Test message"},
            redis=True,
        )
        flask.flash("Notification triggered")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            username=username,
            repo=repo.name,
            namespace=repo.namespace,
        )
        + "#projectoptions-tab"
    )


@UI_NS.route("/<repo>/update", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/update", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/update", methods=["POST"])
@UI_NS.route("/fork/<username>/<namespace>/<repo>/update", methods=["POST"])
@login_required
@is_admin_sess_timedout
@is_repo_admin
def update_project(repo, username=None, namespace=None):
    """ Update the description of a project.
    """

    repo = flask.g.repo

    form = pagure.forms.ProjectFormSimplified()

    if form.validate_on_submit():

        try:
            repo.description = form.description.data
            repo.avatar_email = form.avatar_email.data.strip()
            repo.url = form.url.data.strip()
            if repo.private:
                repo.private = form.private.data
            pagure.lib.update_tags(
                flask.g.session,
                repo,
                tags=[t.strip() for t in form.tags.data.split(",")],
                username=flask.g.fas_user.username,
            )
            flask.g.session.add(repo)
            flask.g.session.commit()
            flask.flash("Project updated")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(str(err), "error")
    else:
        for field in form.errors:
            flask.flash(
                'Field "%s" errored with errors: %s'
                % (field, ", ".join(form.errors[field])),
                "error",
            )

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            username=username,
            repo=repo.name,
            namespace=repo.namespace,
        )
        + "#projectdetails-tab"
    )


@UI_NS.route("/<repo>/update/priorities", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/update/priorities", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/update/priorities", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/update/priorities", methods=["POST"]
)
@login_required
@has_issue_tracker
@is_admin_sess_timedout
@is_repo_admin
def update_priorities(repo, username=None, namespace=None):
    """ Update the priorities of a project.
    """

    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()

    error = False
    if form.validate_on_submit():
        weights = [
            w.strip()
            for w in flask.request.form.getlist("priority_weigth")
            if w.strip()
        ]
        try:
            weights = [int(w) for w in weights]
        except (ValueError, TypeError):
            flask.flash("Priorities weights must be numbers", "error")
            error = True

        titles = [
            p.strip()
            for p in flask.request.form.getlist("priority_title")
            if p.strip()
        ]

        if len(weights) != len(titles):
            flask.flash(
                "Priorities weights and titles are not of the same length",
                "error",
            )
            error = True

        for weight in weights:
            if weights.count(weight) != 1:
                flask.flash(
                    "Priority weight %s is present %s times"
                    % (weight, weights.count(weight)),
                    "error",
                )
                error = True
                break

        for title in titles:
            if titles.count(title) != 1:
                flask.flash(
                    "Priority %s is present %s times"
                    % (title, titles.count(title)),
                    "error",
                )
                error = True
                break

        if not error:
            priorities = {}
            if weights:
                for cnt in range(len(weights)):
                    priorities[weights[cnt]] = titles[cnt]
                priorities[""] = ""
            try:
                repo.priorities = priorities
                if repo.default_priority not in priorities.values():
                    flask.flash(
                        "Default priority reset as it is no longer one of "
                        "set priorities."
                    )
                    repo.default_priority = None
                flask.g.session.add(repo)
                flask.g.session.commit()
                flask.flash("Priorities updated")
            except SQLAlchemyError as err:  # pragma: no cover
                flask.g.session.rollback()
                flask.flash(str(err), "error")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            username=username,
            repo=repo.name,
            namespace=repo.namespace,
        )
        + "#priorities-tab"
    )


@UI_NS.route("/<repo>/update/default_priority", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/update/default_priority", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<repo>/update/default_priority", methods=["POST"]
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/update/default_priority",
    methods=["POST"],
)
@login_required
@has_issue_tracker
@is_admin_sess_timedout
@is_repo_admin
def default_priority(repo, username=None, namespace=None):
    """ Update the default priority of a project.
    """

    repo = flask.g.repo

    form = pagure.forms.DefaultPriorityForm(
        priorities=repo.priorities.values()
    )

    if form.validate_on_submit():
        priority = form.priority.data or None
        if priority in repo.priorities.values() or priority is None:
            repo.default_priority = priority
            try:
                flask.g.session.add(repo)
                flask.g.session.commit()
                if priority:
                    flask.flash("Default priority set to %s" % priority)
                else:
                    flask.flash("Default priority reset")
            except SQLAlchemyError as err:  # pragma: no cover
                flask.g.session.rollback()
                flask.flash(str(err), "error")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            username=username,
            repo=repo.name,
            namespace=repo.namespace,
        )
        + "#priorities-tab"
    )


@UI_NS.route("/<repo>/update/milestones", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/update/milestones", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/update/milestones", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/update/milestones", methods=["POST"]
)
@login_required
@has_issue_tracker
@is_admin_sess_timedout
@is_repo_admin
def update_milestones(repo, username=None, namespace=None):
    """ Update the milestones of a project.
    """

    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()

    error = False
    if form.validate_on_submit():
        redirect = flask.request.args.get("from")
        milestones = [
            w.strip() for w in flask.request.form.getlist("milestones")
        ]

        for cnt, milestone in enumerate(milestones):
            if milestone.strip() and milestones.count(milestone) != 1:
                flask.flash(
                    "Milestone %s is present %s times"
                    % (milestone, milestones.count(milestone)),
                    "error",
                )
                error = True
                break

        keys = []
        if not error:
            miles = {}
            for cnt in range(len(milestones)):
                active = (
                    True
                    if flask.request.form.get(
                        "active_milestone_%s" % (cnt + 1)
                    )
                    else False
                )
                date = flask.request.form.get(
                    "milestone_date_%s" % (cnt + 1), None
                )

                if milestones[cnt].strip():
                    miles[milestones[cnt]] = {
                        "date": date.strip() if date else None,
                        "active": active,
                    }
                    keys.append(milestones[cnt])
            try:
                repo.milestones = miles
                repo.milestones_keys = keys
                flask.g.session.add(repo)
                flask.g.session.commit()
                flask.flash("Milestones updated")
            except SQLAlchemyError as err:  # pragma: no cover
                flask.g.session.rollback()
                flask.flash(str(err), "error")

        if redirect == "issues":
            return flask.redirect(
                flask.url_for(
                    "ui_ns.view_issues",
                    username=username,
                    repo=repo.name,
                    namespace=namespace,
                )
            )

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            username=username,
            repo=repo.name,
            namespace=namespace,
        )
        + "#roadmap-tab"
    )


@UI_NS.route("/<repo>/default/branch/", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/default/branch/", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/default/branch/", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/default/branch/", methods=["POST"]
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def change_ref_head(repo, username=None, namespace=None):
    """ Change HEAD reference
    """

    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

    branches = repo_obj.listall_branches()
    form = pagure.forms.DefaultBranchForm(branches=branches)

    if form.validate_on_submit():
        branchname = form.branches.data
        try:
            reference = repo_obj.lookup_reference(
                "refs/heads/%s" % branchname
            ).resolve()
            repo_obj.set_head(reference.name)
            flask.flash("Default branch updated to %s" % branchname)
        except Exception as err:  # pragma: no cover
            _log.exception(err)

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            username=username,
            repo=repo.name,
            namespace=namespace,
        )
        + "#defaultbranch-tab"
    )


@UI_NS.route("/<repo>/delete", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/delete", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/delete", methods=["POST"])
@UI_NS.route("/fork/<username>/<namespace>/<repo>/delete", methods=["POST"])
@login_required
@is_admin_sess_timedout
@is_repo_admin
def delete_repo(repo, username=None, namespace=None):
    """ Delete the present project.
    """
    repo = flask.g.repo

    del_project = pagure_config.get("ENABLE_DEL_PROJECTS", True)
    del_fork = pagure_config.get("ENABLE_DEL_FORKS", del_project)
    if (not repo.is_fork and not del_project) or (
        repo.is_fork and not del_fork
    ):
        flask.abort(404)

    if repo.read_only:
        flask.flash(
            "The ACLs of this project are being refreshed in the backend "
            "this prevents the project from being deleted. Please wait "
            "for this task to finish before trying again. Thanks!"
        )
        return flask.redirect(
            flask.url_for(
                "ui_ns.view_settings",
                repo=repo.name,
                username=username,
                namespace=namespace,
            )
            + "#deleteproject-tab"
        )

    task = pagure.lib.tasks.delete_project.delay(
        namespace=repo.namespace,
        name=repo.name,
        user=repo.user.user if repo.is_fork else None,
        action_user=flask.g.fas_user.username,
    )
    return pagure.utils.wait_for_task(task)


@UI_NS.route("/<repo>/hook_token", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/hook_token", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/hook_token", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/hook_token", methods=["POST"]
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def new_repo_hook_token(repo, username=None, namespace=None):
    """ Re-generate a hook token for the present project.
    """
    if not pagure_config.get("WEBHOOK", False):
        flask.abort(404)

    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.abort(400, "Invalid request")

    try:
        repo.hook_token = pagure.lib.login.id_generator(40)
        flask.g.session.commit()
        flask.flash("New hook token generated")
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        _log.exception(err)
        flask.flash("Could not generate a new token for this project", "error")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            repo=repo.name,
            username=username,
            namespace=namespace,
        )
        + "#privatehookkey-tab"
    )


@UI_NS.route("/<repo>/dropdeploykey/<int:keyid>", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/dropdeploykey/<int:keyid>", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<repo>/dropdeploykey/<int:keyid>", methods=["POST"]
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/dropdeploykey/<int:keyid>",
    methods=["POST"],
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def remove_deploykey(repo, keyid, username=None, namespace=None):
    """ Remove the specified deploy key from the project.
    """

    if not pagure_config.get("DEPLOY_KEY", True):
        flask.abort(404, "This pagure instance disabled deploy keys")

    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        keyids = ["%s" % key.id for key in repo.deploykeys]
        keyid = "%s" % keyid

        if keyid not in keyids:
            flask.flash("Deploy key does not exist in project.", "error")
            return flask.redirect(
                flask.url_for(
                    "ui_ns.view_settings",
                    repo=repo.name,
                    username=username,
                    namespace=repo.namespace,
                )
                + "#deploykeys-tab"
            )

        for key in repo.deploykeys:
            if "%s" % key.id == keyid:
                flask.g.session.delete(key)
                break
        try:
            flask.g.session.commit()
            pagure.lib.create_deploykeys_ssh_keys_on_disk(
                repo, pagure_config.get("GITOLITE_KEYDIR", None)
            )
            pagure.lib.tasks.gitolite_post_compile_only.delay()
            flask.flash("Deploy key removed")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("Deploy key could not be removed", "error")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            repo=repo.name,
            username=username,
            namespace=namespace,
        )
        + "#deploykey-tab"
    )


@UI_NS.route("/<repo>/dropuser/<int:userid>", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/dropuser/<int:userid>", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/dropuser/<int:userid>", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/dropuser/<int:userid>",
    methods=["POST"],
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def remove_user(repo, userid, username=None, namespace=None):
    """ Remove the specified user from the project.
    """

    if not pagure_config.get("ENABLE_USER_MNGT", True):
        flask.abort(404, "User management not allowed in the pagure instance")

    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()
    delete_themselves = False
    if form.validate_on_submit():
        try:
            user = pagure.lib.get_user_by_id(flask.g.session, int(userid))
            delete_themselves = user.username == flask.g.fas_user.username
            msg = pagure.lib.remove_user_of_project(
                flask.g.session, user, repo, flask.g.fas_user.username
            )
            flask.flash(msg)
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("User could not be removed", "error")
        except pagure.exceptions.PagureException as err:
            flask.flash("%s" % err, "error")
            return flask.redirect(
                flask.url_for(
                    "ui_ns.view_settings",
                    repo=repo.name,
                    username=username,
                    namespace=repo.namespace,
                )
                + "#usersgroups-tab"
            )

    endpoint = "ui_ns.view_settings"
    tab = "#usersgroups-tab"
    if delete_themselves:
        endpoint = "ui_ns.view_repo"
        tab = ""
    return flask.redirect(
        flask.url_for(
            endpoint, repo=repo.name, username=username, namespace=namespace
        )
        + tab
    )


@UI_NS.route("/<repo>/adddeploykey/", methods=("GET", "POST"))
@UI_NS.route("/<repo>/adddeploykey", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/adddeploykey/", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/adddeploykey", methods=("GET", "POST"))
@UI_NS.route("/fork/<username>/<repo>/adddeploykey/", methods=("GET", "POST"))
@UI_NS.route("/fork/<username>/<repo>/adddeploykey", methods=("GET", "POST"))
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/adddeploykey/",
    methods=("GET", "POST"),
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/adddeploykey", methods=("GET", "POST")
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def add_deploykey(repo, username=None, namespace=None):
    """ Add the specified deploy key to the project.
    """

    if not pagure_config.get("DEPLOY_KEY", True):
        flask.abort(404, "This pagure instance disabled deploy keys")

    repo = flask.g.repo

    form = pagure.forms.AddDeployKeyForm()

    if form.validate_on_submit():
        try:
            msg = pagure.lib.add_deploykey_to_project(
                flask.g.session,
                repo,
                ssh_key=form.ssh_key.data,
                pushaccess=form.pushaccess.data,
                user=flask.g.fas_user.username,
            )
            flask.g.session.commit()
            pagure.lib.create_deploykeys_ssh_keys_on_disk(
                repo, pagure_config.get("GITOLITE_KEYDIR", None)
            )
            pagure.lib.tasks.gitolite_post_compile_only.delay()
            flask.flash(msg)
            return flask.redirect(
                flask.url_for(
                    "ui_ns.view_settings",
                    repo=repo.name,
                    username=username,
                    namespace=namespace,
                )
                + "#deploykey-tab"
            )
        except pagure.exceptions.PagureException as msg:
            flask.g.session.rollback()
            _log.debug(msg)
            flask.flash(str(msg), "error")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("Deploy key could not be added", "error")

    return flask.render_template(
        "add_deploykey.html", form=form, username=username, repo=repo
    )


@UI_NS.route("/<repo>/adduser/", methods=("GET", "POST"))
@UI_NS.route("/<repo>/adduser", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/adduser/", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/adduser", methods=("GET", "POST"))
@UI_NS.route("/fork/<username>/<repo>/adduser/", methods=("GET", "POST"))
@UI_NS.route("/fork/<username>/<repo>/adduser", methods=("GET", "POST"))
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/adduser/", methods=("GET", "POST")
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/adduser", methods=("GET", "POST")
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def add_user(repo, username=None, namespace=None):
    """ Add the specified user to the project.
    """

    if not pagure_config.get("ENABLE_USER_MNGT", True):
        flask.abort(
            404, "User management is not allowed in this pagure instance"
        )

    repo = flask.g.repo

    user_to_update = flask.request.args.get("user", "").strip()
    user_to_update_obj = None
    user_access = None
    if user_to_update:
        user_to_update_obj = pagure.lib.search_user(
            flask.g.session, username=user_to_update
        )
        user_access = pagure.lib.get_obj_access(
            flask.g.session, repo, user_to_update_obj
        )

    # The requested user is not found
    if user_to_update_obj is None:
        user_to_update = None
        user_access = None

    form = pagure.forms.AddUserForm()

    if form.validate_on_submit():
        try:
            msg = pagure.lib.add_user_to_project(
                flask.g.session,
                repo,
                new_user=form.user.data,
                user=flask.g.fas_user.username,
                access=form.access.data,
                required_groups=pagure_config.get("REQUIRED_GROUPS"),
            )
            flask.g.session.commit()
            pagure.lib.git.generate_gitolite_acls(project=repo)
            flask.flash(msg)
            return flask.redirect(
                flask.url_for(
                    "ui_ns.view_settings",
                    repo=repo.name,
                    username=username,
                    namespace=namespace,
                )
                + "#usersgroups-tab"
            )
        except pagure.exceptions.PagureException as msg:
            flask.g.session.rollback()
            _log.debug(msg)
            flask.flash(str(msg), "error")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("User could not be added", "error")

    access_levels = pagure.lib.get_access_levels(flask.g.session)
    return flask.render_template(
        "add_user.html",
        form=form,
        username=username,
        repo=repo,
        access_levels=access_levels,
        user_to_update=user_to_update,
        user_access=user_access,
    )


@UI_NS.route("/<repo>/dropgroup/<int:groupid>", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/dropgroup/<int:groupid>", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<repo>/dropgroup/<int:groupid>", methods=["POST"]
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/dropgroup/<int:groupid>",
    methods=["POST"],
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def remove_group_project(repo, groupid, username=None, namespace=None):
    """ Remove the specified group from the project.
    """

    if not pagure_config.get("ENABLE_USER_MNGT", True):
        flask.abort(
            404, "User management is not allowed in this pagure instance"
        )

    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        grpids = [grp.id for grp in repo.groups]

        if groupid not in grpids:
            flask.flash(
                "Group does not seem to be part of this project", "error"
            )
            return flask.redirect(
                flask.url_for(
                    "ui_ns.view_settings",
                    repo=repo.name,
                    username=username,
                    namespace=namespace,
                )
                + "#usersgroups-tab"
            )

        for grp in repo.groups:
            if grp.id == groupid:
                repo.groups.remove(grp)
                break
        try:
            # Mark the project as read_only, celery will unmark it
            pagure.lib.update_read_only_mode(
                flask.g.session, repo, read_only=True
            )
            flask.g.session.commit()
            pagure.lib.git.generate_gitolite_acls(project=repo)
            flask.flash("Group removed")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("Group could not be removed", "error")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            repo=repo.name,
            username=username,
            namespace=namespace,
        )
        + "#usersgroups-tab"
    )


@UI_NS.route("/<repo>/addgroup/", methods=("GET", "POST"))
@UI_NS.route("/<repo>/addgroup", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/addgroup/", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/addgroup", methods=("GET", "POST"))
@UI_NS.route("/fork/<username>/<repo>/addgroup/", methods=("GET", "POST"))
@UI_NS.route("/fork/<username>/<repo>/addgroup", methods=("GET", "POST"))
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/addgroup/", methods=("GET", "POST")
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/addgroup", methods=("GET", "POST")
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def add_group_project(repo, username=None, namespace=None):
    """ Add the specified group to the project.
    """

    if not pagure_config.get("ENABLE_USER_MNGT", True):
        flask.abort(
            404, "User management is not allowed in this pagure instance"
        )

    repo = flask.g.repo

    group_to_update = flask.request.args.get("group", "").strip()
    group_to_update_obj = None
    group_access = None
    if group_to_update:
        group_to_update_obj = pagure.lib.search_groups(
            flask.g.session, group_name=group_to_update
        )
        group_access = pagure.lib.get_obj_access(
            flask.g.session, repo, group_to_update_obj
        )

    # The requested group is not found
    if group_to_update_obj is None:
        group_to_update = None
        group_access = None

    form = pagure.forms.AddGroupForm()

    if form.validate_on_submit():
        try:
            msg = pagure.lib.add_group_to_project(
                flask.g.session,
                repo,
                new_group=form.group.data,
                user=flask.g.fas_user.username,
                access=form.access.data,
                create=pagure_config.get("ENABLE_GROUP_MNGT", False),
                is_admin=pagure.utils.is_admin(),
            )
            flask.g.session.commit()
            pagure.lib.git.generate_gitolite_acls(project=repo)
            flask.flash(msg)
            return flask.redirect(
                flask.url_for(
                    "ui_ns.view_settings",
                    repo=repo.name,
                    username=username,
                    namespace=namespace,
                )
                + "#usersgroups-tab"
            )
        except pagure.exceptions.PagureException as msg:
            flask.g.session.rollback()
            _log.debug(msg)
            flask.flash(str(msg), "error")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("Group could not be added", "error")

    access_levels = pagure.lib.get_access_levels(flask.g.session)
    return flask.render_template(
        "add_group_project.html",
        form=form,
        username=username,
        repo=repo,
        access_levels=access_levels,
        group_to_update=group_to_update,
        group_access=group_access,
    )


@UI_NS.route("/<repo>/regenerate", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/regenerate", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/regenerate", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/regenerate", methods=["POST"]
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def regenerate_git(repo, username=None, namespace=None):
    """ Regenerate the specified git repo with the content in the project.
    """

    repo = flask.g.repo

    regenerate = flask.request.form.get("regenerate")
    if not regenerate or regenerate.lower() not in ["tickets", "requests"]:
        flask.abort(400, "You can only regenerate tickest or requests repos")

    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        if regenerate.lower() == "requests" and repo.settings.get(
            "pull_requests"
        ):

            # delete the requests repo and reinit
            # in case there are no requests
            if len(repo.requests) == 0:
                pagure.lib.git.reinit_git(
                    project=repo, repofolder=pagure_config["REQUESTS_FOLDER"]
                )
            for request in repo.requests:
                pagure.lib.git.update_git(
                    request,
                    repo=repo,
                    repofolder=pagure_config["REQUESTS_FOLDER"],
                )
            flask.flash("Requests git repo updated")

        elif (
            regenerate.lower() == "tickets"
            and repo.settings.get("issue_tracker")
            and pagure_config.get("ENABLE_TICKETS")
        ):

            # delete the ticket repo and reinit
            # in case there are no tickets
            if len(repo.issues) == 0:
                pagure.lib.git.reinit_git(
                    project=repo, repofolder=pagure_config["TICKETS_FOLDER"]
                )
            for ticket in repo.issues:
                pagure.lib.git.update_git(
                    ticket,
                    repo=repo,
                    repofolder=pagure_config["TICKETS_FOLDER"],
                )
            flask.flash("Tickets git repo updated")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            repo=repo.name,
            username=username,
            namespace=namespace,
        )
        + "#regen-tab"
    )


@UI_NS.route("/<repo>/token/new/", methods=("GET", "POST"))
@UI_NS.route("/<repo>/token/new", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/token/new/", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/token/new", methods=("GET", "POST"))
@UI_NS.route("/fork/<username>/<repo>/token/new/", methods=("GET", "POST"))
@UI_NS.route("/fork/<username>/<repo>/token/new", methods=("GET", "POST"))
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/token/new/", methods=("GET", "POST")
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/token/new", methods=("GET", "POST")
)
@login_required
@is_admin_sess_timedout
def add_token(repo, username=None, namespace=None):
    """ Add a token to a specified project.
    """

    repo = flask.g.repo

    if not flask.g.repo_committer:
        flask.abort(
            403, "You are not allowed to change the settings for this project"
        )

    acls = pagure.lib.get_acls(
        flask.g.session, restrict=pagure_config.get("USER_ACLS")
    )
    form = pagure.forms.NewTokenForm(acls=acls)

    if form.validate_on_submit():
        try:
            msg = pagure.lib.add_token_to_user(
                flask.g.session,
                repo,
                description=form.description.data.strip() or None,
                acls=form.acls.data,
                username=flask.g.fas_user.username,
            )
            flask.g.session.commit()
            flask.flash(msg)
            return flask.redirect(
                flask.url_for(
                    "ui_ns.view_settings",
                    repo=repo.name,
                    username=username,
                    namespace=namespace,
                )
                + "#apikeys-tab"
            )
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("API token could not be added", "error")

    # When form is displayed after an empty submission, show an error.
    if form.errors.get("acls"):
        flask.flash("You must select at least one permission.", "error")

    return flask.render_template(
        "add_token.html",
        select="settings",
        form=form,
        acls=acls,
        username=username,
        repo=repo,
    )


@UI_NS.route("/<repo>/token/renew/<token_id>", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/token/renew/<token_id>", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<repo>/token/renew/<token_id>", methods=["POST"]
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/token/renew/<token_id>",
    methods=["POST"],
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def renew_api_token(repo, token_id, username=None, namespace=None):
    """ Renew a token to a specified project.
    """

    repo = flask.g.repo

    token = pagure.lib.get_api_token(flask.g.session, token_id)

    if (
        not token
        or token.project.fullname != repo.fullname
        or token.user.username != flask.g.fas_user.username
    ):
        flask.abort(404, "Token not found")

    form = pagure.forms.ConfirmationForm()

    if form.validate_on_submit():
        acls = [acl.name for acl in token.acls]
        try:
            msg = pagure.lib.add_token_to_user(
                flask.g.session,
                repo,
                description=token.description or None,
                acls=acls,
                username=flask.g.fas_user.username,
            )
            flask.g.session.commit()
            flask.flash(msg)
            return flask.redirect(
                flask.url_for(
                    "ui_ns.view_settings",
                    repo=repo.name,
                    username=username,
                    namespace=namespace,
                )
                + "#apikeys-tab"
            )
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("API token could not be renewed", "error")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            repo=repo.name,
            username=username,
            namespace=namespace,
        )
        + "#apikeys-tab"
    )


@UI_NS.route("/<repo>/token/revoke/<token_id>", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/token/revoke/<token_id>", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<repo>/token/revoke/<token_id>", methods=["POST"]
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/token/revoke/<token_id>",
    methods=["POST"],
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def revoke_api_token(repo, token_id, username=None, namespace=None):
    """ Revokie a token to a specified project.
    """

    repo = flask.g.repo

    token = pagure.lib.get_api_token(flask.g.session, token_id)

    if (
        not token
        or token.project.fullname != repo.fullname
        or token.user.username != flask.g.fas_user.username
    ):
        flask.abort(404, "Token not found")

    form = pagure.forms.ConfirmationForm()

    if form.validate_on_submit():
        try:
            if token.expiration >= datetime.datetime.utcnow():
                token.expiration = datetime.datetime.utcnow()
                flask.g.session.add(token)
            flask.g.session.commit()
            flask.flash("Token revoked")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash(
                "Token could not be revoked, please contact an admin", "error"
            )

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            repo=repo.name,
            username=username,
            namespace=namespace,
        )
        + "#apikeys-tab"
    )


@UI_NS.route(
    "/<repo>/edit/<path:branchname>/f/<path:filename>", methods=("GET", "POST")
)
@UI_NS.route(
    "/<namespace>/<repo>/edit/<path:branchname>/f/<path:filename>",
    methods=("GET", "POST"),
)
@UI_NS.route(
    "/fork/<username>/<repo>/edit/<path:branchname>/f/<path:filename>",
    methods=("GET", "POST"),
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/edit/<path:branchname>/f/"
    "<path:filename>",
    methods=("GET", "POST"),
)
@login_required
@is_repo_admin
def edit_file(repo, branchname, filename, username=None, namespace=None):
    """ Edit a file online.
    """
    repo = flask.g.repo
    repo_obj = flask.g.repo_obj

    user = pagure.lib.search_user(
        flask.g.session, username=flask.g.fas_user.username
    )

    if repo_obj.is_empty:
        flask.abort(404, "Empty repo cannot have a file")

    form = pagure.forms.EditFileForm(emails=user.emails)

    branch = None
    if branchname in repo_obj.listall_branches():
        branch = repo_obj.lookup_branch(branchname)
        commit = branch.get_object()
    else:
        flask.abort(400, "Invalid branch specified")

    if form.validate_on_submit():
        try:
            task = pagure.lib.tasks.update_file_in_git.delay(
                repo.name,
                repo.namespace,
                repo.user.username if repo.is_fork else None,
                branch=branchname,
                branchto=form.branch.data,
                filename=filename,
                content=form.content.data,
                message="%s\n\n%s"
                % (
                    form.commit_title.data.strip(),
                    form.commit_message.data.strip(),
                ),
                username=user.username,
                email=form.email.data,
            )
            return pagure.utils.wait_for_task(task)
        except pagure.exceptions.PagureException as err:  # pragma: no cover
            _log.exception(err)
            flask.flash("Commit could not be done", "error")
            data = form.content.data
    elif flask.request.method == "GET":
        form.email.data = user.default_email
        content = __get_file_in_tree(
            repo_obj, commit.tree, filename.split("/")
        )
        if not content or isinstance(content, pygit2.Tree):
            flask.abort(404, "File not found")

        if is_binary_string(content.data):
            flask.abort(400, "Cannot edit binary files")

        try:
            data = repo_obj[content.oid].data.decode("utf-8")
        except UnicodeDecodeError:  # pragma: no cover
            # In theory we shouldn't reach here since we check if the file
            # is binary with `is_binary_string()` above
            flask.abort(400, "Cannot edit binary files")

    else:
        data = form.content.data
        if not isinstance(data, six.text_type):
            data = data.decode("utf-8")

    return flask.render_template(
        "edit_file.html",
        select="tree",
        repo=repo,
        username=username,
        branchname=branchname,
        data=data,
        filename=filename,
        form=form,
        user=user,
    )


@UI_NS.route("/<repo>/b/<path:branchname>/delete", methods=["POST"])
@UI_NS.route(
    "/<namespace>/<repo>/b/<path:branchname>/delete", methods=["POST"]
)
@UI_NS.route(
    "/fork/<username>/<repo>/b/<path:branchname>/delete", methods=["POST"]
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/b/<path:branchname>/delete",
    methods=["POST"],
)
@login_required
def delete_branch(repo, branchname, username=None, namespace=None):
    """ Delete the branch of a project.
    """
    if not flask.g.repo.is_fork and not pagure_config.get(
        "ALLOW_DELETE_BRANCH", True
    ):
        flask.abort(404, "This pagure instance does not allow branch deletion")

    repo_obj = flask.g.repo_obj

    if not flask.g.repo_committer:
        flask.abort(
            403, "You are not allowed to delete branch for this project"
        )

    if branchname == "master":
        flask.abort(403, "You are not allowed to delete the master branch")

    if branchname not in repo_obj.listall_branches():
        flask.abort(404, "Branch not found")

    task = pagure.lib.tasks.delete_branch.delay(
        repo, namespace, username, branchname
    )
    return pagure.utils.wait_for_task(task)


@UI_NS.route("/docs/<repo>/")
@UI_NS.route("/docs/<repo>/<path:filename>")
@UI_NS.route("/docs/<namespace>/<repo>/")
@UI_NS.route("/docs/<namespace>/<repo>/<path:filename>")
@UI_NS.route("/docs/fork/<username>/<repo>/")
@UI_NS.route("/docs/fork/<username>/<namespace>/<repo>/<path:filename>")
@UI_NS.route("/docs/fork/<username>/<repo>/")
@UI_NS.route("/docs/fork/<username>/<namespace>/<repo>/<path:filename>")
def view_docs(repo, username=None, filename=None, namespace=None):
    """ Display the documentation
    """
    repo = flask.g.repo

    if not pagure_config.get("DOC_APP_URL"):
        flask.abort(404, "This pagure instance has no doc server")

    return flask.render_template(
        "docs.html",
        select="docs",
        repo=repo,
        username=username,
        filename=filename,
        endpoint="view_docs",
    )


@UI_NS.route("/<repo>/activity/")
@UI_NS.route("/<repo>/activity")
@UI_NS.route("/<namespace>/<repo>/activity/")
@UI_NS.route("/<namespace>/<repo>/activity")
def view_project_activity(repo, namespace=None):
    """ Display the activity feed
    """

    if not pagure_config.get("DATAGREPPER_URL"):
        flask.abort(404)

    repo = flask.g.repo

    return flask.render_template("activity.html", repo=repo)


@UI_NS.route("/<repo>/stargazers/")
@UI_NS.route("/fork/<username>/<repo>/stargazers/")
@UI_NS.route("/<namespace>/<repo>/stargazers/")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/stargazers/")
def view_stargazers(repo, username=None, namespace=None):
    """ View all the users who have starred the project """

    stargazers = flask.g.repo.stargazers
    users = [star.user for star in stargazers]
    return flask.render_template(
        "repo_stargazers.html",
        repo=flask.g.repo,
        username=username,
        namespace=namespace,
        users=users,
    )


@UI_NS.route("/<repo>/star/<star>", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/star/<star>", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/star/<star>", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/star/<star>", methods=["POST"]
)
@login_required
def star_project(repo, star, username=None, namespace=None):
    """ Star or Unstar a project

    :arg repo: string representing the project which has to be starred or
    unstarred.
    :arg star: either '0' or '1' for unstar and star respectively
    :arg username: string representing the user the fork of whose is being
    starred or unstarred.
    :arg namespace: namespace of the project if any
    """

    return_point = flask.url_for("ui_ns.index")
    if flask.request.referrer is not None and pagure.utils.is_safe_url(
        flask.request.referrer
    ):
        return_point = flask.request.referrer

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.abort(400)

    if star not in ["0", "1"]:
        flask.abort(400)

    try:
        msg = pagure.lib.update_star_project(
            flask.g.session,
            user=flask.g.fas_user.username,
            repo=flask.g.repo,
            star=star,
        )
        flask.g.session.commit()
        flask.flash(msg)
    except SQLAlchemyError:
        flask.flash("Could not star the project")

    return flask.redirect(return_point)


@UI_NS.route("/<repo>/watch/settings/<watch>", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/watch/settings/<watch>", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<repo>/watch/settings/<watch>", methods=["POST"]
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/watch/settings/<watch>",
    methods=["POST"],
)
@login_required
def watch_repo(repo, watch, username=None, namespace=None):
    """ Marked for watching or unwatching
    """

    return_point = flask.url_for("ui_ns.index")
    if pagure.utils.is_safe_url(flask.request.referrer):
        return_point = flask.request.referrer

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        flask.abort(400)

    if "%s" % watch not in ["0", "1", "2", "3", "-1"]:
        flask.abort(400)

    try:
        msg = pagure.lib.update_watch_status(
            flask.g.session, flask.g.repo, flask.g.fas_user.username, watch
        )
        flask.g.session.commit()
        flask.flash(msg)
    except pagure.exceptions.PagureException as msg:
        _log.debug(msg)
        flask.flash(str(msg), "error")

    return flask.redirect(return_point)


@UI_NS.route("/<repo>/update/public_notif", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/public_notif", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/public_notif", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/public_notif", methods=["POST"]
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def update_public_notifications(repo, username=None, namespace=None):
    """ Update the public notification settings of a project.
    """

    repo = flask.g.repo

    form = pagure.forms.PublicNotificationForm()

    if form.validate_on_submit():
        issue_notifs = [
            w.strip() for w in form.issue_notifs.data.split(",") if w.strip()
        ]
        pr_notifs = [
            w.strip() for w in form.pr_notifs.data.split(",") if w.strip()
        ]

        try:
            notifs = repo.notifications
            notifs["issues"] = issue_notifs
            notifs["requests"] = pr_notifs
            repo.notifications = notifs

            flask.g.session.add(repo)
            flask.g.session.commit()
            flask.flash("Project updated")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(str(err), "error")
    else:
        flask.flash(
            "Unable to adjust one or more of the email provided", "error"
        )

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            username=username,
            repo=repo.name,
            namespace=repo.namespace,
        )
        + "#publicnotifications-tab"
    )


@UI_NS.route("/<repo>/update/close_status", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/update/close_status", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/update/close_status", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/update/close_status", methods=["POST"]
)
@login_required
@has_issue_tracker
@is_admin_sess_timedout
@is_repo_admin
def update_close_status(repo, username=None, namespace=None):
    """ Update the close_status of a project.
    """

    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()

    if form.validate_on_submit():
        close_status = [
            w.strip()
            for w in flask.request.form.getlist("close_status")
            if w.strip()
        ]
        try:
            repo.close_status = close_status
            flask.g.session.add(repo)
            flask.g.session.commit()
            flask.flash("List of close status updated")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(str(err), "error")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            username=username,
            repo=repo.name,
            namespace=namespace,
        )
        + "#closestatus-tab"
    )


@UI_NS.route("/<repo>/update/quick_replies", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/update/quick_replies", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/update/quick_replies", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/update/quick_replies",
    methods=["POST"],
)
@login_required
@has_trackers
@is_admin_sess_timedout
@is_repo_admin
def update_quick_replies(repo, username=None, namespace=None):
    """ Update the quick_replies of a project.
    """

    repo = flask.g.repo

    if not repo.settings.get("pull_requests", True):
        flask.abort(404, "Pull requests are disabled for this project")

    form = pagure.forms.ConfirmationForm()

    if form.validate_on_submit():
        quick_replies = [
            w.strip()
            for w in flask.request.form.getlist("quick_reply")
            if w.strip()
        ]
        try:
            repo.quick_replies = quick_replies
            flask.g.session.add(repo)
            flask.g.session.commit()
            flask.flash("List of quick replies updated")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(str(err), "error")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            username=username,
            repo=repo.name,
            namespace=namespace,
        )
        + "#quickreplies-tab"
    )


@UI_NS.route("/<repo>/update/custom_keys", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/update/custom_keys", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/update/custom_keys", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/update/custom_keys", methods=["POST"]
)
@login_required
@has_issue_tracker
@is_admin_sess_timedout
@is_repo_admin
def update_custom_keys(repo, username=None, namespace=None):
    """ Update the custom_keys of a project.
    """

    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()

    if form.validate_on_submit():
        custom_keys = [
            w.strip()
            for w in flask.request.form.getlist("custom_keys")
            if w.strip()
        ]
        custom_keys_type = [
            w.strip()
            for w in flask.request.form.getlist("custom_keys_type")
            if w.strip()
        ]
        custom_keys_data = [
            w.strip() for w in flask.request.form.getlist("custom_keys_data")
        ]
        custom_keys_notify = []
        for idx in range(len(custom_keys)):
            custom_keys_notify.append(
                "%s"
                % flask.request.form.get("custom_keys_notify-%s" % (idx + 1))
            )

        try:
            msg = pagure.lib.set_custom_key_fields(
                flask.g.session,
                repo,
                custom_keys,
                custom_keys_type,
                custom_keys_data,
                custom_keys_notify,
            )
            flask.g.session.commit()
            flask.flash(msg)
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(str(err), "error")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            username=username,
            repo=repo.name,
            namespace=namespace,
        )
        + "#customfields-tab"
    )


@UI_NS.route("/<repo>/delete/report", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/delete/report", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/delete/report", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/delete/report", methods=["POST"]
)
@login_required
@has_issue_tracker
@is_admin_sess_timedout
@is_repo_admin
def delete_report(repo, username=None, namespace=None):
    """ Delete a report from a project.
    """

    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()

    if form.validate_on_submit():
        report = flask.request.form.get("report")
        reports = repo.reports
        if report not in reports:
            flask.flash("Unknown report: %s" % report, "error")
        else:
            del (reports[report])
            repo.reports = reports
            try:
                flask.g.session.add(repo)
                flask.g.session.commit()
                flask.flash("List of reports updated")
            except SQLAlchemyError as err:  # pragma: no cover
                flask.g.session.rollback()
                flask.flash(str(err), "error")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            username=username,
            repo=repo.name,
            namespace=namespace,
        )
        + "#reports-tab"
    )


@UI_NS.route("/<repo>/torepospanner", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/torepospanner", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/torepospanner", methods=["POST"])
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/torepospanner", methods=["POST"]
)
@login_required
@is_admin_sess_timedout
@is_repo_admin
def move_to_repospanner(repo, username=None, namespace=None):
    """ Give a project to someone else.
    """
    repo = flask.g.repo

    if not pagure.utils.is_admin():
        flask.abort(
            403, "You are not allowed to transfer this project to repoSpanner"
        )

    if not pagure_config.get("REPOSPANNER_ADMIN_MIGRATION"):
        flask.abort(403, "It is not allowed to request migration of a repo")

    form = pagure.forms.ConfirmationForm()

    if form.validate_on_submit():
        region = flask.request.form.get("region", "").strip()
        if not region:
            flask.abort(404, "No target region specified")

        if region not in pagure_config.get("REPOSPANNER_REGIONS"):
            flask.abort(404, "Invalid region specified")

        _log.info(
            "Repo %s requested to be migrated to repoSpanner region %s",
            repo.fullname,
            region,
        )

        task = pagure.lib.tasks.move_to_repospanner.delay(
            repo.name, namespace, username, region
        )

        return pagure.utils.wait_for_task(
            task,
            prev=flask.url_for(
                "ui_ns.view_repo",
                username=username,
                repo=repo.name,
                namespace=namespace,
            ),
        )

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_repo",
            username=username,
            repo=repo.name,
            namespace=namespace,
        )
    )


@UI_NS.route("/<repo>/give", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/give", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/give", methods=["POST"])
@UI_NS.route("/fork/<username>/<namespace>/<repo>/give", methods=["POST"])
@login_required
@is_admin_sess_timedout
@is_repo_admin
def give_project(repo, username=None, namespace=None):
    """ Give a project to someone else.
    """
    if not pagure_config.get("ENABLE_GIVE_PROJECTS", True):
        flask.abort(404)

    repo = flask.g.repo

    if (
        flask.g.fas_user.username != repo.user.user
        and not pagure.utils.is_admin()
    ):
        flask.abort(403, "You are not allowed to give this project")

    form = pagure.forms.ConfirmationForm()

    if form.validate_on_submit():
        new_username = flask.request.form.get("user", "").strip()
        if not new_username:
            flask.abort(404, "No user specified")
        new_owner = pagure.lib.search_user(
            flask.g.session, username=new_username
        )
        if not new_owner:
            flask.abort(404, "No such user %s found" % new_username)
        try:
            old_main_admin = repo.user.user
            pagure.lib.set_project_owner(
                flask.g.session,
                repo,
                new_owner,
                required_groups=pagure_config.get("REQUIRED_GROUPS"),
            )
            # If the person doing the action is the former main admin, keep
            # them as admins
            if flask.g.fas_user.username == old_main_admin:
                pagure.lib.add_user_to_project(
                    flask.g.session,
                    repo,
                    new_user=flask.g.fas_user.username,
                    user=flask.g.fas_user.username,
                )
            flask.g.session.commit()
            pagure.lib.git.generate_gitolite_acls(project=repo)
            flask.flash(
                "The project has been transferred to %s" % new_username
            )
        except pagure.exceptions.PagureException as msg:
            flask.g.session.rollback()
            _log.debug(msg)
            flask.flash(str(msg), "error")
        except SQLAlchemyError:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(
                "Due to a database error, this project could not be "
                "transferred.",
                "error",
            )

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_repo",
            username=username,
            repo=repo.name,
            namespace=namespace,
        )
    )


@UI_NS.route("/<repo>/dowait/")
@UI_NS.route("/<repo>/dowait")
@UI_NS.route("/<namespace>/<repo>/dowait/")
@UI_NS.route("/<namespace>/<repo>/dowait")
@UI_NS.route("/fork/<username>/<repo>/dowait/")
@UI_NS.route("/fork/<username>/<repo>/dowait")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/dowait/")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/dowait")
def project_dowait(repo, username=None, namespace=None):
    """ Schedules a task that just waits 10 seconds for testing locking.

    This is not available unless ALLOW_PROJECT_DOWAIT is set to True, which
    should only ever be done in test instances.
    """
    if not pagure_config.get("ALLOW_PROJECT_DOWAIT", False):
        flask.abort(401, "No")

    task = pagure.lib.tasks.project_dowait.delay(
        name=repo, namespace=namespace, user=username
    )

    return pagure.utils.wait_for_task(task)


@UI_NS.route("/<repo>/stats/")
@UI_NS.route("/<repo>/stats")
@UI_NS.route("/<namespace>/<repo>/stats/")
@UI_NS.route("/<namespace>/<repo>/stats")
@UI_NS.route("/fork/<username>/<repo>/stats/")
@UI_NS.route("/fork/<username>/<repo>/stats")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/stats/")
@UI_NS.route("/fork/<username>/<namespace>/<repo>/stats")
def view_stats(repo, username=None, namespace=None):
    """ Displays some statistics about the specified repo.
    """
    return flask.render_template(
        "repo_stats.html", select="stats", username=username, repo=flask.g.repo
    )


@UI_NS.route("/<repo>/update/tags", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/update/tags", methods=["POST"])
@login_required
@is_repo_admin
@has_trackers
def update_tags(repo, username=None, namespace=None):
    """ Update the tags of a project.
    """

    repo = flask.g.repo

    form = pagure.forms.ConfirmationForm()

    error = False
    if form.validate_on_submit():
        # Uniquify and order preserving
        seen = set()
        tags = [
            tag.strip()
            for tag in flask.request.form.getlist("tag")
            if tag.strip()
            and tag.strip() not in seen  # noqa
            and not seen.add(tag.strip())
        ]

        tag_descriptions = [
            desc.strip()
            for desc in flask.request.form.getlist("tag_description")
        ]

        # Uniquify and order preserving
        colors = [
            col.strip()
            for col in flask.request.form.getlist("tag_color")
            if col.strip()
        ]

        pattern = re.compile(pagure.forms.TAGS_REGEX, re.IGNORECASE)
        for tag in tags:
            if not pattern.match(tag):
                flask.flash(
                    "Tag: %s contains one or more invalid characters" % tag,
                    "error",
                )
                error = True

        color_pattern = re.compile("^#\w{3,6}$")
        for color in colors:
            if not color_pattern.match(color):
                flask.flash(
                    "Color: %s does not match the expected pattern" % color,
                    "error",
                )
                error = True

        if not (len(tags) == len(colors) == len(tag_descriptions)):
            error = True
            # Store the lengths because we are going to use them a lot
            len_tags = len(tags)
            len_tag_descriptions = len(tag_descriptions)
            len_colors = len(colors)
            error_message = "Error: Incomplete request. "

            if len_colors > len_tags or len_tag_descriptions > len_tags:
                error_message += "One or more tag fields missing."
            elif len_colors < len_tags:
                error_message += "One or more tag color fields missing."
            elif len_tag_descriptions < len_tags:
                error_message += "One or more tag description fields missing."

            flask.flash(error_message, "error")

        if not error:
            known_tags = [tag.tag for tag in repo.tags_colored]
            for idx, tag in enumerate(tags):
                if tag in known_tags:
                    flask.flash("Duplicated tag: %s" % tag, "error")
                    break
                try:
                    pagure.lib.new_tag(
                        flask.g.session,
                        tag,
                        tag_descriptions[idx],
                        colors[idx],
                        repo.id,
                    )
                    flask.g.session.commit()
                    flask.flash("Tags updated")
                except SQLAlchemyError as err:  # pragma: no cover
                    flask.g.session.rollback()
                    flask.flash(str(err), "error")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            username=username,
            repo=repo.name,
            namespace=namespace,
        )
        + "#projecttags-tab"
    )


@UI_NS.route("/<repo>/droptag/", methods=["POST"])
@UI_NS.route("/<namespace>/<repo>/droptag/", methods=["POST"])
@UI_NS.route("/fork/<username>/<repo>/droptag/", methods=["POST"])
@UI_NS.route("/fork/<username>/<namespace>/<repo>/droptag/", methods=["POST"])
@login_required
@is_repo_admin
@has_trackers
def remove_tag(repo, username=None, namespace=None):
    """ Remove the specified tag, associated with the issues, from the project.
    """
    repo = flask.g.repo

    form = pagure.forms.DeleteIssueTagForm()
    if form.validate_on_submit():
        tags = form.tag.data
        tags = [tag.strip() for tag in tags.split(",")]

        msgs = pagure.lib.remove_tags(
            flask.g.session, repo, tags, user=flask.g.fas_user.username
        )

        try:
            flask.g.session.commit()
            for msg in msgs:
                flask.flash(msg)
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.error(err)
            flask.flash("Could not remove tag: %s" % ",".join(tags), "error")

    return flask.redirect(
        flask.url_for(
            "ui_ns.view_settings",
            repo=repo.name,
            username=username,
            namespace=repo.namespace,
        )
        + "#projecttags-tab"
    )


@UI_NS.route("/<repo>/tag/<tag>/edit/", methods=("GET", "POST"))
@UI_NS.route("/<repo>/tag/<tag>/edit", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/tag/<tag>/edit/", methods=("GET", "POST"))
@UI_NS.route("/<namespace>/<repo>/tag/<tag>/edit", methods=("GET", "POST"))
@UI_NS.route(
    "/fork/<username>/<repo>/tag/<tag>/edit/", methods=("GET", "POST")
)
@UI_NS.route("/fork/<username>/<repo>/tag/<tag>/edit", methods=("GET", "POST"))
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/tag/<tag>/edit/",
    methods=("GET", "POST"),
)
@UI_NS.route(
    "/fork/<username>/<namespace>/<repo>/tag/<tag>/edit",
    methods=("GET", "POST"),
)
@login_required
@is_repo_admin
@has_trackers
def edit_tag(repo, tag, username=None, namespace=None):
    """ Edit the specified tag associated with the issues of a project.
    """
    repo = flask.g.repo

    tags = pagure.lib.get_tags_of_project(flask.g.session, repo)
    if not tags:
        flask.abort(404, "Project has no tags to edit")

    # Check the tag exists, and get its old/original color
    tagobj = pagure.lib.get_colored_tag(flask.g.session, tag, repo.id)
    if not tagobj:
        flask.abort(404, "Tag %s not found in this project" % tag)

    form = pagure.forms.AddIssueTagForm()
    if form.validate_on_submit():
        new_tag = form.tag.data
        new_tag_description = form.tag_description.data
        new_tag_color = form.tag_color.data

        msgs = pagure.lib.edit_issue_tags(
            flask.g.session,
            repo,
            tagobj,
            new_tag,
            new_tag_description,
            new_tag_color,
            user=flask.g.fas_user.username,
        )

        try:
            flask.g.session.commit()
            for msg in msgs:
                flask.flash(msg)
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.error(err)
            flask.flash("Could not edit tag: %s" % tag, "error")

        return flask.redirect(
            flask.url_for(
                "ui_ns.view_settings",
                repo=repo.name,
                username=username,
                namespace=repo.namespace,
            )
            + "#projecttags-tab"
        )

    elif flask.request.method == "GET":
        tag_color = tagobj.tag_color
        if tag_color == "DeepSkyBlue":
            tag_color = "#00bfff"
        form.tag_color.data = tag_color
        form.tag_description.data = tagobj.tag_description
        form.tag.data = tag

    return flask.render_template(
        "edit_tag.html", username=username, repo=repo, form=form, tagname=tag
    )
