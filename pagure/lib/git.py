# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""
from __future__ import absolute_import, print_function, unicode_literals

import datetime
import json
import logging
import os
import shutil
import subprocess
import tarfile
import tempfile
import zipfile

import arrow
import pygit2
import six

# from sqlalchemy.orm.session import Session
from pygit2.remotes import RemoteCollection
from sqlalchemy.exc import SQLAlchemyError

import pagure.exceptions
import pagure.hooks
import pagure.lib.notify
import pagure.lib.query
import pagure.lib.tasks
import pagure.utils
from pagure.config import config as pagure_config
from pagure.lib import model
from pagure.lib.repo import PagureRepo

# pylint: disable=too-many-branches
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# pylint: disable=too-many-lines


_log = logging.getLogger(__name__)


def commit_to_patch(
    repo_obj, commits, diff_view=False, find_similar=False, separated=False
):
    """For a given commit (PyGit2 commit object) of a specified git repo,
    returns a string representation of the changes the commit did in a
    format that allows it to be used as patch.

    :arg repo_obj: the `pygit2.Repository` object of the git repo to
        retrieve the commits in
    :type repo_obj: `pygit2.Repository`
    :arg commits: the list of commits to convert to path
    :type commits: str or list
    :kwarg diff_view: a boolean specifying if what is returned is a git
        patch or a git diff
    :type diff_view: boolean
    :kwarg find_similar: a boolean specifying if what we run find_similar
        on the diff to group renamed files
    :type find_similar: boolean
    :kwarg separated: a boolean specifying if the data returned should be
        returned as one text blob or not. If diff_view is True, then the diff
        are also split by file, otherwise, the different patches are returned
        as different text blob.
    :type separated: boolean
    :return: the patch or diff representation of the provided commits
    :rtype: str

    """
    if not isinstance(commits, list):
        commits = [commits]

    patch = []
    for cnt, commit in enumerate(commits):
        if commit.parents:
            diff = repo_obj.diff(commit.parents[0], commit)
        else:
            # First commit in the repo
            diff = commit.tree.diff_to_tree(swap=True)

        if diff.patch is None:
            continue

        if find_similar and diff:
            diff.find_similar()

        if diff_view:
            if separated:
                for el in diff.patch.split("\ndiff --git a/"):
                    if el and not el.startswith("diff --git a/"):
                        patch.append("\ndiff --git a/" + el)
                    elif el:
                        patch.append(el)
            else:
                patch.append(diff.patch)
        else:

            subject = message = ""
            if "\n" in commit.message:
                subject, message = commit.message.split("\n", 1)
            else:
                subject = commit.message

            if len(commits) > 1:
                subject = "[PATCH %s/%s] %s" % (cnt + 1, len(commits), subject)

            patch.append(
                """From {commit} Mon Sep 17 00:00:00 2001
From: {author_name} <{author_email}>
Date: {date}
Subject: {subject}

{msg}
---

{patch}
""".format(
                    commit=commit.oid.hex,
                    author_name=commit.author.name,
                    author_email=commit.author.email,
                    date=datetime.datetime.utcfromtimestamp(
                        commit.commit_time
                    ).strftime("%b %d %Y %H:%M:%S +0000"),
                    subject=subject,
                    msg=message,
                    patch=diff.patch,
                )
            )

    if separated:
        return patch
    else:
        return "".join(filter(None, patch))


def generate_gitolite_acls(project=None, group=None):
    """Generate the gitolite configuration file.

    :arg project: the project of which to update the ACLs. This argument
            can take three values: ``-1``, ``None`` and a project.
            If project is ``-1``, the configuration should be refreshed for
            *all* projects.
            If project is ``None``, there no specific project to refresh
            but the ssh key of an user was added and updated.
            If project is a pagure.lib.model.Project, the configuration of
            this project should be updated.
    :type project: None, int or pagure.lib.model.Project
    :kwarg group: the group to refresh the members of
    :type group: None or str

    """
    if project != -1:
        task = pagure.lib.tasks.generate_gitolite_acls.delay(
            namespace=project.namespace if project else None,
            name=project.name if project else None,
            user=project.user.user if project and project.is_fork else None,
            group=group,
        )
    else:
        task = pagure.lib.tasks.generate_gitolite_acls.delay(
            name=-1, group=group
        )
    return task


def update_git(obj, repo):
    """Schedules an update_repo task after determining arguments."""
    ticketuid = None
    requestuid = None
    if obj.isa == "issue":
        ticketuid = obj.uid
    elif obj.isa == "pull-request":
        requestuid = obj.uid
    else:
        raise NotImplementedError("Unknown object type %s" % obj.isa)

    queued = pagure.lib.tasks.update_git.delay(
        repo.name,
        repo.namespace,
        repo.user.username if repo.is_fork else None,
        ticketuid,
        requestuid,
    )
    _maybe_wait(queued)
    return queued


def _maybe_wait(result):
    """Function to patch if one wants to wait for finish.

    This function should only ever be overridden by a few tests that depend
    on counting and very precise timing."""
    pass


def _make_signature(name, email):
    if six.PY2:
        if isinstance(name, six.text_type):
            name = name.encode("utf-8")
        if isinstance(email, six.text_type):
            email = email.encode("utf-8")
    return pygit2.Signature(name=name, email=email)


def _update_git(obj, repo):
    """Update the given issue in its git.

    This method forks the provided repo, add/edit the issue whose file name
    is defined by the uid field of the issue and if there are additions/
    changes commit them and push them back to the original repo.

    """
    _log.info("Update the git repo: %s for: %s", repo.path, obj)

    with TemporaryClone(repo, obj.repotype, "update_git") as tempclone:
        if tempclone is None:
            # Turns out we don't have a repo for this kind of object.
            return

        newpath = tempclone.repopath
        new_repo = tempclone.repo

        file_path = os.path.join(newpath, obj.uid)

        # Get the current index
        index = new_repo.index

        # Are we adding files
        added = False
        if not os.path.exists(file_path):
            added = True

        # Write down what changed
        with open(file_path, "w") as stream:
            stream.write(
                json.dumps(
                    obj.to_json(),
                    sort_keys=True,
                    indent=4,
                    separators=(",", ": "),
                )
            )

        # Retrieve the list of files that changed
        diff = new_repo.diff()
        files = []
        for patch in diff:
            files.append(patch.delta.new_file.path)

        # Add the changes to the index
        if added:
            index.add(obj.uid)
        for filename in files:
            index.add(filename)

        # If not change, return
        if not files and not added:
            return

        # See if there is a parent to this commit
        parent = None
        try:
            parent = new_repo.head.peel().oid
        except pygit2.GitError:
            pass

        parents = []
        if parent:
            parents.append(parent)

        # Author/commiter will always be this one
        author = _make_signature(name="pagure", email="pagure")

        # Actually commit
        new_repo.create_commit(
            "refs/heads/master",
            author,
            author,
            "Updated %s %s: %s" % (obj.isa, obj.uid, obj.title),
            new_repo.index.write_tree(),
            parents,
        )
        index.write()

        # And push it back
        tempclone.push("pagure", "master", internal="yes")


def clean_git(repo, obj_repotype, obj_uid):
    if repo is None:
        return

    task = pagure.lib.tasks.clean_git.delay(
        repo.name,
        repo.namespace,
        repo.user.username if repo.is_fork else None,
        obj_repotype,
        obj_uid,
    )
    _maybe_wait(task)
    return task


def _clean_git(repo, obj_repotype, obj_uid):
    """Update the given issue remove it from its git."""
    _log.info("Update the git repo: %s to remove: %s", repo.path, obj_uid)

    with TemporaryClone(repo, obj_repotype, "clean_git") as tempclone:
        if tempclone is None:
            # This repo is not tracked on disk
            return

        newpath = tempclone.repopath
        new_repo = tempclone.repo

        file_path = os.path.join(newpath, obj_uid)

        # Get the current index
        index = new_repo.index

        # Are we adding files
        if not os.path.exists(file_path):
            return

        # Remove the file
        os.unlink(file_path)

        # Add the changes to the index
        index.remove(obj_uid)

        # See if there is a parent to this commit
        parent = None
        if not new_repo.is_empty:
            parent = new_repo.head.peel().oid

        parents = []
        if parent:
            parents.append(parent)

        # Author/commiter will always be this one
        author = _make_signature(name="pagure", email="pagure")

        # Actually commit
        new_repo.create_commit(
            "refs/heads/master",
            author,
            author,
            "Removed object %s: %s" % (obj_repotype, obj_uid),
            new_repo.index.write_tree(),
            parents,
        )
        index.write()

        master_ref = new_repo.lookup_reference("HEAD").resolve().name
        tempclone.push("pagure", master_ref, internal="yes")


def get_user_from_json(session, jsondata, key="user"):
    """From the given json blob, retrieve the user info and search for it
    in the db and create the user if it does not already exist.
    """
    user = None

    username = fullname = useremails = default_email = None

    data = jsondata.get(key, None)

    if data:
        username = data.get("name")
        fullname = data.get("fullname")
        useremails = data.get("emails")
        default_email = data.get("default_email")

    if not default_email and useremails:
        default_email = useremails[0]

    if not username and not useremails:
        return

    user = pagure.lib.query.search_user(session, username=username)
    if not user:
        for email in useremails:
            user = pagure.lib.query.search_user(session, email=email)
            if user:
                break

    if not user:
        user = pagure.lib.query.set_up_user(
            session=session,
            username=username,
            fullname=fullname or username,
            default_email=default_email,
            emails=useremails,
            keydir=pagure_config.get("GITOLITE_KEYDIR", None),
        )
        session.commit()

    return user


def get_project_from_json(session, jsondata):
    """From the given json blob, retrieve the project info and search for
    it in the db and create the projec if it does not already exist.
    """
    project = None

    user = get_user_from_json(session, jsondata)
    name = jsondata.get("name")
    namespace = jsondata.get("namespace")
    project_user = None
    if jsondata.get("parent"):
        project_user = user.username

    project = pagure.lib.query._get_project(
        session, name, user=project_user, namespace=namespace
    )

    if not project:
        parent = None
        if jsondata.get("parent"):
            parent = get_project_from_json(session, jsondata.get("parent"))

            pagure.lib.query.fork_project(
                session=session, repo=parent, user=user.username
            )

        else:
            pagure.lib.query.new_project(
                session,
                user=user.username,
                name=name,
                namespace=namespace,
                description=jsondata.get("description"),
                parent_id=parent.id if parent else None,
                blacklist=pagure_config.get("BLACKLISTED_PROJECTS", []),
                allowed_prefix=pagure_config.get("ALLOWED_PREFIX", []),
                prevent_40_chars=pagure_config.get(
                    "OLD_VIEW_COMMIT_ENABLED", False
                ),
            )

        session.commit()
        project = pagure.lib.query._get_project(
            session, name, user=user.username, namespace=namespace
        )

        tags = jsondata.get("tags", None)
        if tags:
            pagure.lib.query.add_tag_obj(
                session, project, tags=tags, user=user.username
            )

    return project


def update_custom_field_from_json(session, repo, issue, json_data):
    """Update the custom fields according to the custom fields of
    the issue. If the custom field is not present for the repo in
    it's settings, this will create them.

    :arg session: the session to connect to the database with.
    :arg repo: the sqlalchemy object of the project
    :arg issue: the sqlalchemy object of the issue
    :arg json_data: the json representation of the issue taken from the git
        and used to update the data in the database.
    """

    # Update custom key value, if present
    custom_fields = json_data.get("custom_fields")
    if not custom_fields:
        return

    current_keys = []
    for key in repo.issue_keys:
        current_keys.append(key.name)

    for new_key in custom_fields:
        if new_key["name"] not in current_keys:
            issuekey = model.IssueKeys(
                project_id=repo.id,
                name=new_key["name"],
                key_type=new_key["key_type"],
            )
            try:
                session.add(issuekey)
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                continue

        # The key should be present in the database now
        key_obj = pagure.lib.query.get_custom_key(
            session, repo, new_key["name"]
        )

        value = new_key.get("value")
        if value:
            value = value.strip()
        pagure.lib.query.set_custom_key_value(
            session, issue=issue, key=key_obj, value=value
        )
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()


def update_ticket_from_git(
    session, reponame, namespace, username, issue_uid, json_data, agent
):
    """Update the specified issue (identified by its unique identifier)
    with the data present in the json blob provided.

    :arg session: the session to connect to the database with.
    :arg repo: the name of the project to update
    :arg namespace: the namespace of the project to update
    :arg username: the username of the project to update (if the project
        is a fork)
    :arg issue_uid: the unique identifier of the issue to update
    :arg json_data: the json representation of the issue taken from the git
        and used to update the data in the database.
    :arg agent: the username of the person who pushed the changes (and thus
        is assumed did the action).

    """

    repo = pagure.lib.query._get_project(
        session, reponame, user=username, namespace=namespace
    )

    if not repo:
        raise pagure.exceptions.PagureException(
            "Unknown repo %s of username: %s in namespace: %s"
            % (reponame, username, namespace)
        )

    user = get_user_from_json(session, json_data)
    # rely on the agent provided, but if something goes wrong, behave as
    # ticket creator
    agent = pagure.lib.query.search_user(session, username=agent) or user

    status = json_data.get("status")
    close_status = json_data.get("close_status")
    if status and status.lower() not in ["open", "closed"]:
        if status.lower() != "open" and close_status is None:
            close_status = status
            status = "Closed"
        elif status.lower() != "open" and close_status is not None:
            status = "Closed"
    elif status:
        status = status.capitalize()

    if close_status and close_status not in repo.close_status:
        close_status = repo.close_status
        close_status.append(close_status)
        repo.close_status = close_status
        session.add(repo)
        session.commit()

    issue = pagure.lib.query.get_issue_by_uid(session, issue_uid=issue_uid)
    messages = []
    if not issue:
        date_created = None
        if json_data.get("date_created"):
            date_created = datetime.datetime.utcfromtimestamp(
                float(json_data.get("date_created"))
            )
        # Create new issue
        issue = pagure.lib.query.new_issue(
            session,
            repo=repo,
            title=json_data.get("title"),
            content=json_data.get("content"),
            priority=json_data.get("priority"),
            user=user.username,
            issue_id=json_data.get("id"),
            issue_uid=issue_uid,
            private=json_data.get("private"),
            status=status,
            close_status=close_status,
            date_created=date_created,
            notify=False,
        )

        if json_data.get("closed_at"):
            issue.closed_at = datetime.datetime.utcfromtimestamp(
                float(json_data.get("date_created"))
            )

    else:
        # Edit existing issue
        msgs = pagure.lib.query.edit_issue(
            session,
            issue=issue,
            user=agent.username,
            title=json_data.get("title"),
            content=json_data.get("content"),
            priority=json_data.get("priority"),
            status=status,
            close_status=close_status,
            private=json_data.get("private"),
        )
        if json_data.get("closed_at"):
            issue.closed_at = datetime.datetime.utcfromtimestamp(
                float(json_data.get("date_created"))
            )
        if msgs:
            messages.extend(msgs)

    session.commit()

    issue = pagure.lib.query.get_issue_by_uid(session, issue_uid=issue_uid)

    update_custom_field_from_json(
        session, repo=repo, issue=issue, json_data=json_data
    )

    # Update milestone
    milestone = json_data.get("milestone")

    # If milestone is not in the repo settings, add it
    if milestone:
        if milestone.strip() not in repo.milestones:
            try:
                tmp_milestone = repo.milestones.copy()
                tmp_milestone[milestone.strip()] = None
                repo.milestones = tmp_milestone
                session.add(repo)
                session.commit()
            except SQLAlchemyError:
                session.rollback()
    try:
        msgs = pagure.lib.query.edit_issue(
            session,
            issue=issue,
            user=agent.username,
            milestone=milestone,
            title=json_data.get("title"),
            content=json_data.get("content"),
            status=json_data.get("status"),
            close_status=json_data.get("close_status"),
            private=json_data.get("private"),
        )
        if msgs:
            messages.extend(msgs)
    except SQLAlchemyError:
        session.rollback()

    # Update close_status
    close_status = json_data.get("close_status")

    if close_status:
        if close_status.strip() not in repo.close_status:
            try:
                repo.close_status.append(close_status.strip())
                session.add(repo)
                session.commit()
            except SQLAlchemyError:
                session.rollback()

    # Update tags
    tags = json_data.get("tags", [])
    msgs = pagure.lib.query.update_tags(
        session, issue, tags, username=user.user
    )
    if msgs:
        messages.extend(msgs)

    # Update boards
    boards = json_data.get("boards") or []
    _log.debug("Loading %s boards", len(boards))

    # Go over the boards and add them
    try:
        for board_issue in boards:
            board = board_issue["board"]
            _log.debug("Loading board: %s", board["name"])
            tag_obj = pagure.lib.query.get_colored_tag(
                session, board["tag"]["tag"], issue.project.id
            )
            if not tag_obj:
                _log.debug("Creating tag: %s", board["tag"]["tag"])
                pagure.lib.query.new_tag(
                    session,
                    tag_name=board["tag"]["tag"],
                    tag_description=board["tag"]["tag_description"],
                    tag_color=board["tag"]["tag_color"],
                    project_id=issue.project.id,
                )
            board_obj = None
            for b in repo.boards:
                if b.name == board["name"]:
                    board_obj = b
                    break
            if not board_obj:
                _log.debug("Creating board: %s", board["name"])
                board_obj = pagure.lib.query.create_board(
                    session,
                    project=issue.project,
                    name=board["name"],
                    active=board["active"],
                    tag=board["tag"]["tag"],
                )
                session.flush()
            for idx, status in enumerate(board["status"]):
                _log.debug("Updating status: %s", status["name"])
                pagure.lib.query.update_board_status(
                    session,
                    board=board_obj,
                    name=status["name"],
                    rank=idx,
                    default=status["default"],
                    close=status["close"],
                    close_status=status["close_status"],
                    bg_color=status["bg_color"],
                )
            session.flush()

            _log.debug("Updating ticket in board")
            pagure.lib.query.update_ticket_board_status(
                session,
                board=board_obj,
                user=agent,
                rank=board_issue["rank"],
                status_name=board_issue["status"]["name"],
                ticket_uid=issue.uid,
                ticket_id=None,
            )
            session.flush()
    except SQLAlchemyError:
        _log.exception("An error occured while loading the boards")
        session.rollback()

    # Update assignee
    assignee = get_user_from_json(session, json_data, key="assignee")
    if assignee:
        msg = pagure.lib.query.add_issue_assignee(
            session, issue, assignee.username, user=agent.user, notify=False
        )
        if msg:
            messages.append(msg)

    # Update depends
    depends = json_data.get("depends", [])
    msgs = pagure.lib.query.update_dependency_issue(
        session, issue.project, issue, depends, username=agent.user
    )
    if msgs:
        messages.extend(msgs)

    # Update blocks
    blocks = json_data.get("blocks", [])
    msgs = pagure.lib.query.update_blocked_issue(
        session, issue.project, issue, blocks, username=agent.user
    )
    if msgs:
        messages.extend(msgs)

    for comment in json_data["comments"]:
        usercomment = get_user_from_json(session, comment)
        commentobj = pagure.lib.query.get_issue_comment_by_user_and_comment(
            session, issue_uid, usercomment.id, comment["comment"]
        )
        if not commentobj:
            pagure.lib.query.add_issue_comment(
                session,
                issue=issue,
                comment=comment["comment"],
                user=usercomment.username,
                notify=False,
                date_created=datetime.datetime.fromtimestamp(
                    float(comment["date_created"])
                ),
            )

    if messages:
        pagure.lib.query.add_metadata_update_notif(
            session=session, obj=issue, messages=messages, user=agent.username
        )
    session.commit()


def update_request_from_git(
    session, reponame, namespace, username, request_uid, json_data
):
    """Update the specified request (identified by its unique identifier)
    with the data present in the json blob provided.

    :arg session: the session to connect to the database with.
    :arg repo: the name of the project to update
    :arg username: the username to find the repo, is not None for forked
        projects
    :arg request_uid: the unique identifier of the issue to update
    :arg json_data: the json representation of the issue taken from the git
        and used to update the data in the database.

    """

    repo = pagure.lib.query._get_project(
        session, reponame, user=username, namespace=namespace
    )

    if not repo:
        raise pagure.exceptions.PagureException(
            "Unknown repo %s of username: %s in namespace: %s"
            % (reponame, username, namespace)
        )

    user = get_user_from_json(session, json_data)

    request = pagure.lib.query.get_request_by_uid(
        session, request_uid=request_uid
    )

    if not request:
        repo_from = get_project_from_json(session, json_data.get("repo_from"))

        repo_to = get_project_from_json(session, json_data.get("project"))

        status = json_data.get("status")
        if pagure.utils.is_true(status):
            status = "Open"
        elif pagure.utils.is_true(status, ["false"]):
            status = "Merged"

        # Create new request
        pagure.lib.query.new_pull_request(
            session,
            repo_from=repo_from,
            branch_from=json_data.get("branch_from"),
            repo_to=repo_to if repo_to else None,
            remote_git=json_data.get("remote_git"),
            branch_to=json_data.get("branch"),
            title=json_data.get("title"),
            user=user.username,
            requestuid=json_data.get("uid"),
            requestid=json_data.get("id"),
            status=status,
            notify=False,
        )
        session.commit()

    request = pagure.lib.query.get_request_by_uid(
        session, request_uid=request_uid
    )

    # Update start and stop commits
    request.commit_start = json_data.get("commit_start")
    request.commit_stop = json_data.get("commit_stop")

    # Update assignee
    assignee = get_user_from_json(session, json_data, key="assignee")
    if assignee:
        pagure.lib.query.add_pull_request_assignee(
            session, request, assignee.username, user=user.user
        )

    for comment in json_data["comments"]:
        user = get_user_from_json(session, comment)
        commentobj = pagure.lib.query.get_request_comment(
            session, request_uid, comment["id"]
        )
        if not commentobj:
            pagure.lib.query.add_pull_request_comment(
                session,
                request,
                commit=comment["commit"],
                tree_id=comment.get("tree_id") or None,
                filename=comment["filename"],
                row=comment["line"],
                comment=comment["comment"],
                user=user.username,
                notify=False,
            )

    # Add/update tags:
    tags = json_data.get("tags") or []
    if tags:
        user = get_user_from_json(session, json_data)
        pagure.lib.query.add_tag_obj(session, request, tags, user.username)

    session.commit()


def _add_file_to_git(repo, issue, attachmentfolder, user, filename):
    """Add a given file to the specified ticket git repository.

    :arg repo: the Project object from the database
    :arg attachmentfolder: the folder on the filesystem where the attachments
        are stored
    :arg ticketfolder: the folder on the filesystem where the git repo for
        tickets are stored
    :arg user: the user object with its username and email
    :arg filename: the name of the file to save

    """
    with TemporaryClone(repo, issue.repotype, "add_file_to_git") as tempclone:
        newpath = tempclone.repopath
        new_repo = tempclone.repo

        folder_path = os.path.join(newpath, "files")
        file_path = os.path.join(folder_path, filename)

        # Get the current index
        index = new_repo.index

        # Are we adding files
        if os.path.exists(file_path):
            # File exists, remove the clone and return
            shutil.rmtree(newpath)
            return os.path.join("files", filename)

        if not os.path.exists(folder_path):
            os.mkdir(folder_path)

        # Copy from attachments directory
        src = os.path.join(attachmentfolder, repo.fullname, "files", filename)
        shutil.copyfile(src, file_path)

        # Retrieve the list of files that changed
        diff = new_repo.diff()
        files = [patch.new_file_path for patch in diff]

        # Add the changes to the index
        index.add(os.path.join("files", filename))
        for filename in files:
            index.add(filename)

        # See if there is a parent to this commit
        parent = None
        try:
            parent = new_repo.head.peel().oid
        except pygit2.GitError:
            pass

        parents = []
        if parent:
            parents.append(parent)

        # Author/commiter will always be this one
        author = _make_signature(name=user.username, email=user.default_email)

        # Actually commit
        new_repo.create_commit(
            "refs/heads/master",
            author,
            author,
            "Add file %s to ticket %s: %s"
            % (filename, issue.uid, issue.title),
            new_repo.index.write_tree(),
            parents,
        )
        index.write()

        master_ref = new_repo.lookup_reference("HEAD").resolve()
        tempclone.push(user.username, master_ref.name)

    return os.path.join("files", filename)


class TemporaryClone(object):
    _project = None
    _action = None
    _repotype = None
    _origpath = None
    _origrepopath = None
    repopath = None
    repo = None

    def __init__(self, project, repotype, action, path=None, parent=None):
        """Initializes a TempoaryClone instance.

        Args:
            project (model.Project): A project instance
            repotype (string): The type of repo to clone, one of:
                main, docs, requests, tickets
            action (string): Type of action performing, used in the
                temporary directory name
            path (string or None): the path to clone, allows cloning, for
                example remote git repo for remote PRs instead of the
                default one
            parent (string or None): Adds this directory to the path in
                which the project is cloned

        """
        if repotype not in pagure.lib.query.get_repotypes():
            raise NotImplementedError("Repotype %s not known" % repotype)

        self._project = project
        self._repotype = repotype
        self._action = action
        self._path = path
        self._parent = parent

    def __enter__(self):
        """Enter the context manager, creating the clone."""
        self.repopath = tempfile.mkdtemp(prefix="pagure-%s-" % self._action)
        self._origrepopath = self.repopath
        if self._parent:
            self.repopath = os.path.join(self.repopath, self._parent)
            os.makedirs(self.repopath)
        # This is the simple case. Just do a local clone
        # use either the specified path or the use the path of the
        # specified project
        self._origpath = self._path or self._project.repopath(self._repotype)
        if self._origpath is None:
            # No repository of this type
            # 'main' is already caught and returns an error in repopath()
            return None
        if not os.path.exists(self._origpath):
            return None
        PagureRepo.clone(self._origpath, self.repopath)
        # Because for whatever reason, one pygit2.Repository is not
        # equal to another.... The pygit2.Repository returned from
        # pygit2.clone_repository does not have the "branches" attribute.
        self.repo = pygit2.Repository(self.repopath)
        self._origrepo = pygit2.Repository(self._origpath)

        # Make sure that all remote refs are mapped to local ones.
        headname = None
        if not self.repo.is_empty and not self.repo.head_is_unborn:
            headname = self.repo.head.shorthand

        # Sync up all the references, branches and PR heads
        for ref in self._origrepo.listall_references():
            if ref.startswith("refs/heads/"):
                localname = ref.replace("refs/heads/", "")
                if localname in (headname, "HEAD"):
                    # This gets checked out by default
                    continue
                branch = self.repo.branches.remote.get("origin/%s" % localname)
                self.repo.branches.local.create(localname, branch.peel())
            elif ref.startswith("refs/pull/"):
                reference = self._origrepo.references.get(ref)
                self.repo.references.create(ref, reference.peel().oid.hex)

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit the context manager, removing the temorary clone."""
        shutil.rmtree(self.repopath)

    def change_project_association(self, new_project):
        """Make this instance "belong" to another project.

        This is useful when you want to create TemporaryClone of one project
        and then push some of its content into a different project just
        by running ``push`` or ``mirror`` methods.

        Args:
            new_project (pagure.lib.model.Project): project to associate
                this TemporaryClone instance with
        """
        self._project = new_project
        self.repo.remotes.set_push_url("origin", new_project.repopath("main"))

    def mirror(self, username, force=False, **extra):
        """Run ``git push --mirror`` of the repo to its origin.

        Args:
            username (string): The user on who's account this push is
            force (bool): whether or not to use ``--force`` when pushing
            extra (dict): Extra fields passed to the remote side. Either via
                environment variables, or as X-Extra-<key> HTTP headers.
        """
        # git push --mirror fails if there are no branches
        if len(list(self.repo.branches)) > 0:
            self._push(username, "--mirror", force, **extra)

    def push(self, username, sbranch, tbranch=None, force=False, **extra):
        """Push the repo back to its origin.

        Args:
            username (string): The user on who's account this push is
            sbranch (string): Source branch to push
            tbranch (string): Target branch if different from sbranch
            force (bool): whether or not to use ``--force`` when pushing
            extra (dict): Extra fields passed to the remote side. Either via
                environment variables, or as X-Extra-<key> HTTP headers.
        """
        pushref = "%s:%s" % (sbranch, tbranch if tbranch else sbranch)
        self._push(username, pushref, force, **extra)

    def _push(self, username, pushref, force, **extra):
        """Push the repo back to its origin.

        Args:
            username (string): The user on who's account this push is
            pushref(string): either ``<sbranch>:<tbranch>`` or ``--mirror``
            force (bool): whether or not to use ``--force`` when pushing
            extra (dict): Extra fields passed to the remote side. Either via
                environment variables, or as X-Extra-<key> HTTP headers.
        """
        if "pull_request" in extra:
            extra["pull_request_uid"] = extra["pull_request"].uid
            del extra["pull_request"]

        command = ["git", "push", "origin"]
        if force:
            command.append("--force")
        environ = {}

        command.append("--follow-tags")

        try:
            _log.debug(
                "Running a git push of %s to %s"
                % (pushref, self._path or self._project.fullname)
            )
            env = os.environ.copy()
            env["GL_USER"] = username
            env["GL_BYPASS_ACCESS_CHECKS"] = "1"
            if pagure_config.get("GITOLITE_HOME"):
                env["HOME"] = pagure_config["GITOLITE_HOME"]
            env.update(environ)
            env.update(extra)
            out = subprocess.check_output(
                command + [pushref],
                cwd=self.repopath,
                stderr=subprocess.STDOUT,
                env=env,
            )
            _log.debug("Output: %s" % out)
        except subprocess.CalledProcessError as ex:
            # This should never really happen, since we control the repos, but
            # this way, we can be sure to get the output logged
            remotes = []
            for line in ex.output.decode("utf-8").split("\n"):
                _log.info("Remote line: %s", line)
                if line.startswith("remote: "):
                    _log.debug("Remote: %s" % line)
                    remotes.append(line[len("remote: ") :].strip())
            if remotes:
                _log.info("Remote rejected with: %s" % remotes)
                raise pagure.exceptions.PagurePushDenied(
                    "Remote hook declined the push: %s" % "\n".join(remotes)
                )
            else:
                # Something else happened, pass the original
                _log.exception("Error pushing. Output: %s", ex.output)
                raise


def _update_file_in_git(
    repo, branch, branchto, filename, content, message, user, email
):
    """Update a specific file in the specified repository with the content
    given and commit the change under the user's name.

    :arg repo: the Project object from the database
    :arg branch: the branch from which the edit is made
    :arg branchto: the name of the branch into which to edit the file
    :arg filename: the name of the file to save
    :arg content: the new content of the file
    :arg message: the message of the git commit
    :arg user: the user name, to use in the commit
    :arg email: the email of the user, to use in the commit

    """
    _log.info("Updating file: %s in the repo: %s", filename, repo.path)

    with TemporaryClone(repo, "main", "edit_file") as tempclone:
        newpath = tempclone.repopath
        new_repo = tempclone.repo

        new_repo.checkout("refs/heads/%s" % branch)

        file_path = os.path.join(newpath, filename)

        # Get the current index
        index = new_repo.index

        # Write down what changed
        with open(file_path, "wb") as stream:
            stream.write(content.replace("\r", "").encode("utf-8"))

        # Retrieve the list of files that changed
        diff = new_repo.diff()
        files = []
        for patch in diff:
            files.append(patch.delta.new_file.path)

        # Add the changes to the index
        added = False
        for filename in files:
            added = True
            index.add(filename)

        # If not change, return
        if not files and not added:
            return

        # See if there is a parent to this commit
        branch_ref = get_branch_ref(new_repo, branch)
        parent = branch_ref.peel()

        # See if we need to create the branch
        nbranch_ref = None
        if branchto not in new_repo.listall_branches():
            nbranch_ref = new_repo.create_branch(branchto, parent)

        parents = []
        if parent:
            parents.append(parent.hex)

        # Author/commiter will always be this one
        name = user.fullname or user.username
        author = _make_signature(name=name, email=email)

        # Actually commit
        new_repo.create_commit(
            nbranch_ref.name if nbranch_ref else branch_ref.name,
            author,
            author,
            message.strip(),
            new_repo.index.write_tree(),
            parents,
        )
        index.write()

        tempclone.push(
            user.username,
            nbranch_ref.name if nbranch_ref else branch_ref.name,
            branchto,
        )

    return os.path.join("files", filename)


def read_output(cmd, abspath, input=None, keepends=False, error=False, **kw):
    """Read the output from the given command to run.

    cmd:
        The command to run, this is a list with each space separated into an
        element of the list.
    abspath:
        The absolute path where the command should be ran.
    input:
        Whether the command should take input from stdin or not.
        (Defaults to False)
    keepends:
        Whether to strip the newline characters at the end of the standard
        output or not.
    error:
        Whether to return both the standard output and the standard error,
        or just the standard output.
        (Defaults to False).
    kw*:
        Any other arguments to be passed onto the subprocess.Popen command,
        such as env, shell, executable...

    """
    if input:
        stdin = subprocess.PIPE
    else:
        stdin = None
    procs = subprocess.Popen(
        cmd,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=abspath,
        **kw,
    )
    (out, err) = procs.communicate(input)
    retcode = procs.wait()
    if isinstance(out, six.binary_type):
        out = out.decode("utf-8")
    if isinstance(err, six.binary_type):
        err = err.decode("utf-8")
    if retcode:
        print("ERROR: %s =-- %s" % (cmd, retcode))
        print(out)
        print(err)
    if not keepends:
        out = out.rstrip("\n\r")

    if error:
        return (out, err)
    else:
        return out


def read_git_output(
    args, abspath, input=None, keepends=False, error=False, **kw
):
    """Read the output of a Git command."""

    return read_output(
        ["git"] + args,
        abspath,
        input=input,
        keepends=keepends,
        error=error,
        **kw,
    )


def read_git_lines(args, abspath, keepends=False, error=False, **kw):
    """Return the lines output by Git command.

    Return as single lines, with newlines stripped off."""

    if error:
        return read_git_output(
            args, abspath, keepends=keepends, error=error, **kw
        )
    else:
        return read_git_output(
            args, abspath, keepends=keepends, **kw
        ).splitlines(keepends)


def get_revs_between(oldrev, newrev, abspath, refname, forced=False):
    """Yield revisions between HEAD and BASE."""

    cmd = ["rev-list", "%s...%s" % (oldrev, newrev)]
    if forced:
        head = get_default_branch(abspath)
        cmd.append("^%s" % head)
    if set(newrev) == set("0"):
        cmd = ["rev-list", "%s" % oldrev]
    elif set(oldrev) == set("0") or set(oldrev) == set("^0"):
        head = get_default_branch(abspath)
        cmd = ["rev-list", "%s" % newrev, "^%s" % head]
        if head in refname:
            cmd = ["rev-list", "%s" % newrev]
    return pagure.lib.git.read_git_lines(cmd, abspath)


def is_forced_push(oldrev, newrev, abspath):
    """Returns whether there was a force push between HEAD and BASE.
    Doc: http://stackoverflow.com/a/12258773
    """

    if set(oldrev) == set("0"):
        # This is a push that's creating a new branch => certainly ok
        return False
    # Returns if there was any commits deleted in the changeset
    cmd = ["rev-list", "%s" % oldrev, "^%s" % newrev]
    out = pagure.lib.git.read_git_lines(cmd, abspath)
    return len(out) > 0


def get_base_revision(torev, fromrev, abspath):
    """Return the base revision between HEAD and BASE.
    This is useful in case of force-push.
    """
    cmd = ["merge-base", fromrev, torev]
    return pagure.lib.git.read_git_lines(cmd, abspath)


def get_default_branch(abspath):
    """Return the default branch of a repo."""
    cmd = ["rev-parse", "--abbrev-ref", "HEAD"]
    out = pagure.lib.git.read_git_lines(cmd, abspath)
    if out:
        return out[0]
    else:
        return "master"


def get_author(commit, abspath):
    """Return the name of the person that authored the commit."""
    user = pagure.lib.git.read_git_lines(
        ["log", "-1", '--pretty=format:"%an"', commit], abspath
    )[0].replace('"', "")
    return user


def get_author_email(commit, abspath):
    """Return the email of the person that authored the commit."""
    user = pagure.lib.git.read_git_lines(
        ["log", "-1", '--pretty=format:"%ae"', commit], abspath
    )[0].replace('"', "")
    return user


def get_commit_subject(commit, abspath):
    """Return the subject of the commit."""
    subject = pagure.lib.git.read_git_lines(
        ["log", "-1", '--pretty=format:"%s"', commit], abspath
    )[0].replace('"', "")
    return subject


def get_changed_files(torev, fromrev, abspath):
    """Return files changed between HEAD and BASE.
    Return as a dict with paths as keys and status letters as values.
    """
    cmd = ["diff", "--name-status", "-z", fromrev, torev]
    output = pagure.lib.git.read_git_output(cmd, abspath)
    items = output.split("\0")
    return {k: v for v, k in zip(items[0::2], items[1::2])}


def get_repo_info_from_path(gitdir, hide_notfound=False):
    """Returns the name, username, namespace and type of a git directory

    This gets computed based on the *_FOLDER's in the config file,
    and as such only works for the central file-based repositories.

    Args:
        gitdir (string): Path of the canonical git repository
        hide_notfound (bool): Whether to return a tuple with None's instead of
            raising an error if the regenerated repo didn't exist.
            Can be used to hide the difference between no project access vs not
            existing when looking up private repos.
    Return: (tuple): Tuple with (repotype, username, namespace, repo)
        Some of these elements may be None if not applicable.
    """
    if not os.path.isabs(gitdir):
        raise ValueError("Tried to locate non-absolute gitdir %s" % gitdir)
    gitdir = os.path.normpath(gitdir)

    types = {
        "main": pagure_config["GIT_FOLDER"],
        "docs": pagure_config["DOCS_FOLDER"],
        "tickets": pagure_config["TICKETS_FOLDER"],
        "requests": pagure_config["REQUESTS_FOLDER"],
    }

    match = None
    matchlen = None

    # First find the longest match in types. This makes sure that even if the
    # non-main repos are in a subdir of main (i.e. repos/ and repos/tickets/),
    # we find the correct type.
    for typename in types:
        if not types[typename]:
            continue
        types[typename] = os.path.abspath(types[typename])
        path = types[typename] + "/"
        if gitdir.startswith(path) and (
            matchlen is None or len(path) > matchlen
        ):
            match = typename
            matchlen = len(path)

    if match is None:
        raise ValueError("Gitdir %s could not be located" % gitdir)

    typepath = types[match]
    guesspath = gitdir[len(typepath) + 1 :]
    if len(guesspath) < 5:
        # At least 4 characters for ".git" is required plus one for project
        # name
        raise ValueError("Invalid gitdir %s located" % gitdir)

    # Just in the case we run on a non-*nix system...
    guesspath = guesspath.replace("\\", "/")

    # Now guesspath should be one of:
    # - reponame.git
    # - namespace/reponame.git
    # - forks/username/reponame.git
    # - forks/username/namespace/reponame.git
    repotype = match
    username = None
    namespace = None
    repo = None

    guesspath, repo = os.path.split(guesspath)
    if not repo.endswith(".git"):
        raise ValueError("Git dir looks to not be a bare repo")
    repo = repo[: -len(".git")]
    if not repo:
        raise ValueError("Gitdir %s seems to not be a bare repo" % gitdir)

    # Split the guesspath up, throwing out any empty strings
    splitguess = [part for part in guesspath.split("/") if part]
    if splitguess and splitguess[0] == "forks":
        if len(splitguess) < 2:
            raise ValueError("Invalid gitdir %s" % gitdir)
        username = splitguess[1]
        splitguess = splitguess[2:]

    if splitguess:
        # At this point, we've cut off the repo name at the end, and any forks/
        # indicators and their usernames are also removed, so remains just the
        # namespace
        namespace = os.path.join(*splitguess)

    # Okay, we think we have everything. Let's make doubly sure the path is
    # correct and exists
    rebuiltpath = os.path.join(
        typepath,
        "forks/" if username else "",
        username if username else "",
        namespace if namespace else "",
        repo + ".git",
    )
    if os.path.normpath(rebuiltpath) != gitdir:
        raise ValueError(
            "Rebuilt %s path not identical to gitdir %s"
            % (rebuiltpath, gitdir)
        )
    if not os.path.exists(rebuiltpath) and not hide_notfound:
        raise ValueError("Splitting gitdir %s failed" % gitdir)

    return (repotype, username, namespace, repo)


def get_repo_name(abspath):
    """Return the name of the git repo based on its path."""
    _, _, _, name = get_repo_info_from_path(abspath)
    return name


def get_repo_namespace(abspath, gitfolder=None):
    """Return the name of the git repo based on its path."""
    _, _, namespace, _ = get_repo_info_from_path(abspath)
    return namespace


def get_username(abspath):
    """Return the username of the git repo based on its path."""
    _, username, _, _ = get_repo_info_from_path(abspath)
    return username


def get_branch_ref(repo, branchname):
    """Return the reference to the specified branch or raises an exception."""
    location = pygit2.GIT_BRANCH_LOCAL
    if branchname not in repo.listall_branches():
        branchname = "origin/%s" % branchname
        location = pygit2.GIT_BRANCH_REMOTE
    branch_ref = repo.lookup_branch(branchname, location)

    if not branch_ref or not branch_ref.resolve():
        raise pagure.exceptions.PagureException(
            "No refs found for %s" % branchname
        )
    return branch_ref.resolve()


def merge_pull_request(session, request, username, domerge=True):
    """Merge the specified pull-request."""
    if domerge:
        _log.info("%s asked to merge the pull-request: %s", username, request)
    else:
        _log.info("%s asked to diff the pull-request: %s", username, request)

    repopath = None
    if request.remote:
        # Get the fork
        repopath = pagure.utils.get_remote_repo_path(
            request.remote_git, request.branch_from
        )
    elif request.project_from:
        # Get the fork
        repopath = pagure.utils.get_repo_path(request.project_from)

    fork_obj = None
    if repopath:
        fork_obj = PagureRepo(repopath)

    with TemporaryClone(request.project, "main", "merge_pr") as tempclone:
        new_repo = tempclone.repo

        # Update the start and stop commits in the DB, one last time
        diff_commits = diff_pull_request(
            session,
            request,
            fork_obj,
            new_repo,
            with_diff=False,
            username=username,
        )
        _log.info("  %s commit to merge", len(diff_commits))

        if request.project.settings.get(
            "Enforce_signed-off_commits_in_pull-request", False
        ):
            for commit in diff_commits:
                if "signed-off-by" not in commit.message.lower():
                    _log.info("  Missing a required: signed-off-by: Bailing")
                    raise pagure.exceptions.PagureException(
                        "This repo enforces that all commits are "
                        "signed off by their author. "
                    )

        if not new_repo.is_empty and not new_repo.head_is_unborn:
            try:
                branch_ref = get_branch_ref(new_repo, request.branch)
            except pagure.exceptions.PagureException:
                branch_ref = None
            if not branch_ref:
                _log.info("  Target branch could not be found")
                raise pagure.exceptions.BranchNotFoundException(
                    "Branch %s could not be found in the repo %s"
                    % (request.branch, request.project.fullname)
                )

            new_repo.checkout(branch_ref)

        if fork_obj:
            # Check/Get the branch from
            branch = None
            try:
                branch = get_branch_ref(fork_obj, request.branch_from)
            except pagure.exceptions.PagureException:
                pass
            if not branch:
                _log.info("  Branch of origin could not be found")
                raise pagure.exceptions.BranchNotFoundException(
                    "Branch %s could not be found in the repo %s"
                    % (
                        request.branch_from,
                        request.project_from.fullname
                        if request.project_from
                        else request.remote_git,
                    )
                )

            # Add the fork as remote repo
            reponame = "%s_%s" % (request.user.user, request.uid)

            _log.info(
                "  Adding remote: %s pointing to: %s", reponame, repopath
            )
            remote = new_repo.create_remote(reponame, repopath)

            # Fetch the commits
            remote.fetch()

            # repo_commit = fork_obj[branch.peel().hex]
            repo_commit = new_repo[branch.peel().hex]

            # Checkout the correct branch
            if new_repo.is_empty or new_repo.head_is_unborn:
                _log.debug(
                    "  target repo is empty, so PR can be merged using "
                    "fast-forward, reporting it"
                )

                if domerge:
                    _log.info("  PR merged using fast-forward")
                    if not request.project.settings.get("always_merge", False):
                        new_repo.create_branch(request.branch, repo_commit)
                        commit = repo_commit.oid.hex
                    else:
                        tree = new_repo.index.write_tree()
                        user_obj = pagure.lib.query.get_user(session, username)
                        commitname = user_obj.fullname or user_obj.user
                        author = _make_signature(
                            commitname, user_obj.default_email
                        )
                        commit = new_repo.create_commit(
                            "refs/heads/%s" % request.branch,
                            author,
                            author,
                            "Merge #%s `%s`" % (request.id, request.title),
                            tree,
                            [repo_commit.oid.hex],
                        )

                    _log.info("  New head: %s", commit)
                    tempclone.push(
                        username,
                        request.branch,
                        request.branch,
                        pull_request=request,
                    )

                    # Update status
                    _log.info("  Closing the PR in the DB")
                    pagure.lib.query.close_pull_request(
                        session, request, username
                    )

                    return "Changes merged!"
                else:
                    _log.info(
                        "  PR can be merged using fast-forward, reporting it"
                    )
                    request.merge_status = "FFORWARD"
                    session.commit()
                    return "FFORWARD"

        else:
            try:
                ref = new_repo.lookup_reference(
                    "refs/pull/%s/head" % request.id
                )
                repo_commit = new_repo[ref.target.hex]
            except KeyError:
                pass

        merge = new_repo.merge(repo_commit.oid)
        _log.debug("  Merge: %s", merge)
        if merge is None:
            mergecode = new_repo.merge_analysis(repo_commit.oid)[0]
            _log.debug("  Mergecode: %s", mergecode)

        # Wait until the last minute then check if the PR was already closed
        # by someone else in the mean while and if so, just bail
        if request.status != "Open":
            _log.info(
                "  This pull-request has already been merged or closed by %s "
                "on %s" % (request.closed_by.user, request.closed_at)
            )
            raise pagure.exceptions.PagureException(
                "This pull-request was merged or closed by %s"
                % request.closed_by.user
            )

        if (merge is not None and merge.is_uptodate) or (  # noqa
            merge is None and mergecode & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE
        ):

            if domerge:
                _log.info("  PR up to date, closing it")
                pagure.lib.query.close_pull_request(session, request, username)
                try:
                    session.commit()
                except SQLAlchemyError:  # pragma: no cover
                    session.rollback()
                    _log.exception("  Could not merge the PR in the DB")
                    raise pagure.exceptions.PagureException(
                        "Could not close this pull-request"
                    )
                raise pagure.exceptions.PagureException(
                    "Nothing to do, changes were already merged"
                )
            else:
                _log.info("  PR up to date, reporting it")
                request.merge_status = "NO_CHANGE"
                session.commit()
                return "NO_CHANGE"

        elif (merge is not None and merge.is_fastforward) or (  # noqa
            merge is None and mergecode & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD
        ):

            if domerge:
                _log.info("  PR merged using fast-forward")
                head = new_repo.lookup_reference("HEAD").peel()
                if not request.project.settings.get("always_merge", False):
                    if merge is not None:
                        # This is depending on the pygit2 version
                        branch_ref.target = merge.fastforward_oid
                    elif merge is None and mergecode is not None:
                        branch_ref.set_target(repo_commit.oid.hex)
                    commit = repo_commit.oid.hex
                else:
                    tree = new_repo.index.write_tree()
                    user_obj = pagure.lib.query.get_user(session, username)
                    commitname = user_obj.fullname or user_obj.user
                    author = _make_signature(
                        commitname, user_obj.default_email
                    )

                    commit_message = "Merge #%s `%s`" % (
                        request.id,
                        request.title,
                    )
                    if request.project.settings.get(
                        "Enforce_signed-off_commits_in_pull-request", False
                    ):
                        commit_message += "\n\nSigned-off-by: %s <%s>" % (
                            commitname,
                            user_obj.default_email,
                        )

                    commit = new_repo.create_commit(
                        "refs/heads/%s" % request.branch,
                        author,
                        author,
                        commit_message,
                        tree,
                        [head.hex, repo_commit.oid.hex],
                    )

                _log.info("  New head: %s", commit)
                tempclone.push(
                    username,
                    branch_ref.name,
                    request.branch,
                    pull_request=request,
                )
            else:
                _log.info(
                    "  PR can be merged using fast-forward, reporting it"
                )
                request.merge_status = "FFORWARD"
                session.commit()
                return "FFORWARD"

        else:
            tree = None
            try:
                tree = new_repo.index.write_tree()
            except pygit2.GitError as err:
                _log.debug(
                    "  Could not write down the new tree: " "merge conflicts"
                )
                _log.debug(err)
                if domerge:
                    _log.info("  Merge conflict: Bailing")
                    raise pagure.exceptions.PagureException("Merge conflicts!")
                else:
                    _log.info("  Merge conflict, reporting it")
                    request.merge_status = "CONFLICTS"
                    session.commit()
                    return "CONFLICTS"

            if domerge:
                if request.project.settings.get(
                    "disable_non_fast-forward_merges", False
                ):
                    _log.info("  Merge non-FF PR is disabled for this project")
                    return "MERGE"
                _log.info("  Writing down merge commit")
                head = new_repo.lookup_reference("HEAD").peel()
                _log.info(
                    "  Basing on: %s - %s", head.hex, repo_commit.oid.hex
                )
                user_obj = pagure.lib.query.get_user(session, username)
                commitname = user_obj.fullname or user_obj.user
                author = _make_signature(commitname, user_obj.default_email)

                commit_message = "Merge #%s `%s`" % (request.id, request.title)
                if request.project.settings.get(
                    "Enforce_signed-off_commits_in_pull-request", False
                ):
                    commit_message += "\n\nSigned-off-by: %s <%s>" % (
                        commitname,
                        user_obj.default_email,
                    )

                commit = new_repo.create_commit(
                    "refs/heads/%s" % request.branch,
                    author,
                    author,
                    commit_message,
                    tree,
                    [head.hex, repo_commit.oid.hex],
                )

                _log.info("  New head: %s", commit)
                local_ref = "refs/heads/_pagure_topush"
                new_repo.create_reference(local_ref, commit)
                tempclone.push(
                    username, local_ref, request.branch, pull_request=request
                )

            else:
                _log.info(
                    "  PR can be merged with a merge commit, " "reporting it"
                )
                request.merge_status = "MERGE"
                session.commit()
                return "MERGE"

    # Update status
    _log.info("  Closing the PR in the DB")
    pagure.lib.query.close_pull_request(session, request, username)

    return "Changes merged!"


def rebase_pull_request(session, request, username):
    """Rebase the specified pull-request.

    Args:
        session (sqlalchemy): the session to connect to the database with
        request (pagure.lib.model.PullRequest): the database object
            corresponding to the pull-request to rebase
        username (string): the name of the user asking for the pull-request
            to be rebased

    Returns: (string or None): Pull-request rebased
    Raises: pagure.exceptions.PagureException

    """
    _log.info("%s asked to rebase the pull-request: %s", username, request)
    user = pagure.lib.query.get_user(session, username)

    if request.remote:
        # Get the fork
        repopath = pagure.utils.get_remote_repo_path(
            request.remote_git, request.branch_from
        )
    elif request.project_from:
        # Get the fork
        repopath = pagure.utils.get_repo_path(request.project_from)
    else:
        _log.info(
            "PR is neither from a remote git repo or an existing local "
            "repo, bailing"
        )
        return

    if not request.project or not os.path.exists(
        pagure.utils.get_repo_path(request.project)
    ):
        _log.info(
            "Could not find the targeted git repository for %s",
            request.project.fullname,
        )
        raise pagure.exceptions.PagureException(
            "Could not find the targeted git repository for %s"
            % request.project.fullname
        )

    with TemporaryClone(
        project=request.project,
        repotype="main",
        action="rebase_pr",
        path=repopath,
    ) as tempclone:
        new_repo = tempclone.repo
        new_repo.checkout("refs/heads/%s" % request.branch_from)

        # Add the upstream repo as remote
        upstream = "%s_%s" % (request.user.user, request.uid)
        upstream_path = pagure.utils.get_repo_path(request.project)
        _log.info(
            "  Adding remote: %s pointing to: %s", upstream, upstream_path
        )
        remote = new_repo.create_remote(upstream, upstream_path)

        # Fetch the commits
        remote.fetch()

        def _run_command(command):
            _log.info("Running command: %s", command)
            try:
                out = subprocess.check_output(
                    command, cwd=tempclone.repopath, stderr=subprocess.STDOUT
                )
                _log.info("   command ran successfully")
                _log.debug("Output: %s" % out)
            except subprocess.CalledProcessError as err:
                _log.debug(
                    "Rebase FAILED: {cmd} returned code {code} with the "
                    "following output: {output}".format(
                        cmd=err.cmd, code=err.returncode, output=err.output
                    )
                )
                raise pagure.exceptions.PagureException(
                    "Did not manage to rebase this pull-request"
                )

        # Configure git for that user
        command = ["git", "config", "user.name", username]
        _run_command(command)
        command = ["git", "config", "user.email", user.default_email]
        _run_command(command)

        # Do the rebase
        command = ["git", "pull", "--rebase", upstream, request.branch]
        _run_command(command)

        # Retrieve the reference of the branch we're working on
        try:
            branch_ref = get_branch_ref(new_repo, request.branch_from)
        except pagure.exceptions.PagureException:
            branch_ref = None
        if not branch_ref:
            _log.debug("  Target branch could not be found")
            raise pagure.exceptions.BranchNotFoundException(
                "Branch %s could not be found in the repo %s"
                % (request.branch, request.project.fullname)
            )

        # Push the changes
        _log.info("Pushing %s to %s", branch_ref.name, request.branch_from)
        try:
            if request.allow_rebase:
                tempclone.push(
                    username,
                    branch_ref.name,
                    request.branch_from,
                    pull_request=request,
                    force=True,
                    internal="yes",
                )
            else:
                tempclone.push(
                    username,
                    branch_ref.name,
                    request.branch_from,
                    pull_request=request,
                    force=True,
                )
        except subprocess.CalledProcessError as err:
            _log.debug(
                "Rebase FAILED: {cmd} returned code {code} with the "
                "following output: {output}".format(
                    cmd=err.cmd, code=err.returncode, output=err.output
                )
            )
            raise pagure.exceptions.PagureException(
                "Did not manage to rebase this pull-request"
            )

    return "Pull-request rebased"


def get_diff_info(repo_obj, orig_repo, branch_from, branch_to, prid=None):
    """Return the info needed to see a diff or make a Pull-Request between
    the two specified repo.

    :arg repo_obj: The pygit2.Repository object of the first git repo
    :arg orig_repo:  The pygit2.Repository object of the second git repo
    :arg branch_from: the name of the branch having the changes, in the
        first git repo
    :arg branch_to: the name of the branch in which we want to merge the
        changes in the second git repo
    :kwarg prid: the identifier of the pull-request to

    """
    try:
        frombranch = repo_obj.lookup_branch(branch_from)
    except ValueError:
        raise pagure.exceptions.BranchNotFoundException(
            "Branch %s does not exist" % branch_from
        )
    except AttributeError:
        frombranch = None
    if not frombranch and prid is None and repo_obj and not repo_obj.is_empty:
        raise pagure.exceptions.BranchNotFoundException(
            "Branch %s does not exist" % branch_from
        )

    branch = None
    if branch_to:
        try:
            branch = orig_repo.lookup_branch(branch_to)
        except ValueError:
            raise pagure.exceptions.BranchNotFoundException(
                "Branch %s does not exist" % branch_to
            )
        local_branches = orig_repo.listall_branches(pygit2.GIT_BRANCH_LOCAL)
        if not branch and local_branches:
            raise pagure.exceptions.BranchNotFoundException(
                "Branch %s could not be found in the target repo" % branch_to
            )

    commitid = None
    if frombranch:
        commitid = frombranch.peel().hex
    elif prid is not None:
        # If there is not branch found but there is a PR open, use the ref
        # of that PR in the main repo
        try:
            ref = orig_repo.lookup_reference("refs/pull/%s/head" % prid)
            commitid = ref.target.hex
        except KeyError:
            pass

    if not commitid and repo_obj and not repo_obj.is_empty:
        raise pagure.exceptions.PagureException(
            "No branch from which to pull or local PR reference were found"
        )

    diff_commits = []
    diff = None
    orig_commit = None

    # If the fork is empty but there is a PR open, use the main repo
    if (not repo_obj or repo_obj.is_empty) and prid is not None:
        repo_obj = orig_repo

    if not repo_obj.is_empty and not orig_repo.is_empty:
        _log.info(
            "pagure.lib.git.get_diff_info: Pulling into a non-empty repo"
        )
        if branch:
            orig_commit = orig_repo[branch.peel().hex]
            main_walker = orig_repo.walk(
                orig_commit.oid.hex, pygit2.GIT_SORT_NONE
            )

        repo_commit = repo_obj[commitid]
        branch_walker = repo_obj.walk(
            repo_commit.oid.hex, pygit2.GIT_SORT_NONE
        )

        main_commits = set()
        branch_commits = set()

        while 1:
            com = None
            if branch:
                try:
                    com = next(main_walker)
                    main_commits.add(com.oid.hex)
                except StopIteration:
                    com = None

            try:
                branch_commit = next(branch_walker)
            except StopIteration:
                branch_commit = None

            # We sure never end up here but better safe than sorry
            if com is None and branch_commit is None:
                break

            if branch_commit:
                branch_commits.add(branch_commit.oid.hex)
                diff_commits.append(branch_commit)
            if main_commits.intersection(branch_commits):
                break

        # If master is ahead of branch, we need to remove the commits
        # that are after the first one found in master
        i = 0
        if diff_commits and main_commits:
            for i in range(len(diff_commits)):
                if diff_commits[i].oid.hex in main_commits:
                    break
            diff_commits = diff_commits[:i]

        _log.debug("Diff commits: %s", diff_commits)
        if diff_commits:
            first_commit = repo_obj[diff_commits[-1].oid.hex]
            if len(first_commit.parents) > 0:
                diff = repo_obj.diff(
                    repo_obj.revparse_single(first_commit.parents[0].oid.hex),
                    repo_obj.revparse_single(diff_commits[0].oid.hex),
                )
            elif first_commit.oid.hex == diff_commits[0].oid.hex:
                _log.info(
                    "pagure.lib.git.get_diff_info: First commit is also the "
                    "last commit"
                )
                diff = diff_commits[0].tree.diff_to_tree(swap=True)

    elif orig_repo.is_empty and repo_obj and not repo_obj.is_empty:
        _log.info("pagure.lib.git.get_diff_info: Pulling into an empty repo")
        if "master" in repo_obj.listall_branches():
            repo_commit = repo_obj[repo_obj.head.target]
        else:
            branch = repo_obj.lookup_branch(branch_from)
            repo_commit = branch.peel()

        for commit in repo_obj.walk(repo_commit.oid.hex, pygit2.GIT_SORT_NONE):
            diff_commits.append(commit)

        _log.debug("Diff commits: %s", diff_commits)
        diff = repo_commit.tree.diff_to_tree(swap=True)
    else:
        raise pagure.exceptions.PagureException(
            "Fork is empty, there are no commits to create a pull "
            "request with"
        )

    _log.info(
        "pagure.lib.git.get_diff_info: diff_commits length: %s",
        len(diff_commits),
    )
    _log.info("pagure.lib.git.get_diff_info: original commit: %s", orig_commit)

    return (diff, diff_commits, orig_commit)


def diff_pull_request(
    session,
    request,
    repo_obj,
    orig_repo,
    with_diff=True,
    notify=True,
    username=None,
):
    """Returns the diff and the list of commits between the two git repos
    mentionned in the given pull-request.

    :arg session: The sqlalchemy session to connect to the database
    :arg request: The pagure.lib.model.PullRequest object of the pull-request
        to look into
    :arg repo_obj: The pygit2.Repository object of the first git repo
    :arg orig_repo:  The pygit2.Repository object of the second git repo
    :arg with_diff: A boolean on whether to return the diff with the list
        of commits (or just the list of commits)
    :arg username: The username of the user diffing the pull-request

    """

    _log.debug("pagure.lib.git.diff_pull_request, started")
    diff = None
    diff_commits = []
    diff, diff_commits, orig_commit = get_diff_info(
        repo_obj,
        orig_repo,
        request.branch_from,
        request.branch,
        prid=request.id,
    )
    _log.debug("pagure.lib.git.diff_pull_request, diff done")

    if request.status == "Open" and diff_commits:
        _log.debug("pagure.lib.git.diff_pull_request, PR open and with a diff")
        first_commit = diff_commits[-1]
        # Check if we can still rely on the merge_status
        commenttext = None
        if (
            request.commit_start != first_commit.oid.hex
            or request.commit_stop != diff_commits[0].oid.hex
        ):
            request.merge_status = None
            if request.commit_start:
                pr_action = "updated"
                new_commits_count = 0
                commenttext = ""
                for i in diff_commits:
                    if i.oid.hex == request.commit_stop:
                        break
                    new_commits_count = new_commits_count + 1
                    commenttext = "%s * ``%s``\n" % (
                        commenttext,
                        i.message.strip().split("\n")[0],
                    )
                if new_commits_count == 1:
                    commenttext = "**%d new commit added**\n\n%s" % (
                        new_commits_count,
                        commenttext,
                    )
                else:
                    commenttext = "**%d new commits added**\n\n%s" % (
                        new_commits_count,
                        commenttext,
                    )
            if (
                request.commit_start
                and request.commit_start != first_commit.oid.hex
            ):
                pr_action = "rebased"
                if orig_commit:
                    commenttext = "rebased onto %s" % orig_commit.oid.hex
                else:
                    commenttext = "rebased onto unknown target"
        request.commit_start = first_commit.oid.hex
        request.commit_stop = diff_commits[0].oid.hex
        session.add(request)
        session.commit()
        _log.debug(
            "pagure.lib.git.diff_pull_request, commenttext: %s", commenttext
        )

        pagure.lib.tasks.sync_pull_ref.delay(
            request.project.name,
            request.project.namespace,
            request.project.user.username if request.project.is_fork else None,
            request.id,
        )

        if commenttext:
            pagure.lib.tasks.link_pr_to_ticket.delay(request.uid)
            if notify:
                if pr_action:
                    pagure.lib.notify.log(
                        request.project,
                        topic="pull-request.%s" % pr_action,
                        msg=dict(
                            pullrequest=request.to_json(
                                with_comments=False, public=True
                            ),
                            agent="pagure",
                        ),
                    )
                _log.debug(
                    "pagure.lib.git.diff_pull_request: adding notification: %s"
                    "as user: %s",
                    commenttext,
                    username or request.user.username,
                )
                pagure.lib.query.add_pull_request_comment(
                    session,
                    request,
                    commit=None,
                    tree_id=None,
                    filename=None,
                    row=None,
                    comment="%s" % commenttext,
                    user=username or request.user.username,
                    notify=False,
                    notification=True,
                )
                session.commit()
        else:
            pagure.lib.git.update_git(request, repo=request.project)

    if with_diff:
        return (diff_commits, diff)
    else:
        return diff_commits


def update_pull_ref(request, repo):
    """Create or update the refs/pull/ reference in the git repo."""

    repopath = pagure.utils.get_repo_path(request.project)
    reponame = "%s_%s" % (request.user.user, request.uid)

    _log.info("  Adding remote: %s pointing to: %s", reponame, repopath)
    rc = RemoteCollection(repo)

    try:
        # we do rc.delete(reponame) both here and in the finally block below:
        # * here: it's useful for cases when worker was interrupted
        #   on the previous execution of this function and didn't manage
        #   to remove the ref
        # * in the finally clause: to remove the ref so that it doesn't stay
        #   in the fork forever (as noted above, it might still stay there
        #   if the worker gets interrupted, but that's not a huge deal)
        rc[reponame]
        rc.delete(reponame)
    except KeyError:
        pass

    remote = rc.create(reponame, repopath)
    try:
        _log.info(
            "  Pushing refs/heads/%s to refs/pull/%s/head",
            request.branch_from,
            request.id,
        )
        refname = "+refs/heads/%s:refs/pull/%s/head" % (
            request.branch_from,
            request.id,
        )
        PagureRepo.push(remote, refname)
    finally:
        rc.delete(reponame)


def get_git_tags(project, with_commits=False):
    """Returns the list of tags created in the git repositorie of the
    specified project.
    """
    repopath = pagure.utils.get_repo_path(project)
    repo_obj = PagureRepo(repopath)

    if with_commits:
        tags = {}
        for tag in repo_obj.listall_references():
            if tag.startswith("refs/tags/"):
                ref = repo_obj.lookup_reference(tag)
                if ref:
                    com = ref.peel()
                    if com:
                        tags[tag.split("refs/tags/")[1]] = com.oid.hex
    else:
        tags = [
            tag.split("refs/tags/")[1]
            for tag in repo_obj.listall_references()
            if tag.startswith("refs/tags/")
        ]

    return tags


def new_git_tag(project, tagname, target, user, message=str(), force=False):
    """Create a new git tag in the git repositorie of the specified project.

    :arg project: the project in which we want to create a git tag
    :type project: pagure.lib.model.Project
    :arg tagname: the name of the tag to create
    :type tagname: str
    :arg user: the user creating the tag
    :type user: pagure.lib.model.User
    :kwarg message: the message to include in the annotation of the tag
    :type message: str or None
    :kwarg force: a boolean specifying wether to force the creation of
        the git tag or not
    :type message: bool
    """
    repopath = pagure.utils.get_repo_path(project)
    repo_obj = PagureRepo(repopath)

    target_obj = repo_obj.get(target)
    if not target_obj:
        raise pygit2.GitError("Unknown target: %s" % target)

    if force:
        existing_tag = repo_obj.lookup_reference("refs/tags/%s" % tagname)
        if existing_tag:
            existing_tag.delete()

    tag = repo_obj.create_tag(
        tagname,
        target,
        target_obj.type,
        pygit2.Signature(user.fullname, user.default_email),
        message if message else str(),
    )

    return tag


def get_git_tags_objects(project):
    """Returns the list of references of the tags created in the git
    repositorie the specified project.
    The list is sorted using the time of the commit associated to the tag"""
    repopath = pagure.utils.get_repo_path(project)
    repo_obj = PagureRepo(repopath)
    tags = {}
    for tag in repo_obj.listall_references():
        if "refs/tags/" in tag and repo_obj.lookup_reference(tag):
            commit_time = None
            try:
                theobject = repo_obj[repo_obj.lookup_reference(tag).target]
            except ValueError:
                theobject = None
            objecttype = ""
            if isinstance(theobject, pygit2.Tag):
                underlying_obj = theobject.peel(pygit2.Commit)
                commit_time = underlying_obj.commit_time
                objecttype = "tag"
            elif isinstance(theobject, pygit2.Commit):
                commit_time = theobject.commit_time
                objecttype = "commit"

            tags[commit_time] = {
                "object": theobject,
                "tagname": tag.replace("refs/tags/", ""),
                "date": commit_time,
                "objecttype": objecttype,
                "head_msg": None,
                "body_msg": None,
            }
            if objecttype == "tag":
                head_msg, _, body_msg = tags[commit_time][
                    "object"
                ].message.partition("\n")
                if body_msg.strip().endswith("\n-----END PGP SIGNATURE-----"):
                    body_msg = body_msg.rsplit(
                        "-----BEGIN PGP SIGNATURE-----", 1
                    )[0].strip()
                tags[commit_time]["head_msg"] = head_msg
                tags[commit_time]["body_msg"] = body_msg
    sorted_tags = []

    for tag in sorted(tags, reverse=True):
        sorted_tags.append(tags[tag])

    return sorted_tags


def log_commits_to_db(session, project, commits, gitdir):
    """Log the given commits to the DB."""
    repo_obj = PagureRepo(gitdir)

    for commitid in commits:
        try:
            commit = repo_obj[commitid]
        except ValueError:
            continue

        try:
            author_obj = pagure.lib.query.get_user(
                session, commit.author.email
            )
        except pagure.exceptions.PagureException:
            author_obj = None

        date_created = arrow.get(commit.commit_time)

        log = model.PagureLog(
            user_id=author_obj.id if author_obj else None,
            user_email=commit.author.email if not author_obj else None,
            project_id=project.id,
            log_type="committed",
            ref_id=commit.oid.hex,
            date=date_created.date(),
            date_created=date_created.datetime,
        )
        session.add(log)


def reinit_git(project, repofolder):
    """Delete and recreate a git folder
    :args project: SQLAlchemy object of the project
    :args folder: The folder which contains the git repos
    like TICKETS_FOLDER for tickets and REQUESTS_FOLDER for
    pull requests
    """

    repo_path = os.path.join(repofolder, project.path)
    if not os.path.exists(repo_path):
        return

    # delete that repo
    shutil.rmtree(repo_path)

    # create it again
    pygit2.init_repository(
        repo_path, bare=True, mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP
    )


def get_git_branches(project, with_commits=False):
    """Return a list of branches for the project
    :arg project: The Project instance to get the branches for
    :arg with_commits: Whether we should return branch head commits or not
    """
    repo_path = pagure.utils.get_repo_path(project)
    repo_obj = PagureRepo(repo_path)

    if with_commits:
        branches = {}

        for branch in repo_obj.listall_branches():
            resolved_branch = repo_obj.lookup_branch(branch).resolve()
            com = resolved_branch.peel()
            if com:
                branches[branch] = com.oid.hex
    else:
        branches = repo_obj.listall_branches()

    return branches


def get_default_git_branches(project):
    """Return a tuple of the default branchname and its head commit hash
    :arg project: The Project instance to get the branches for
    """
    repo_path = pagure.utils.get_repo_path(project)
    repo_obj = PagureRepo(repo_path)
    branchname = repo_obj.head.shorthand
    branch = repo_obj.lookup_branch(branchname)
    commit = branch.peel(pygit2.Commit)

    return branchname, commit.oid.hex


def new_git_branch(
    username, project, branch, from_branch=None, from_commit=None
):
    """Create a new git branch on the project
    :arg project: The Project instance to get the branches for
    :arg from_branch: The branch to branch off of
    """
    with TemporaryClone(project, "main", "new_branch") as tempclone:
        repo_obj = tempclone.repo

        if not from_branch and not from_commit:
            from_branch = "master"
        branches = repo_obj.listall_branches()

        if from_branch:
            if from_branch not in branches:
                raise pagure.exceptions.PagureException(
                    'The "{0}" branch does not exist'.format(from_branch)
                )
            parent = get_branch_ref(repo_obj, from_branch).peel()
        else:
            if from_commit not in repo_obj:
                raise pagure.exceptions.PagureException(
                    'The commit "{0}" does not exist'.format(from_commit)
                )
            parent = repo_obj[from_commit]

        if branch not in branches:
            repo_obj.create_branch(branch, parent)
        else:
            raise pagure.exceptions.PagureException(
                'The branch "{0}" already exists'.format(branch)
            )

        tempclone.push(username, branch, branch)


def git_set_ref_head(project, branch):
    """Set the HEAD reference of the project
    :arg project: The project instance to set the HEAD reference
    :arg branch: The branch to be set as HEAD reference
    """
    repo_path = pagure.utils.get_repo_path(project)
    repo_obj = PagureRepo(repo_path)

    reference = repo_obj.lookup_reference("refs/heads/%s" % branch).resolve()
    repo_obj.set_head(reference.name)


def get_branch_aliases(project):
    """Iterates through the references of the provided git repo to extract all
    of its aliases.
    """
    repo_path = pagure.utils.get_repo_path(project)
    repo_obj = PagureRepo(repo_path)

    output = {}
    for ref in repo_obj.listall_reference_objects():
        if "refs/heads/" in str(ref.target):
            output[ref.name] = ref.target
    return output


def set_branch_alias(project, source, dest):
    """Create a reference in the provided git repo from the source reference
    to the dest one.
    """
    repo_path = pagure.utils.get_repo_path(project)
    repo_obj = PagureRepo(repo_path)

    # Check that the source reference exists
    repo_obj.lookup_reference("refs/heads/{}".format(dest))

    try:
        repo_obj.create_reference(
            "refs/heads/{}".format(source),
            "refs/heads/{}".format(dest),
        )
    except ValueError as err:
        _log.debug(
            "Failed to create alias from %s to %s -- %s", source, dest, err
        )
        raise pagure.exceptions.PagureException(
            "Could not create alias from {0} to {1}. "
            "Reference already existing?".format(source, dest)
        )


def drop_branch_aliases(project, source, dest):
    """Delete a reference in the provided git repo from the source reference
    to the dest one.
    """
    repo_path = pagure.utils.get_repo_path(project)
    repo_obj = PagureRepo(repo_path)

    ref = repo_obj.lookup_reference("refs/heads/{}".format(dest))
    output = False
    if ref.target == "refs/heads/{}".format(source):
        ref_file = os.path.join(repo_obj.path, ref.name)
        if os.path.exists(ref_file):
            os.unlink(ref_file)
            output = True
    return output


def delete_project_repos(project):
    """Deletes the actual git repositories on disk

    Args:
        project (Project): Project to delete repos for
    """
    for repotype in pagure.lib.query.get_repotypes():
        repopath = project.repopath(repotype)
        if repopath is None:
            continue

        try:
            shutil.rmtree(repopath)
        except Exception:
            _log.exception(
                "Failed to remove repotype %s for %s",
                repotype,
                project.fullname,
            )


def set_up_project_hooks(project, hook=None):
    """Makes sure the git repositories for a project have their hooks setup.

    Args:
        project (model.Project): Project to set up hooks for
    """
    # Create hooks locally
    pagure.hooks.BaseHook.set_up(project)


def _create_project_repo(project, templ, ignore_existing, repotype):
    """Creates a single specific git repository on disk

    Args:
        project (Project): Project to create repos for
        templ (string): Template directory
        ignore_existing (bool): Whether a repo already existing is fatal
        repotype (string): Repotype to create
    Returns: (string or None): Directory created
    """
    repodir = project.repopath(repotype)
    if repodir is None:
        # This repo type is disabled
        return None
    if os.path.exists(repodir):
        if not ignore_existing:
            raise pagure.exceptions.RepoExistsException(
                "The %s repo %s already exists" % (repotype, project.path)
            )
        else:
            return None

    if repotype == "main":
        pygit2.init_repository(repodir, bare=True, template_path=templ)

        if not project.private:
            # Make the repo exportable via apache
            http_clone_file = os.path.join(repodir, "git-daemon-export-ok")
            if not os.path.exists(http_clone_file):
                with open(http_clone_file, "w"):
                    pass
    else:
        pygit2.init_repository(
            repodir,
            bare=True,
            mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP,
        )

    return repodir


def create_project_repos(project, templ, ignore_existing):
    """Creates the actual git repositories on disk

    Args:
        project (Project): Project to create repos for
        templ (string): Template directory
        ignore_existing (bool): Whether a repo already existing is fatal
    """
    created_dirs = []

    try:
        for repotype in pagure.lib.query.get_repotypes():
            created = _create_project_repo(
                project, templ, ignore_existing, repotype
            )
            if created:
                created_dirs.append(created)
    except Exception:
        for created in created_dirs:
            shutil.rmtree(created)
        raise

    set_up_project_hooks(project)


def get_stats_patch(patch):
    """Returns some statistics about a given patch.

    These stats include:
        status: if the file was added (A), deleted (D), modified (M) or
            renamed (R)
        old_path: the path to the old file
        new_path: the path to the new file
        lines_added: the number of lines added in this patch
        lines_removed: the number of lines removed in this patch

    All these information are returned in a dict.

    Args:
        patch (pygit2.Patch): the patch object to get stats on
    Returns: a dict with the stats described above
    Raises (pagure.exceptions.PagureException): if for some reason (likely
        a change in pygit2's API) this function does not manage to gather
        all the stats it should

    """

    output = {
        "lines_added": patch.line_stats[1],
        "lines_removed": patch.line_stats[2],
        "new_path": None,
        "old_path": None,
        "status": None,
        "new_id": None,
        "old_id": None,
    }
    if hasattr(patch, "new_file_path"):
        # Older pygit2
        status = patch.status
        if patch.new_file_path != patch.old_file_path:
            status = "R"
        output["status"] = status
        output["new_path"] = patch.new_file_path
        output["old_path"] = patch.old_file_path
        output["new_id"] = str(patch.new_id)
        output["old_id"] = str(patch.old_id)
    elif hasattr(patch, "delta"):
        status = None
        # Newer pygit2
        # we recognize non-executable file, executable file and symlink
        expected_modes = [33188, 33261, 40960]
        if (
            patch.delta.new_file.mode == 0
            and patch.delta.old_file.mode in expected_modes
        ):
            status = "D"
        elif (
            patch.delta.new_file.mode in expected_modes
            and patch.delta.old_file.mode == 0
        ):
            status = "A"
        elif (
            patch.delta.new_file.mode in expected_modes
            and patch.delta.old_file.mode in expected_modes
        ):
            status = "M"
        if patch.delta.new_file.path != patch.delta.old_file.path:
            status = "R"

        output["status"] = status
        output["new_path"] = patch.delta.new_file.path
        output["new_id"] = str(patch.delta.new_file.id)
        output["old_path"] = patch.delta.old_file.path
        output["old_id"] = str(patch.delta.old_file.id)

    if None in output.values():  # pragma: no-cover
        raise pagure.exceptions.PagureException(
            "Unable to properly retrieve the stats for this patch"
        )

    return output


def generate_archive(project, commit, tag, name, archive_fmt):
    """Generate the desired archive of the specified project for the
    specified commit with the given name and archive format.

    Args:
        project (pagure.lib.model.Project): the project's repository from
            which to generate the archive
        commit (str): the commit hash to generate the archive of
        name (str): the name to give to the archive
        archive_fmt (str): the format of the archive to generate, can be
            either gzip or tag or tar.gz
    Returns: None
    Raises (pagure.exceptions.PagureException): if an un-supported archive
        format is specified

    """

    def _exclude_git(filename):
        return ".git" in filename

    with TemporaryClone(project, "main", "archive", parent=name) as tempclone:
        repo_obj = tempclone.repo
        commit_obj = repo_obj[commit]
        repo_obj.checkout_tree(commit_obj.tree)
        archive_folder = pagure_config.get("ARCHIVE_FOLDER")

        tag_path = ""
        if tag:
            tag_path = os.path.join("tags", tag)
        target_path = os.path.join(
            archive_folder, project.fullname, tag_path, commit
        )
        if not os.path.exists(target_path):
            _log.info("Creating folder: %s", target_path)
            os.makedirs(target_path)
        fullpath = os.path.join(target_path, name)

        if archive_fmt == "tar":
            with tarfile.open(name=fullpath + ".tar", mode="w") as tar:
                tar.add(
                    name=tempclone.repopath, exclude=_exclude_git, arcname=name
                )
        elif archive_fmt == "tar.gz":
            with tarfile.open(name=fullpath + ".tar.gz", mode="w:gz") as tar:
                tar.add(
                    name=tempclone.repopath, exclude=_exclude_git, arcname=name
                )
        elif archive_fmt == "zip":
            # Code from /usr/lib64/python2.7/zipfile.py adjusted for our
            # needs
            def addToZip(zf, path, zippath):
                if _exclude_git(path):
                    return
                if os.path.isfile(path):
                    zf.write(path, zippath, zipfile.ZIP_DEFLATED)
                elif os.path.isdir(path):
                    if zippath:
                        zf.write(path, zippath)
                    for nm in os.listdir(path):
                        if _exclude_git(path):
                            continue
                        addToZip(
                            zf,
                            os.path.join(path, nm),
                            os.path.join(zippath, nm),
                        )

            with zipfile.ZipFile(fullpath + ".zip", "w") as zipstream:
                addToZip(zipstream, tempclone.repopath, name)
        else:
            raise pagure.exceptions.PagureException(
                "Un-support archive format requested: %s", archive_fmt
            )


def mirror_pull_project(session, project, debug=False):
    """Mirror locally a project from a remote URL."""
    remote = project.mirrored_from
    if not remote:
        _log.info("No remote found, ignoring")
        return
    repopath = tempfile.mkdtemp(prefix="pagure-mirror_in-")
    lclrepopath = pagure.utils.get_repo_path(project)

    def _run_command(command, logs):
        _log.info("Running the command: %s" % command)
        if debug:
            print("Running the command: %s" % command)
            print("  Running in: %s" % repopath)
        (stdout, stderr) = pagure.lib.git.read_git_lines(
            command, abspath=repopath, error=True
        )
        log = "Output from %s:\n  stdout: %s\n  stderr: %s" % (
            command,
            stdout,
            stderr,
        )
        logs.append(log)
        if debug:
            print(log)
        return logs

    try:
        # Pull
        logs = ["Run from: %s" % datetime.datetime.utcnow().isoformat()]
        logs = _run_command(["clone", "--mirror", remote, "."], logs)
        logs = _run_command(["remote", "add", "local", lclrepopath], logs)

        # Push the changes
        _log.info("Pushing")
        if debug:
            print("Pushing to the local git repo")
        extra = {}
        command = ["git", "push", "local", "--mirror"]
        environ = {}

        _log.debug("Running a git push to %s", project.fullname)
        env = os.environ.copy()
        env["GL_USER"] = "pagure"
        env["GL_BYPASS_ACCESS_CHECKS"] = "1"
        env["internal"] = "yes"
        if pagure_config.get("GITOLITE_HOME"):
            env["HOME"] = pagure_config["GITOLITE_HOME"]
        env.update(environ)
        env.update(extra)
        out = subprocess.check_output(
            command, cwd=repopath, stderr=subprocess.STDOUT, env=env
        ).decode("utf-8")
        log = "Output from %s:" % command
        logs.append(log)
        logs.append(out)
        _log.debug("Output: %s" % out)

        project.mirrored_from_last_log = "\n".join(logs)
        session.add(project)
        session.commit()
        _log.info("\n".join(logs))
    except subprocess.CalledProcessError as err:
        _log.debug(
            "Rebase FAILED: {cmd} returned code {code} with the "
            "following output: {output}".format(
                cmd=err.cmd, code=err.returncode, output=err.output
            )
        )
        # This should never really happen, since we control the repos, but
        # this way, we can be sure to get the output logged
        remotes = []
        for line in err.output.decode("utf-8").split("\n"):
            _log.info("Remote line: %s", line)
            if line.startswith("remote: "):
                _log.debug("Remote: %s" % line)
                remotes.append(line[len("remote: ") :].strip())
        if remotes:
            _log.info("Remote rejected with: %s" % remotes)
            raise pagure.exceptions.PagurePushDenied(
                "Remote hook declined the push: %s" % "\n".join(remotes)
            )
        else:
            # Something else happened, pass the original
            _log.exception("Error pushing. Output: %s", err.output)
            raise
    finally:
        shutil.rmtree(repopath)
