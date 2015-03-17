# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


import datetime
import json
import os
import random
import shutil
import string
import tempfile
import uuid

import pygit2

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


def update_git_ticket(issue, repo, ticketfolder):
    """ Update the given issue in its git.

    This method forks the provided repo, add/edit the issue whose file name
    is defined by the uid field of the issue and if there are additions/
    changes commit them and push them back to the original repo.

    """

    if not ticketfolder:
        return

    # Get the fork
    repopath = os.path.join(ticketfolder, repo.path)
    ticket_repo = pygit2.Repository(repopath)

    # Clone the repo into a temp folder
    newpath = tempfile.mkdtemp()
    new_repo = pygit2.clone_repository(repopath, newpath)

    file_path = os.path.join(newpath, issue.uid)

    # Get the current index
    index = new_repo.index

    # Are we adding files
    added = False
    if not os.path.exists(file_path):
        added = True

    # Write down what changed
    with open(file_path, 'w') as stream:
        stream.write(issue.to_json())

    # Retrieve the list of files that changed
    diff = new_repo.diff()
    files = [patch.new_file_path for patch in diff]

    # Add the changes to the index
    if added:
        index.add(issue.uid)
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
        'Updated ticket %s: %s' % (issue.uid, issue.title),
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
