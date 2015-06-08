# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


import datetime
import hashlib
import json
import os
import shutil
import subprocess
import tempfile

import pygit2
import werkzeug

from sqlalchemy.exc import SQLAlchemyError

import pagure
import pagure.exceptions
import pagure.lib
import pagure.lib.notify
from pagure.lib import model

# pylint: disable=R0913,E1101,R0914


def commit_to_patch(repo_obj, commits):
    ''' For a given commit (PyGit2 commit object) of a specified git repo,
    returns a string representation of the changes the commit did in a
    format that allows it to be used as patch.
    '''
    if not isinstance(commits, list):
        commits = [commits]

    patch = ""
    for cnt, commit in enumerate(commits):
        if commit.parents:
            diff = commit.tree.diff_to_tree()

            parent = repo_obj.revparse_single('%s^' % commit.oid.hex)
            diff = repo_obj.diff(parent, commit)
        else:
            # First commit in the repo
            diff = commit.tree.diff_to_tree(swap=True)

        subject = message = ''
        if '\n' in commit.message:
            subject, message = commit.message.split('\n', 1)
        else:
            subject = commit.message

        if len(commits) > 1:
            subject = '[PATCH %s/%s] %s' % (cnt + 1, len(commits), subject)

        patch += u"""From {commit} Mon Sep 17 00:00:00 2001
From: {author_name} <{author_email}>
Date: {date}
Subject: {subject}

{msg}
---

{patch}
""".format(commit=commit.oid.hex,
           author_name=commit.author.name,
           author_email=commit.author.email,
           date=datetime.datetime.utcfromtimestamp(
               commit.commit_time).strftime('%b %d %Y %H:%M:%S +0000'),
           subject=subject,
           msg=message,
           patch=diff.patch)
    return patch


def write_gitolite_acls(session, configfile):
    ''' Generate the configuration file for gitolite for all projects
    on the forge.
    '''
    config = []
    groups = {}
    for project in session.query(model.Project).all():
        for group in project.groups:
            if group.group_name not in groups:
                groups[group.group_name] = [
                    user.username for user in group.users]

        for repos in ['repos', 'docs/', 'tickets/', 'requests/']:
            if repos == 'repos':
                if project.parent_id:
                    repos = 'forks/'
                else:
                    repos = ''

            config.append('repo %s%s' % (repos, project.fullname))
            config.append('  R   = @all')
            if project.groups:
                config.append('  RW+ = @%s' % ' @'.join([
                    group.group_name for group in project.groups]))
            config.append('  RW+ = %s' % project.user.user)
            for user in project.users:
                if user != project.user:
                    config.append('  RW+ = %s' % user.user)
            config.append('')

    with open(configfile, 'w') as stream:
        for key, users in groups.iteritems():
            stream.write('@%s   = %s\n' % (key, ' '.join(users)))
        stream.write('\n')

        for row in config:
            stream.write(row + '\n')


def update_git(obj, repo, repofolder, objtype='ticket'):
    """ Update the given issue in its git.

    This method forks the provided repo, add/edit the issue whose file name
    is defined by the uid field of the issue and if there are additions/
    changes commit them and push them back to the original repo.

    """

    if not repofolder:
        return

    # Get the fork
    repopath = os.path.join(repofolder, repo.path)

    # Clone the repo into a temp folder
    newpath = tempfile.mkdtemp(prefix='pagure-')
    new_repo = pygit2.clone_repository(repopath, newpath)

    file_path = os.path.join(newpath, obj.uid)

    # Get the current index
    index = new_repo.index

    # Are we adding files
    added = False
    if not os.path.exists(file_path):
        added = True

    # Write down what changed
    with open(file_path, 'w') as stream:
        stream.write(json.dumps(obj.to_json()))

    # Retrieve the list of files that changed
    diff = new_repo.diff()
    files = [patch.new_file_path for patch in diff]

    # Add the changes to the index
    if added:
        index.add(obj.uid)
    for filename in files:
        index.add(filename)

    # If not change, return
    if not files and not added:
        shutil.rmtree(newpath)
        return

    # See if there is a parent to this commit
    parent = None
    try:
        parent = new_repo.head.get_object().oid
    except pygit2.GitError:
        pass

    parents = []
    if parent:
        parents.append(parent)

    # Author/commiter will always be this one
    author = pygit2.Signature(name='pagure', email='pagure')

    # Actually commit
    new_repo.create_commit(
        'refs/heads/master',
        author,
        author,
        'Updated %s %s: %s' % (objtype, obj.uid, obj.title),
        new_repo.index.write_tree(),
        parents)
    index.write()

    # Push to origin
    ori_remote = new_repo.remotes[0]
    master_ref = new_repo.lookup_reference('HEAD').resolve()
    refname = '%s:%s' % (master_ref.name, master_ref.name)

    ori_remote.push(refname)

    # Remove the clone
    shutil.rmtree(newpath)


def clean_git(obj, repo, repofolder, objtype='ticket'):
    """ Update the given issue remove it from its git.

    """

    if not repofolder:
        return

    # Get the fork
    repopath = os.path.join(repofolder, repo.path)

    # Clone the repo into a temp folder
    newpath = tempfile.mkdtemp(prefix='pagure-')
    new_repo = pygit2.clone_repository(repopath, newpath)

    file_path = os.path.join(newpath, obj.uid)

    # Get the current index
    index = new_repo.index

    # Are we adding files
    if not os.path.exists(file_path):
        shutil.rmtree(newpath)
        return

    # Remove the file
    os.unlink(file_path)

    diff = new_repo.diff()

    # Add the changes to the index
    index.remove(obj.uid)

    # See if there is a parent to this commit
    parent = None
    try:
        parent = new_repo.head.get_object().oid
    except pygit2.GitError:
        pass

    parents = []
    if parent:
        parents.append(parent)

    # Author/commiter will always be this one
    author = pygit2.Signature(name='pagure', email='pagure')

    # Actually commit
    new_repo.create_commit(
        'refs/heads/master',
        author,
        author,
        'Removed %s %s: %s' % (objtype, obj.uid, obj.title),
        new_repo.index.write_tree(),
        parents)
    index.write()

    # Push to origin
    ori_remote = new_repo.remotes[0]
    master_ref = new_repo.lookup_reference('HEAD').resolve()
    refname = '%s:%s' % (master_ref.name, master_ref.name)

    ori_remote.push(refname)

    # Remove the clone
    shutil.rmtree(newpath)


def get_user_from_json(session, jsondata, key='user'):
    """ From the given json blob, retrieve the user info and search for it
    in the db and create the user if it does not already exist.
    """
    user = None

    username = fullname = useremails = default_email = None

    data = jsondata.get(key, None)

    if data:
        username = data.get('name')
        fullname = data.get('fullname')
        useremails = data.get('emails')
        default_email = data.get('default_email')

    if not default_email and useremails:
        default_email = useremails[0]

    if not username and not useremails:
        return

    user = pagure.lib.search_user(session, username=username)
    if not user:
        for email in useremails:
            user = pagure.lib.search_user(session, email=email)
            if user:
                break

    if not user:
        user = pagure.lib.set_up_user(
            session=session,
            username=username,
            fullname=fullname or username,
            default_email=default_email,
            emails=useremails,
        )
        session.commit()

    return user


def get_project_from_json(
        session, jsondata,
        gitfolder, forkfolder, docfolder, ticketfolder, requestfolder):
    """ From the given json blob, retrieve the project info and search for
    it in the db and create the projec if it does not already exist.
    """
    project = None

    user = get_user_from_json(session, jsondata)
    name = jsondata.get('name')
    project_user = None
    if jsondata.get('parent'):
        project_user = user.username
    project = pagure.lib.get_project(session, name, user=project_user)

    if not project:
        parent = None
        if jsondata.get('parent'):
            parent = get_project_from_json(
                session, jsondata.get('parent'),
                gitfolder, forkfolder, docfolder, ticketfolder, requestfolder)

            pagure.lib.fork_project(
                session=session,
                repo=parent,
                gitfolder=pagure.APP.config['GIT_FOLDER'],
                forkfolder=pagure.APP.config['FORK_FOLDER'],
                docfolder=pagure.APP.config['DOCS_FOLDER'],
                ticketfolder=pagure.APP.config['TICKETS_FOLDER'],
                requestfolder=pagure.APP.config['REQUESTS_FOLDER'],
                user=user.username)

        else:
            pagure.lib.new_project(
                session,
                user=user.username,
                name=name,
                description=jsondata.get('description'),
                parent_id=parent.id if parent else None,
                blacklist=pagure.APP.config.get('BLACKLISTED_PROJECTS', []),
                gitfolder=forkfolder if parent else gitfolder,
                docfolder=docfolder,
                ticketfolder=ticketfolder,
                requestfolder=requestfolder,
            )

        session.commit()
        project = pagure.lib.get_project(session, name, user=user.username)

    return project


def update_ticket_from_git(
        session, reponame, username, issue_uid, json_data):
    """ Update the specified issue (identified by its unique identifier)
    with the data present in the json blob provided.

    :arg session: the session to connect to the database with.
    :arg repo: the name of the project to update
    :arg issue_uid: the unique identifier of the issue to update
    :arg json_data: the json representation of the issue taken from the git
        and used to update the data in the database.

    """

    repo = pagure.lib.get_project(session, reponame, user=username)
    if not repo:
        raise pagure.exceptions.PagureException(
            'Unknown repo %s of username: %s' % (reponame, username))

    user = get_user_from_json(session, json_data)

    issue = pagure.lib.get_issue_by_uid(session, issue_uid=issue_uid)
    if not issue:
        # Create new issue
        pagure.lib.new_issue(
            session,
            repo=repo,
            title=json_data.get('title'),
            content=json_data.get('content'),
            user=user.username,
            ticketfolder=None,
            issue_id=json_data.get('id'),
            issue_uid=issue_uid,
            private=json_data.get('private'),
            status=json_data.get('status'),
            notify=False,
        )

    else:
        # Edit existing issue
        pagure.lib.edit_issue(
            session,
            issue=issue,
            ticketfolder=None,
            user=user.username,
            title=json_data.get('title'),
            content=json_data.get('content'),
            status=json_data.get('status'),
            private=json_data.get('private'),
        )
    session.commit()

    issue = pagure.lib.get_issue_by_uid(session, issue_uid=issue_uid)

    # Update tags
    tags = json_data.get('tags', [])
    pagure.lib.update_tags_issue(
        session, issue, tags, username=user.user, ticketfolder=None)

    # Update assignee
    assignee = get_user_from_json(session, json_data, key='assignee')
    if assignee:
        pagure.lib.add_issue_assignee(
            session, issue, assignee.username,
            user=user.user, ticketfolder=None)

    # Update depends
    depends = json_data.get('depends', [])
    pagure.lib.update_dependency_issue(
        session, issue.project, issue, depends,
        username=user.user, ticketfolder=None)

    # Update blocks
    blocks = json_data.get('blocks', [])
    pagure.lib.update_blocked_issue(
        session, issue.project, issue, blocks,
        username=user.user, ticketfolder=None)

    for comment in json_data['comments']:
        user = get_user_from_json(session, comment)
        commentobj = pagure.lib.get_issue_comment(
            session, issue_uid, comment['id'])
        if not commentobj:
            pagure.lib.add_issue_comment(
                session,
                issue=issue,
                comment=comment['comment'],
                user=user.username,
                ticketfolder=None,
                notify=False,
            )
    session.commit()


def update_request_from_git(
        session, reponame, username, request_uid, json_data,
        gitfolder, forkfolder, docfolder, ticketfolder, requestfolder):
    """ Update the specified request (identified by its unique identifier)
    with the data present in the json blob provided.

    :arg session: the session to connect to the database with.
    :arg repo: the name of the project to update
    :arg username: the username to find the repo, is not None for forked
        projects
    :arg request_uid: the unique identifier of the issue to update
    :arg json_data: the json representation of the issue taken from the git
        and used to update the data in the database.

    """

    repo = pagure.lib.get_project(session, reponame, user=username)
    if not repo:
        raise pagure.exceptions.PagureException(
            'Unknown repo %s of username: %s' % (reponame, username))

    user = get_user_from_json(session, json_data)

    request = pagure.lib.get_request_by_uid(
        session, request_uid=request_uid)

    if not request:
        repo_from = get_project_from_json(
            session, json_data.get('repo_from'),
            gitfolder, forkfolder, docfolder, ticketfolder, requestfolder
        )

        repo_to = get_project_from_json(
            session, json_data.get('project'),
            gitfolder, forkfolder, docfolder, ticketfolder, requestfolder
        )

        # Create new request
        pagure.lib.new_pull_request(
            session,
            repo_from=repo_from,
            branch_from=json_data.get('branch_from'),
            repo_to=repo_to,
            branch_to=json_data.get('branch'),
            title=json_data.get('title'),
            user=user.username,
            requestuid=json_data.get('uid'),
            requestid=json_data.get('id'),
            status=json_data.get('status'),
            requestfolder=None,
            notify=False,
        )
        session.commit()

    request = pagure.lib.get_request_by_uid(
        session, request_uid=request_uid)

    # Update start and stop commits
    request.commit_start = json_data.get('commit_start')
    request.commit_stop = json_data.get('commit_stop')

    # Update assignee
    assignee = get_user_from_json(session, json_data, key='assignee')
    if assignee:
        pagure.lib.add_pull_request_assignee(
            session, request, assignee.username,
            user=user.user, requestfolder=None)

    for comment in json_data['comments']:
        user = get_user_from_json(session, comment)
        commentobj = pagure.lib.get_request_comment(
            session, request_uid, comment['id'])
        if not commentobj:
            pagure.lib.add_pull_request_comment(
                session,
                request,
                commit=comment['commit'],
                filename=comment['filename'],
                row=comment['line'],
                comment=comment['comment'],
                user=user.username,
                requestfolder=None,
                notify=False,
            )
    session.commit()


def add_file_to_git(repo, issue, ticketfolder, user, filename, filestream):
    ''' Add a given file to the specified ticket git repository.

    :arg repo: the Project object from the database
    :arg ticketfolder: the folder on the filesystem where the git repo for
        tickets are stored
    :arg user: the user object with its username and email
    :arg filename: the name of the file to save
    :arg filestream: the actual content of the file

    '''

    if not ticketfolder:
        return

    # Prefix the filename with a timestamp:
    filename = '%s-%s' % (
        hashlib.sha256(filestream.read()).hexdigest(),
        werkzeug.secure_filename(filename)
    )

    # Get the fork
    repopath = os.path.join(ticketfolder, repo.path)

    # Clone the repo into a temp folder
    newpath = tempfile.mkdtemp(prefix='pagure-')
    new_repo = pygit2.clone_repository(repopath, newpath)

    folder_path = os.path.join(newpath, 'files')
    file_path = os.path.join(folder_path, filename)

    # Get the current index
    index = new_repo.index

    # Are we adding files
    added = False
    if not os.path.exists(file_path):
        added = True
    else:
        # File exists, remove the clone and return
        shutil.rmtree(newpath)
        return os.path.join('files', filename)

    if not os.path.exists(folder_path):
        os.mkdir(folder_path)

    # Write down what changed
    filestream.seek(0)
    with open(file_path, 'w') as stream:
        stream.write(filestream.read())

    # Retrieve the list of files that changed
    diff = new_repo.diff()
    files = [patch.new_file_path for patch in diff]

    # Add the changes to the index
    if added:
        index.add(os.path.join('files', filename))
    for filename in files:
        index.add(filename)

    # If not change, return
    if not files and not added:
        shutil.rmtree(newpath)
        return

    # See if there is a parent to this commit
    parent = None
    try:
        parent = new_repo.head.get_object().oid
    except pygit2.GitError:
        pass

    parents = []
    if parent:
        parents.append(parent)

    # Author/commiter will always be this one
    author = pygit2.Signature(
        name=user.username,
        email=user.email
    )

    # Actually commit
    new_repo.create_commit(
        'refs/heads/master',
        author,
        author,
        'Add file %s to ticket %s: %s' % (filename, issue.uid, issue.title),
        new_repo.index.write_tree(),
        parents)
    index.write()

    # Push to origin
    ori_remote = new_repo.remotes[0]
    master_ref = new_repo.lookup_reference('HEAD').resolve()
    refname = '%s:%s' % (master_ref.name, master_ref.name)

    ori_remote.push(refname)

    # Remove the clone
    shutil.rmtree(newpath)

    return os.path.join('files', filename)


def update_file_in_git(repo, branch, filename, content, message, user, email):
    ''' Update a specific file in the specified repository with the content
    given and commit the change under the user's name.

    :arg repo: the Project object from the database
    :arg filename: the name of the file to save
    :arg content: the new content of the file
    :arg message: the message of the git commit
    :arg user: the user object with its username and email

    '''

    # Get the fork
    repopath = pagure.get_repo_path(repo)

    # Clone the repo into a temp folder
    newpath = tempfile.mkdtemp(prefix='pagure-')
    new_repo = pygit2.clone_repository(repopath, newpath)

    file_path = os.path.join(newpath, filename)

    # Get the current index
    index = new_repo.index

    # Write down what changed
    with open(file_path, 'w') as stream:
        stream.write(content.replace('\r', ''))

    # Retrieve the list of files that changed
    diff = new_repo.diff()
    files = [patch.new_file_path for patch in diff]

    # Add the changes to the index
    added = False
    for filename in files:
        added = True
        index.add(filename)

    # If not change, return
    if not files and not added:
        shutil.rmtree(newpath)
        return

    # See if there is a parent to this commit
    branch_ref = get_branch_ref(new_repo, branch)
    parent = branch_ref.get_object()

    parents = []
    if parent:
        parents.append(parent.hex)

    # Author/commiter will always be this one
    author = pygit2.Signature(
        name=user.username,
        email=email
    )

    # Actually commit
    new_repo.create_commit(
        branch_ref.name,
        author,
        author,
        message.strip(),
        new_repo.index.write_tree(),
        parents)
    index.write()

    # Push to origin
    ori_remote = new_repo.remotes[0]
    refname = '%s:refs/heads/%s' % (branch_ref.name, branch)

    ori_remote.push(refname)

    # Remove the clone
    shutil.rmtree(newpath)

    return os.path.join('files', filename)


def read_output(cmd, abspath, input=None, keepends=False, **kw):
    """ Read the output from the given command to run """
    if input:
        stdin = subprocess.PIPE
    else:
        stdin = None
    p = subprocess.Popen(
        cmd,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=abspath,
        **kw)
    (out, err) = p.communicate(input)
    retcode = p.wait()
    if retcode:
        print 'ERROR: %s =-- %s' % (cmd, retcode)
        print out
        print err
    if not keepends:
        out = out.rstrip('\n\r')
    return out


def read_git_output(args, abspath, input=None, keepends=False, **kw):
    """Read the output of a Git command."""

    return read_output(
        ['git'] + args, abspath, input=input, keepends=keepends, **kw)


def read_git_lines(args, abspath, keepends=False, **kw):
    """Return the lines output by Git command.

    Return as single lines, with newlines stripped off."""

    return read_git_output(
        args, abspath, keepends=keepends, **kw
    ).splitlines(keepends)


def get_revs_between(torev, fromrev, abspath):
    """ Yield revisions between HEAD and BASE. """

    cmd = ['rev-list', '%s...%s' % (torev, fromrev)]
    if set(fromrev) == set('0'):
        cmd = ['rev-list', '%s' % torev]
    return pagure.lib.git.read_git_lines(cmd, abspath)


def get_pusher(commit, abspath):
    ''' Return the name of the person that pushed the commit. '''
    user = pagure.lib.git.read_git_lines(
        ['log', '-1', '--pretty=format:"%an"', commit],
        abspath)[0].replace('"', '')
    return user


def get_pusher_email(commit, abspath):
    ''' Return the email of the person that pushed the commit. '''
    user = pagure.lib.git.read_git_lines(
        ['log', '-1', '--pretty=format:"%ae"', commit],
        abspath)[0].replace('"', '')
    return user


def get_repo_name(abspath):
    ''' Return the name of the git repo based on its path.
    '''
    repo_name = '.'.join(abspath.split(os.path.sep)[-1].split('.')[:-1])
    return repo_name


def get_username(abspath):
    ''' Return the username of the git repo based on its path.
    '''
    username = None
    repo = os.path.abspath(os.path.join(abspath, '..'))
    if pagure.APP.config['FORK_FOLDER'] in repo:
        username = repo.split(pagure.APP.config['FORK_FOLDER'])[1]
        if username.startswith('/'):
            username = username[1:]
    return username


def get_branch_ref(repo, branchname):
    ''' Return the reference to the specified branch or raises an exception.
    '''
    location = pygit2.GIT_BRANCH_LOCAL
    if branchname not in repo.listall_branches():
        branchname = 'origin/%s' % branchname
        location = pygit2.GIT_BRANCH_REMOTE
    branch_ref = repo.lookup_branch(branchname, location).resolve()

    if not branch_ref:
        raise pagure.exceptions.PagureException(
            'No refs found for %s' % branchname)
    return branch_ref


def merge_pull_request(
        session, request, username, request_folder, domerge=True):
    ''' Merge the specified pull-request.
    '''
    # Get the fork
    repopath = pagure.get_repo_path(request.project_from)
    fork_obj = pygit2.Repository(repopath)

    # Get the original repo
    parentpath = pagure.get_repo_path(request.project)

    # Clone the original repo into a temp folder
    newpath = tempfile.mkdtemp(prefix='pagure-pr-merge')
    new_repo = pygit2.clone_repository(parentpath, newpath)

    # Update the start and stop commits in the DB, one last time
    diff_commits = diff_pull_request(
        session, request, pygit2.Repository(parentpath), fork_obj,
        requestfolder=request_folder, with_diff=False)[0]

    if request.project.settings.get(
            'Enforce_signed-off_commits_in_pull-request', False):
        for commit in diff_commits:
            if not 'signed-off-by' in commit.message.lower():
                raise pagure.exceptions.PagureException(
                    'This repo enforces that all commits are '
                    'signed off by their author. ')

    # Checkout the correct branch
    branch_ref = get_branch_ref(new_repo, request.branch)
    if not branch_ref:
        shutil.rmtree(newpath)
        raise pagure.exceptions.BranchNotFoundException(
            'Branch %s could not be found in the repo %s' % (
                request.branch, request.project.fullname
            ))

    new_repo.checkout(branch_ref)

    branch = get_branch_ref(fork_obj, request.branch_from)
    if not branch:
        shutil.rmtree(newpath)
        raise pagure.exceptions.BranchNotFoundException(
            'Branch %s could not be found in the repo %s' % (
                request.branch_from, request.project_from.fullname
            ))

    repo_commit = fork_obj[branch.get_object().hex]

    ori_remote = new_repo.remotes[0]
    # Add the fork as remote repo
    reponame = '%s_%s' % (request.user.user, request.project_from.name)
    remote = new_repo.create_remote(reponame, repopath)

    # Fetch the commits
    remote.fetch()

    merge = new_repo.merge(repo_commit.oid)
    if merge is None:
        mergecode = new_repo.merge_analysis(repo_commit.oid)[0]

    refname = '%s:refs/heads/%s' % (branch_ref.name, request.branch)
    if (
            (merge is not None and merge.is_uptodate)
            or
            (merge is None and
             mergecode & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE)):

        if domerge:
            pagure.lib.close_pull_request(
                session, request, username,
                requestfolder=request_folder)
            try:
                session.commit()
            except SQLAlchemyError as err:  # pragma: no cover
                session.rollback()
                pagure.APP.logger.exception(err)
                shutil.rmtree(newpath)
                raise pagure.exceptions.PagureException(
                    'Could not close this pull-request')
            raise pagure.exceptions.PagureException(
                'Nothing to do, changes were already merged')
        else:
            request.merge_status = 'NO_CHANGE'
            session.commit()
            return 'NO_CHANGE'

    elif (
            (merge is not None and merge.is_fastforward)
            or
            (merge is None and
             mergecode & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD)):

        if domerge:
            if merge is not None:
                # This is depending on the pygit2 version
                branch_ref.target = merge.fastforward_oid
            elif merge is None and mergecode is not None:
                branch_ref.set_target(repo_commit.oid.hex)

            ori_remote.push(refname)
        else:
            request.merge_status = 'FFORWARD'
            session.commit()
            return 'FFORWARD'

    else:
        tree = None
        try:
            tree = new_repo.index.write_tree()
        except pygit2.GitError:
            shutil.rmtree(newpath)
            if domerge:
                raise pagure.exceptions.PagureException('Merge conflicts!')
            else:
                request.merge_status = 'CONFLICTS'
                session.commit()
                return 'CONFLICTS'

        if not domerge:
            request.merge_status = 'MERGE'
            session.commit()
            return 'MERGE'

        head = new_repo.lookup_reference('HEAD').get_object()
        new_repo.create_commit(
            'refs/heads/%s' % request.branch,
            repo_commit.author,
            repo_commit.committer,
            'Merge #%s `%s`' % (request.id, request.title),
            tree,
            [head.hex, repo_commit.oid.hex])
        ori_remote.push(refname)

    # Update status
    pagure.lib.close_pull_request(
        session, request, username,
        requestfolder=request_folder,
    )
    try:
        session.commit()
    except SQLAlchemyError as err:  # pragma: no cover
        session.rollback()
        pagure.APP.logger.exception(err)
        shutil.rmtree(newpath)
        raise pagure.exceptions.PagureException(
            'Could not update this pull-request in the database')
    shutil.rmtree(newpath)

    return 'Changes merged!'


def diff_pull_request(
        session, request, repo_obj, orig_repo, requestfolder,
        with_diff=True):
    """ Returns the diff and the list of commits between the two git repos
    mentionned in the given pull-request.
    """

    commitid = None
    diff = None
    diff_commits = []
    branch = repo_obj.lookup_branch(request.branch_from)
    if branch:
        commitid = branch.get_object().hex

    if not repo_obj.is_empty and not orig_repo.is_empty:
        # Pull-request open
        master_commits = [
            commit.oid.hex
            for commit in orig_repo.walk(
                orig_repo.lookup_branch(request.branch).get_object().hex,
                pygit2.GIT_SORT_TIME)
        ]
        for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
            if request.status and commit.oid.hex in master_commits:
                break
            diff_commits.append(commit)

        if request.status and diff_commits:
            first_commit = repo_obj[diff_commits[-1].oid.hex]
            # Check if we can still rely on the merge_status
            if request.commit_start != first_commit.oid.hex or\
                    request.commit_stop != diff_commits[0].oid.hex:
                request.merge_status = None
            request.commit_start = first_commit.oid.hex
            request.commit_stop = diff_commits[0].oid.hex
            session.add(request)
            session.commit()
            pagure.lib.git.update_git(
                request, repo=request.project,
                repofolder=requestfolder)

        if diff_commits and with_diff:
            diff = repo_obj.diff(
                repo_obj.revparse_single(diff_commits[-1].parents[0].oid.hex),
                repo_obj.revparse_single(diff_commits[0].oid.hex)
            )

    elif orig_repo.is_empty and not repo_obj.is_empty:
        for commit in repo_obj.walk(commitid, pygit2.GIT_SORT_TIME):
            diff_commits.append(commit)
        if request.status and diff_commits:
            first_commit = repo_obj[diff_commits[-1].oid.hex]
            # Check if we can still rely on the merge_status
            if request.commit_start != first_commit.oid.hex or\
                    request.commit_stop != diff_commits[0].oid.hex:
                request.merge_status = None
            request.commit_start = first_commit.oid.hex
            request.commit_stop = diff_commits[0].oid.hex
            session.add(request)
            session.commit()
            pagure.lib.git.update_git(
                request, repo=request.project,
                repofolder=requestfolder)

        repo_commit = repo_obj[request.commit_stop]
        if with_diff:
            diff = repo_commit.tree.diff_to_tree(swap=True)
    else:
        raise pagure.exceptions.PagureException(
            'Fork is empty, there are no commits to request pulling')

    return (diff_commits, diff)


def get_git_tags(project):
    """ Returns the list of tags created in the git repositorie of the
    specified project.
    """
    repopath = pagure.get_repo_path(project)
    repo_obj = pygit2.Repository(repopath)
    tags = [
        tag.split('refs/tags/')[1]
        for tag in repo_obj.listall_references()
        if 'refs/tags/' in tag
    ]
    return tags


def get_git_tags_objects(project):
    """ Returns the list of references of the tags created in the git
    repositorie the specified project.
    """
    repopath = pagure.get_repo_path(project)
    repo_obj = pygit2.Repository(repopath)
    tags = [
        repo_obj.lookup_reference(tag)
        for tag in repo_obj.listall_references()
        if 'refs/tags/' in tag
    ]
    return tags
