#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import flask
import os
import tempfile
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
from progit import APP, SESSION, LOG, __get_file_in_tree


### Application
def view_repo(repo, username=None):
    """ Front page of a specific repo.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404)

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


def view_repo_branch(repo, branchname, username=None):
    """ Displays the information about a specific branch.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        reponame = os.path.join(APP.config['FORK_FOLDER'], repo.path)
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


def view_log(repo, branchname=None, username=None):
    """ Displays the logs of the specified repo.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        reponame = os.path.join(APP.config['FORK_FOLDER'], repo.path)
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
    if username:
        origin = 'view_fork_log'

    return flask.render_template(
        'repo_info.html',
        select='logs',
        origin=origin,
        repo=repo,
        username=username,
        branches=sorted(repo_obj.listall_branches()),
        branchname=branchname,
        last_commits=last_commits,
        diff_commits=diff_commits,
        page=page,
        total_page=total_page,
    )


def view_file(repo, identifier, filename, username=None):
    """ Displays the content of a file or a tree for the specified repo.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

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


def view_commit(repo, commitid, username=None):
    """ Render a commit in a repo
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404)

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo.path)
    if repo.is_fork:
        reponame = os.path.join(APP.config['FORK_FOLDER'], repo.path)
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


def view_tree(repo, identifier=None, username=None):
    """ Render the tree of the repo
    """
    repo = progit.lib.get_project(SESSION, repo)

    if repo is None:
        flask.abort(404)

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


def view_issues(repo, username=None):
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


def new_issue(repo, username=None):
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


def view_issue(repo, issueid, username=None):
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
        username=username,
        issue=issue,
    )


def edit_issue(repo, issueid, username=None):
    """ Edit the specified issue
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if repo is None:
        flask.abort(404, 'Project not found')

    issue = progit.lib.get_issue(SESSION, issueid)

    if issue is None:
        flask.abort(404, 'Issue not found')

    status = progit.lib.get_issue_statuses(SESSION)
    form = progit.forms.IssueForm(status=status)
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        status = form.status.data

        try:
            message = progit.lib.edit_issue(
                SESSION,
                issue=issue,
                title=title,
                content=content,
                status=status,
            )
            SESSION.commit()
            flask.flash(message)
            url = flask.url_for('view_issues', repo=repo.name)
            if username:
                url = flask.url_for(
                    'view_fork_issues', username=username, repo=repo.name)
            return flask.redirect(url)
        except progit.exceptions.ProgitException, err:
            flask.flash(str(err), 'error')
        except SQLAlchemyError, err:  # pragma: no cover
            SESSION.rollback()
            flask.flash(str(err), 'error')
    elif flask.request.method == 'GET':
        form.title.data = issue.title
        form.content.data = issue.content
        form.status.data = issue.status

    return flask.render_template(
        'new_issue.html',
        select='issues',
        type='edit',
        form=form,
        repo=repo,
        username=username,
        issue=issue,
    )


def request_pulls(repo, username=None):
    """ Returns the list of pull-requests opened on a project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    requests = progit.lib.get_pull_requests(
        SESSION, project_id=repo.id, status=True)

    return flask.render_template(
        'requests.html',
        select='requests',
        repo=repo,
        username=username,
        requests=requests,
    )


def request_pull(repo, requestid, username=None):
    """ Request pulling the changes from the fork into the project.
    """
    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    request = progit.lib.get_pull_request(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    repopath = os.path.join(
        APP.config['FORK_FOLDER'], request.repo_from.path)
    repo_obj = pygit2.Repository(repopath)

    parentname = os.path.join(
        APP.config['GIT_FOLDER'], request.repo.path)
    orig_repo = pygit2.Repository(parentname)

    diff_commits = []
    diffs = []
    repo_commit = repo_obj[request.stop_id]
    if not repo_obj.is_empty and not orig_repo.is_empty:
        orig_commit = orig_repo[request.start_id]

        for commit in repo_obj.walk(request.stop_id, pygit2.GIT_SORT_TIME):
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

    return flask.render_template(
        'pull_request.html',
        select='requests',
        repo=repo,
        username=username or request.user,
        request=request,
        repo_obj=repo_obj,
        orig_repo=orig_repo,
        diff_commits=diff_commits,
        diffs=diffs,
        html_diffs=html_diffs,
    )


def merge_request_pull(repo, requestid, username=None):
    """ Merge a request pulling the changes from the fork into the project.
    """

    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    request = progit.lib.get_pull_request(
        SESSION, project_id=repo.id, requestid=requestid)

    if not request:
        flask.abort(404, 'Pull-request not found')

    error_output = flask.url_for(
        'request_pull', repo=repo.name, requestid=requestid)
    if username:
        error_output = flask.url_for(
            'fork_request_pull',
            repo=repo.name,
            requestid=requestid,
            username=username)

    # Get the fork
    repopath = os.path.join(
        APP.config['FORK_FOLDER'], request.repo_from.path)
    fork_obj = pygit2.Repository(repopath)

    # Get the original repo
    parentpath = os.path.join(APP.config['GIT_FOLDER'], request.repo.path)
    orig_repo = pygit2.Repository(parentpath)

    if orig_repo.get(request.stop_id, None):
        flask.flash('These chanages have already been merged.', 'error')
        # Update status
        progit.lib.close_pull_request(SESSION, request)
        SESSION.commit()
        return flask.redirect(error_output)

    # Clone the original repo into a temp folder
    newpath = tempfile.mkdtemp()
    new_repo = pygit2.clone_repository(parentpath, newpath)

    repo_commit = fork_obj[request.stop_id]

    ori_remote = new_repo.remotes[0]
    # Add the fork as remote repo
    reponame = '%s_%s' % (request.user, repo.name)
    remote = new_repo.create_remote(reponame, repopath)

    # Fetch the commits
    remote.fetch()

    merge = new_repo.merge(repo_commit.oid)
    master_ref = new_repo.lookup_reference('HEAD').resolve()

    if merge.is_fastforward:
        master_ref.target = merge.fastforward_oid
        refname = '%s:%s' % (master_ref.name, master_ref.name)
        ori_remote.push(refname)
        flask.flash('Changes merged!')
    else:
        flask.flash(
            'This merge is not fast-forward and cannot be applied via '
            'progit', 'error')
        flask.redirect(error_output)

    # Update status
    progit.lib.close_pull_request(SESSION, request)
    SESSION.commit()

    return flask.redirect(flask.url_for('view_repo', repo=repo.name))


def view_forks(repo, username=None):
    """ Return the list of forks of a project.
    """

    repo = progit.lib.get_project(SESSION, repo, user=username)

    if not repo:
        flask.abort(404, 'Project not found')

    return flask.render_template(
        'forks.html',
        select='forks',
        repo=repo,
    )
