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
import random
import shutil
import string
import tempfile
import time
import uuid

import pygit2
import werkzeug

import progit
import progit.exceptions
import progit.lib
import progit.lib.notify
from progit.lib import model


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

        patch += """From %(commit)s Mon Sep 17 00:00:00 2001
From: %(author_name)s <%(author_email)s>
Date: %(date)s
Subject: %(subject)s

%(msg)s
---

%(patch)s
""" % (
            {
                'commit': commit.oid.hex,
                'author_name': commit.author.name,
                'author_email': commit.author.email,
                'date': datetime.datetime.utcfromtimestamp(
                    commit.commit_time).strftime('%b %d %Y %H:%M:%S +0000'),
                'subject': subject,
                'msg': message,
                'patch': diff.patch,
            }
        )
    return patch


def write_gitolite_acls(session, configfile):
    ''' Generate the configuration file for gitolite for all projects
    on the forge.
    '''
    config = []
    for project in session.query(model.Project).all():
        if project.parent_id:
            config.append('repo forks/%s' % project.fullname)
        else:
            config.append('repo %s' % project.fullname)
        config.append('  R   = @all')
        config.append('  RW+ = %s' % project.user.user)
        for user in project.users:
            if user != project.user:
                config.append('  RW+ = %s' % user.user)
        config.append('')

        config.append('repo docs/%s' % project.fullname)
        config.append('  R   = @all')
        config.append('  RW+ = %s' % project.user.user)
        for user in project.users:
            if user != project.user:
                config.append('  RW+ = %s' % user.user)
        config.append('')

        config.append('repo tickets/%s' % project.fullname)
        config.append('  R   = @all')
        config.append('  RW+ = %s' % project.user.user)
        for user in project.users:
            if user != project.user:
                config.append('  RW+ = %s' % user.user)
        config.append('')

    with open(configfile, 'w') as stream:
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
    ticket_repo = pygit2.Repository(repopath)

    # Clone the repo into a temp folder
    newpath = tempfile.mkdtemp()
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
        stream.write(obj.to_json())

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
    author = pygit2.Signature(name='progit', email='progit')

    # Actually commit
    sha = new_repo.create_commit(
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


def get_user_from_json(session, jsondata):
    """ From the given json blob, retrieve the user info and search for it
    in the db and create the user if it does not already exist.
    """
    user = None

    username = jsondata.get('user', {}).get('name')
    fullname = jsondata.get('user', {}).get('fullname')
    useremails = jsondata.get('user', {}).get('emails')
    user = progit.lib.search_user(session, username=username)
    if not user:
        for email in useremails:
            user = progit.lib.search_user(session, email=email)
            if user:
                break

    if not user:
        user = progit.lib.set_up_user(
            session=session,
            username=username,
            fullname=fullname or username,
            user_email=useremails[0],
        )
        session.commit()

    return user


def get_project_from_json(
        session, jsondata, gitfolder, docfolder, ticketfolder, requestfolder):
    """ From the given json blob, retrieve the project info and search for
    it in the db and create the projec if it does not already exist.
    """
    project = None


    user = get_user_from_json(session, jsondata)
    name = jsondata.get('name')
    project_user = None
    if jsondata.get('parent'):
        project_user = user.username
    project = progit.lib.get_project(session, name, user=project_user)


    if not project:
        parent = None
        if jsondata.get('parent'):
            parent = get_project_from_json(
                session, jsondata.get('parent'),
                gitfolder, docfolder, ticketfolder, requestfolder)

        progit.lib.new_project(
            session,
            user=user.username,
            name=name,
            description=jsondata.get('description'),
            parent_id=parent.id if parent else None,
            gitfolder=gitfolder,
            docfolder=docfolder,
            ticketfolder=ticketfolder,
            requestfolder=requestfolder,
        )

        session.commit()
        project = progit.lib.get_project(session, name, user=user.username)

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
    print json.dumps(json_data, sort_keys=True,
                     indent=4, separators=(',', ': '))

    repo = progit.lib.get_project(session, reponame, user=username)
    if not repo:
        raise progit.exceptions.ProgitException(
            'Unknown repo %s of username: %s' % (reponame, username))

    user = get_user_from_json(session, json_data)

    issue = progit.lib.get_issue_by_uid(session, issue_uid=issue_uid)
    if not issue:
        # Create new issue
        progit.lib.new_issue(
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
        progit.lib.edit_issue(
            session,
            issue=issue,
            ticketfolder=None,
            title=json_data.get('title'),
            content=json_data.get('content'),
            status=json_data.get('status'),
            private=json_data.get('private'),
        )
    session.commit()

    issue = progit.lib.get_issue_by_uid(session, issue_uid=issue_uid)

    # Update tags
    tags = json_data.get('tags', [])
    progit.lib.update_tags_issue(
        session, issue, tags, username=user.user, ticketfolder=None)

    # Update depends
    depends = json_data.get('depends', [])
    progit.lib.update_dependency_issue(
        session, issue.project, issue, depends,
        username=user.user, ticketfolder=None)

    # Update blocks
    blocks = json_data.get('blocks', [])
    progit.lib.update_blocked_issue(
        session, issue.project, issue, blocks,
        username=user.user, ticketfolder=None)

    for comment in json_data['comments']:
        user = get_user_from_json(session, comment)
        commentobj = progit.lib.get_issue_comment(
            session, issue_uid, comment['id'])
        if not commentobj:
            progit.lib.add_issue_comment(
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
        gitfolder, docfolder, ticketfolder, requestfolder):
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
    print json.dumps(json_data, sort_keys=True,
                     indent=4, separators=(',', ': '))

    repo = progit.lib.get_project(session, reponame, user=username)
    if not repo:
        raise progit.exceptions.ProgitException(
            'Unknown repo %s of username: %s' % (reponame, username))

    user = get_user_from_json(session, json_data)

    request = progit.lib.get_request_by_uid(
        session, request_uid=request_uid)

    if not request:
        repo_from = get_project_from_json(
            session, json_data.get('repo_from'),
            gitfolder, docfolder, ticketfolder, requestfolder
        )

        repo_to = get_project_from_json(
            session, json_data.get('repo'),
            gitfolder, docfolder, ticketfolder, requestfolder
        )

        # Create new request
        progit.lib.new_pull_request(
            session,
            repo_from=repo_from,
            branch_from=json_data.get('branch_from'),
            repo_to=repo_to,
            branch_to=json_data.get('branch'),
            title=json_data.get('title'),
            user=user.username,
            requestuid=json_data.get('uid'),
            requestid=json_data.get('id'),
            status= json_data.get('status'),
            requestfolder=None,
            notify=False,
        )
        session.commit()

    request = progit.lib.get_request_by_uid(
        session, request_uid=request_uid)

    for comment in json_data['comments']:
        user = get_user_from_json(session, comment)
        commentobj = progit.lib.get_request_comment(
            session, request_uid, comment['id'])
        if not commentobj:
            progit.lib.add_pull_request_comment(
                session,
                request,
                commit=comment['commit'],
                filename=comment['filename'],
                row=comment['line'],
                comment=comment['comment'],
                user=user.username,
                requestfolder=None,
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
    ticket_repo = pygit2.Repository(repopath)

    # Clone the repo into a temp folder
    newpath = tempfile.mkdtemp()
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
    sha = new_repo.create_commit(
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
