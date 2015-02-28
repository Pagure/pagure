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
