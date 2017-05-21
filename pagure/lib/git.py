# -*- coding: utf-8 -*-

"""
 (c) 2015-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-many-branches
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# pylint: disable=too-many-lines

import datetime
import json
import logging
import os
import shutil
import subprocess
import tempfile

import arrow
import pygit2
import werkzeug

from sqlalchemy.exc import SQLAlchemyError
import pagure
import pagure.exceptions
import pagure.lib
import pagure.lib.notify
from pagure.lib import model
from pagure.lib.repo import PagureRepo
from pagure.lib import tasks


_log = logging.getLogger(__name__)


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
    _log.info('Write down the gitolite configuration file')
    global_pr_only = pagure.APP.config.get('PR_ONLY', False)
    config = []
    groups = {}
    query = session.query(
        model.Project
    ).order_by(
        model.Project.id
    )
    for project in query.all():
        _log.debug('    Processing project: %s', project.fullname)
        for group in project.committer_groups:
            if group.group_name not in groups:
                groups[group.group_name] = [
                    user.username for user in group.users]

        # Check if the project or the pagure instance enforce the PR only
        # development model.
        pr_only = project.settings.get('pull_request_access_only', False)

        for repos in ['repos', 'docs/', 'tickets/', 'requests/']:
            if repos == 'repos':
                # Do not grant access to project enforcing the PR model
                if pr_only or (global_pr_only and not project.is_fork):
                    continue
                repos = ''

            config.append('repo %s%s' % (repos, project.fullname))
            if repos not in ['tickets/', 'requests/']:
                config.append('  R   = @all')
            if project.committer_groups:
                config.append('  RW+ = @%s' % ' @'.join([
                    group.group_name for group in project.committer_groups]))
            config.append('  RW+ = %s' % project.user.user)
            for user in project.committers:
                if user != project.user:
                    config.append('  RW+ = %s' % user.user)
            for deploykey in project.deploykeys:
                access = 'R'
                if deploykey.pushaccess:
                    access = 'RW+'
                # Note: the replace of / with _ is because gitolite users can't
                # contain a /. At first, this might look like deploy keys in a
                # project called $namespace_$project would give access to the
                # repos of a project $namespace/$project or vica versa, however
                # this is NOT the case because we add the deploykey.id to the
                # end of the deploykey name, which means it is unique. The
                # project name is solely there to make it easier to determine
                # what project created the deploykey for admins.
                config.append('  %s = deploykey_%s_%s' %
                              (access,
                               werkzeug.secure_filename(project.fullname),
                               deploykey.id))
            config.append('')

    with open(configfile, 'w') as stream:
        for key, users in groups.iteritems():
            stream.write('@%s   = %s\n' % (key, ' '.join(users)))
        stream.write('\n')

        for row in config:
            stream.write(row + '\n')


def _get_gitolite_command():
    """ Return the gitolite command to run based on the info in the
    configuration file.
    """
    _log.info('Compiling the gitolite configuration')
    gitolite_folder = pagure.APP.config.get('GITOLITE_HOME', None)
    gitolite_version = pagure.APP.config.get('GITOLITE_VERSION', 3)
    if gitolite_folder:
        if gitolite_version == 2:
            cmd = 'GL_RC=%s GL_BINDIR=%s gl-compile-conf' % (
                pagure.APP.config.get('GL_RC'),
                pagure.APP.config.get('GL_BINDIR')
            )
        elif gitolite_version == 3:
            cmd = 'HOME=%s gitolite compile && HOME=%s gitolite trigger '\
                'POST_COMPILE' % (
                    pagure.APP.config.get('GITOLITE_HOME'),
                    pagure.APP.config.get('GITOLITE_HOME')
                )
        else:
            raise pagure.exceptions.PagureException(
                'Non-supported gitolite version "%s"' % gitolite_version
            )
        _log.debug('Command: %s', cmd)
        return cmd


def generate_gitolite_acls():
    tasks.generate_gitolite_acls.delay()


def _generate_gitolite_acls():
    """ Generate the gitolite configuration file for all repos
    """
    _log.info('Refresh gitolite configuration')
    pagure.lib.git.write_gitolite_acls(
        pagure.SESSION, pagure.APP.config['GITOLITE_CONFIG'])

    cmd = _get_gitolite_command()
    if cmd:
        subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=pagure.APP.config['GITOLITE_HOME']
        )


def update_git(obj, repo, repofolder):
    """ Schedules an update_repo task after determining arguments. """
    ticketuid = None
    requestuid = None
    if obj.isa == 'issue':
        ticketuid = obj.uid
    elif obj.isa == 'pull-request':
        requestuid = obj.uid
    else:
        raise NotImplementedError('Unknown object type %s' % obj.isa)

    return pagure.lib.tasks.update_git.delay(
        repo.name, repo.namespace,
        repo.user.username if repo.is_fork else None,
        ticketuid, requestuid)


def _update_git(obj, repo, repofolder):
    """ Update the given issue in its git.

    This method forks the provided repo, add/edit the issue whose file name
    is defined by the uid field of the issue and if there are additions/
    changes commit them and push them back to the original repo.

    """
    _log.info('Update the git repo: %s for: %s', repo.path, obj)

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
        stream.write(json.dumps(
            obj.to_json(), sort_keys=True, indent=4,
            separators=(',', ': ')))

    # Retrieve the list of files that changed
    diff = new_repo.diff()
    files = []
    for patch in diff:
        if hasattr(patch, 'new_file_path'):
            files.append(patch.new_file_path)
        elif hasattr(patch, 'delta'):
            files.append(patch.delta.new_file.path)

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
        'Updated %s %s: %s' % (obj.isa, obj.uid, obj.title),
        new_repo.index.write_tree(),
        parents)
    index.write()

    # Push to origin
    ori_remote = new_repo.remotes[0]
    master_ref = new_repo.lookup_reference('HEAD').resolve()
    refname = '%s:%s' % (master_ref.name, master_ref.name)

    PagureRepo.push(ori_remote, refname)

    # Remove the clone
    shutil.rmtree(newpath)


def clean_git(obj, repo, repofolder):
    user = None
    ticketuid = obj.uid

    if repo.is_fork:
        user = repo.user

    return pagure.lib.tasks.clean_git.delay(
        repo.name, repo.namespace, user.username, ticketuid)


def _clean_git(obj, repo, repofolder):
    """ Update the given issue remove it from its git.

    """

    if not repofolder:
        return

    _log.info('Update the git repo: %s to remove: %s', repo.path, obj)

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

    # Add the changes to the index
    index.remove(obj.uid)

    # See if there is a parent to this commit
    parent = None
    if not new_repo.is_empty:
        parent = new_repo.head.get_object().oid

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
        'Removed %s %s: %s' % (obj.isa, obj.uid, obj.title),
        new_repo.index.write_tree(),
        parents)
    index.write()

    # Push to origin
    ori_remote = new_repo.remotes[0]
    master_ref = new_repo.lookup_reference('HEAD').resolve()
    refname = '%s:%s' % (master_ref.name, master_ref.name)

    PagureRepo.push(ori_remote, refname)

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
            keydir=pagure.APP.config.get('GITOLITE_KEYDIR', None),
        )
        session.commit()

    return user


def get_project_from_json(
        session, jsondata,
        gitfolder, docfolder, ticketfolder, requestfolder):
    """ From the given json blob, retrieve the project info and search for
    it in the db and create the projec if it does not already exist.
    """
    project = None

    user = get_user_from_json(session, jsondata)
    name = jsondata.get('name')
    namespace = jsondata.get('namespace')
    project_user = None
    if jsondata.get('parent'):
        project_user = user.username
    project = pagure.lib._get_project(
        session, name, user=project_user, namespace=namespace)

    if not project:
        parent = None
        if jsondata.get('parent'):
            parent = get_project_from_json(
                session, jsondata.get('parent'),
                gitfolder, docfolder, ticketfolder, requestfolder)

            pagure.lib.fork_project(
                session=session,
                repo=parent,
                gitfolder=pagure.APP.config['GIT_FOLDER'],
                docfolder=pagure.APP.config['DOCS_FOLDER'],
                ticketfolder=pagure.APP.config['TICKETS_FOLDER'],
                requestfolder=pagure.APP.config['REQUESTS_FOLDER'],
                user=user.username)

        else:
            gitfolder = os.path.join(
                gitfolder, 'forks', user.username) if parent else gitfolder
            pagure.lib.new_project(
                session,
                user=user.username,
                name=name,
                namespace=namespace,
                description=jsondata.get('description'),
                parent_id=parent.id if parent else None,
                blacklist=pagure.APP.config.get('BLACKLISTED_PROJECTS', []),
                allowed_prefix=pagure.APP.config.get('ALLOWED_PREFIX', []),
                gitfolder=gitfolder,
                docfolder=docfolder,
                ticketfolder=ticketfolder,
                requestfolder=requestfolder,
                prevent_40_chars=pagure.APP.config.get(
                    'OLD_VIEW_COMMIT_ENABLED', False),
            )

        session.commit()
        project = pagure.lib._get_project(
            session, name, user=user.username, namespace=namespace)

        tags = jsondata.get('tags', None)
        if tags:
            pagure.lib.add_tag_obj(
                session, project, tags=tags, user=user.username,
                ticketfolder=None)

    return project


def update_custom_field_from_json(session, repo, issue, json_data):
    ''' Update the custom fields according to the custom fields of
    the issue. If the custom field is not present for the repo in
    it's settings, this will create them.

    :arg session: the session to connect to the database with.
    :arg repo: the sqlalchemy object of the project
    :arg issue: the sqlalchemy object of the issue
    :arg json_data: the json representation of the issue taken from the git
        and used to update the data in the database.
    '''

    # Update custom key value, if present
    custom_fields = json_data.get('custom_fields')
    if not custom_fields:
        return

    current_keys = []
    for key in repo.issue_keys:
        current_keys.append(key.name)

    for new_key in custom_fields:
        if new_key['name'] not in current_keys:
            issuekey = model.IssueKeys(
                project_id=repo.id,
                name=new_key['name'],
                key_type=new_key['key_type'],
            )
            try:
                session.add(issuekey)
                session.commit()
            except SQLAlchemyError:
                session.rollback()
                continue

        # The key should be present in the database now
        key_obj = pagure.lib.get_custom_key(session, repo, new_key['name'])

        value = new_key.get('value')
        if value:
            value = value.strip()
        pagure.lib.set_custom_key_value(
            session,
            issue=issue,
            key=key_obj,
            value=value,
        )
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()


def update_ticket_from_git(
        session, reponame, namespace, username, issue_uid, json_data):
    """ Update the specified issue (identified by its unique identifier)
    with the data present in the json blob provided.

    :arg session: the session to connect to the database with.
    :arg repo: the name of the project to update
    :arg issue_uid: the unique identifier of the issue to update
    :arg json_data: the json representation of the issue taken from the git
        and used to update the data in the database.

    """

    repo = pagure.lib._get_project(
        session, reponame, user=username, namespace=namespace)

    if not repo:
        raise pagure.exceptions.PagureException(
            'Unknown repo %s of username: %s in namespace: %s' % (
                reponame, username, namespace))

    user = get_user_from_json(session, json_data)

    issue = pagure.lib.get_issue_by_uid(session, issue_uid=issue_uid)
    messages = []
    if not issue:
        # Create new issue
        pagure.lib.new_issue(
            session,
            repo=repo,
            title=json_data.get('title'),
            content=json_data.get('content'),
            priority=json_data.get('priority'),
            user=user.username,
            ticketfolder=None,
            issue_id=json_data.get('id'),
            issue_uid=issue_uid,
            private=json_data.get('private'),
            status=json_data.get('status'),
            close_status=json_data.get('close_status'),
            date_created=datetime.datetime.utcfromtimestamp(
                float(json_data.get('date_created'))),
            notify=False,
        )

    else:
        # Edit existing issue
        msgs = pagure.lib.edit_issue(
            session,
            issue=issue,
            ticketfolder=None,
            user=user.username,
            title=json_data.get('title'),
            content=json_data.get('content'),
            priority=json_data.get('priority'),
            status=json_data.get('status'),
            close_status=json_data.get('close_status'),
            private=json_data.get('private'),
        )
        if msgs:
            messages.extend(msgs)

    session.commit()

    issue = pagure.lib.get_issue_by_uid(session, issue_uid=issue_uid)

    update_custom_field_from_json(
        session,
        repo=repo,
        issue=issue,
        json_data=json_data,
    )

    # Update milestone
    milestone = json_data.get('milestone')

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
        msgs = pagure.lib.edit_issue(
            session,
            issue=issue,
            ticketfolder=None,
            user=user.username,
            milestone=milestone,
            title=json_data.get('title'),
            content=json_data.get('content'),
            status=json_data.get('status'),
            close_status=json_data.get('close_status'),
            private=json_data.get('private'),
        )
        if msgs:
            messages.extend(msgs)
    except SQLAlchemyError:
        session.rollback()

    # Update close_status
    close_status = json_data.get('close_status')

    if close_status:
        if close_status.strip() not in repo.close_status:
            try:
                repo.close_status.append(close_status.strip())
                session.add(repo)
                session.commit()
            except SQLAlchemyError:
                session.rollback()

    # Update tags
    tags = json_data.get('tags', [])
    msgs = pagure.lib.update_tags(
        session, issue, tags, username=user.user, ticketfolder=None)
    if msgs:
        messages.extend(msgs)

    # Update assignee
    assignee = get_user_from_json(session, json_data, key='assignee')
    if assignee:
        msg = pagure.lib.add_issue_assignee(
            session, issue, assignee.username,
            user=user.user, ticketfolder=None, notify=False)
        if msg:
            messages.append(msg)

    # Update depends
    depends = json_data.get('depends', [])
    msgs = pagure.lib.update_dependency_issue(
        session, issue.project, issue, depends,
        username=user.user, ticketfolder=None)
    if msgs:
        messages.extend(msgs)

    # Update blocks
    blocks = json_data.get('blocks', [])
    msgs = pagure.lib.update_blocked_issue(
        session, issue.project, issue, blocks,
        username=user.user, ticketfolder=None)
    if msgs:
        messages.extend(msgs)

    for comment in json_data['comments']:
        usercomment = get_user_from_json(session, comment)
        commentobj = pagure.lib.get_issue_comment(
            session, issue_uid, comment['id'])
        if not commentobj:
            pagure.lib.add_issue_comment(
                session,
                issue=issue,
                comment=comment['comment'],
                user=usercomment.username,
                ticketfolder=None,
                notify=False,
                date_created=datetime.datetime.utcfromtimestamp(
                    float(comment['date_created'])),
            )

    if messages:
        pagure.lib.add_metadata_update_notif(
            session=session,
            issue=issue,
            messages=messages,
            user=user.username,
            ticketfolder=None
        )
    session.commit()


def update_request_from_git(
        session, reponame, namespace, username, request_uid, json_data,
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

    repo = pagure.lib._get_project(
        session, reponame, user=username, namespace=namespace)
    if not repo:
        raise pagure.exceptions.PagureException(
            'Unknown repo %s of username: %s in namespace: %s' % (
                reponame, username, namespace))

    user = get_user_from_json(session, json_data)

    request = pagure.lib.get_request_by_uid(
        session, request_uid=request_uid)

    if not request:
        repo_from = get_project_from_json(
            session, json_data.get('repo_from'),
            gitfolder, docfolder, ticketfolder, requestfolder
        )

        repo_to = get_project_from_json(
            session, json_data.get('project'),
            gitfolder, docfolder, ticketfolder, requestfolder
        )

        status = json_data.get('status')
        if str(status).lower() == 'true':
            status = 'Open'
        elif str(status).lower() == 'false':
            status = 'Merged'

        # Create new request
        pagure.lib.new_pull_request(
            session,
            repo_from=repo_from,
            branch_from=json_data.get('branch_from'),
            repo_to=repo_to if repo_to else None,
            remote_git=json_data.get('remote_git'),
            branch_to=json_data.get('branch'),
            title=json_data.get('title'),
            user=user.username,
            requestuid=json_data.get('uid'),
            requestid=json_data.get('id'),
            status=status,
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
                tree_id=comment.get('tree_id') or None,
                filename=comment['filename'],
                row=comment['line'],
                comment=comment['comment'],
                user=user.username,
                requestfolder=None,
                notify=False,
            )
    session.commit()


def _add_file_to_git(repo, issue, attachmentfolder, ticketfolder, user,
                     filename):
    ''' Add a given file to the specified ticket git repository.

    :arg repo: the Project object from the database
    :arg attachmentfolder: the folder on the filesystem where the attachments
        are stored
    :arg ticketfolder: the folder on the filesystem where the git repo for
        tickets are stored
    :arg user: the user object with its username and email
    :arg filename: the name of the file to save

    '''
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
    if os.path.exists(file_path):
        # File exists, remove the clone and return
        shutil.rmtree(newpath)
        return os.path.join('files', filename)

    if not os.path.exists(folder_path):
        os.mkdir(folder_path)

    # Copy from attachments directory
    src = os.path.join(attachmentfolder, repo.fullname, filename)
    shutil.copyfile(src, file_path)

    # Retrieve the list of files that changed
    diff = new_repo.diff()
    files = [patch.new_file_path for patch in diff]

    # Add the changes to the index
    index.add(os.path.join('files', filename))
    for filename in files:
        index.add(filename)

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
        name=user.username.encode('utf-8'),
        email=user.default_email.encode('utf-8')
    )

    # Actually commit
    new_repo.create_commit(
        'refs/heads/master',
        author,
        author,
        'Add file %s to ticket %s: %s' % (
            filename, issue.uid, issue.title),
        new_repo.index.write_tree(),
        parents)
    index.write()

    # Push to origin
    ori_remote = new_repo.remotes[0]
    master_ref = new_repo.lookup_reference('HEAD').resolve()
    refname = '%s:%s' % (master_ref.name, master_ref.name)

    PagureRepo.push(ori_remote, refname)

    # Remove the clone
    shutil.rmtree(newpath)

    return os.path.join('files', filename)


def _update_file_in_git(
        repo, branch, branchto, filename, content, message, user, email):
    ''' Update a specific file in the specified repository with the content
    given and commit the change under the user's name.

    :arg repo: the Project object from the database
    :arg filename: the name of the file to save
    :arg content: the new content of the file
    :arg message: the message of the git commit
    :arg user: the user object with its username and email

    '''
    _log.info('Updating file: %s in the repo: %s', filename, repo.path)

    # Get the fork
    repopath = pagure.get_repo_path(repo)

    # Clone the repo into a temp folder
    newpath = tempfile.mkdtemp(prefix='pagure-')
    new_repo = pygit2.clone_repository(
        repopath, newpath, checkout_branch=branch)

    file_path = os.path.join(newpath, filename)

    # Get the current index
    index = new_repo.index

    # Write down what changed
    with open(file_path, 'w') as stream:
        stream.write(content.replace('\r', '').encode('utf-8'))

    # Retrieve the list of files that changed
    diff = new_repo.diff()
    files = []
    for patch in diff:
        if hasattr(patch, 'new_file_path'):
            files.append(patch.new_file_path)
        elif hasattr(patch, 'delta'):
            files.append(patch.delta.new_file.path)

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

    # See if we need to create the branch
    nbranch_ref = None
    if branchto not in new_repo.listall_branches():
        nbranch_ref = new_repo.create_branch(branchto, parent)

    parents = []
    if parent:
        parents.append(parent.hex)

    # Author/commiter will always be this one
    author = pygit2.Signature(
        name=user.username.encode('utf-8'),
        email=email.encode('utf-8')
    )

    # Actually commit
    new_repo.create_commit(
        nbranch_ref.name if nbranch_ref else branch_ref.name,
        author,
        author,
        message.strip(),
        new_repo.index.write_tree(),
        parents)
    index.write()

    # Push to origin
    ori_remote = new_repo.remotes[0]
    refname = '%s:refs/heads/%s' % (
        nbranch_ref.name if nbranch_ref else branch_ref.name,
        branchto)

    try:
        PagureRepo.push(ori_remote, refname)
    except pygit2.GitError as err:  # pragma: no cover
        shutil.rmtree(newpath)
        raise pagure.exceptions.PagureException(
            'Commit could not be done: %s' % err)

    # Remove the clone
    shutil.rmtree(newpath)

    return os.path.join('files', filename)


def read_output(cmd, abspath, input=None, keepends=False, **kw):
    """ Read the output from the given command to run """
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
        **kw)
    (out, err) = procs.communicate(input)
    retcode = procs.wait()
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


def get_revs_between(oldrev, newrev, abspath, refname, forced=False):
    """ Yield revisions between HEAD and BASE. """

    cmd = ['rev-list', '%s...%s' % (oldrev, newrev)]
    if forced:
        head = get_default_branch(abspath)
        cmd.append('^%s' % head)
    if set(newrev) == set('0'):
        cmd = ['rev-list', '%s' % oldrev]
    elif set(oldrev) == set('0') or set(oldrev) == set('^0'):
        head = get_default_branch(abspath)
        cmd = ['rev-list', '%s' % newrev, '^%s' % head]
        if head in refname:
            cmd = ['rev-list', '%s' % newrev]
    return pagure.lib.git.read_git_lines(cmd, abspath)


def is_forced_push(oldrev, newrev, abspath):
    """ Returns whether there was a force push between HEAD and BASE.
    Doc: http://stackoverflow.com/a/12258773
    """

    # Returns if there was any commits deleted in the changeset
    cmd = ['rev-list', '%s' % oldrev, '^%s' % newrev]
    out = pagure.lib.git.read_git_lines(cmd, abspath)
    return len(out) > 0


def get_base_revision(torev, fromrev, abspath):
    """ Return the base revision between HEAD and BASE.
    This is useful in case of force-push.
    """
    cmd = ['merge-base', fromrev, torev]
    return pagure.lib.git.read_git_lines(cmd, abspath)


def get_default_branch(abspath):
    """ Return the default branch of a repo. """
    cmd = ['rev-parse', '--abbrev-ref', 'HEAD']
    out = pagure.lib.git.read_git_lines(cmd, abspath)
    if out:
        return out[0]
    else:
        return 'master'


def get_author(commit, abspath):
    ''' Return the name of the person that authored the commit. '''
    user = pagure.lib.git.read_git_lines(
        ['log', '-1', '--pretty=format:"%an"', commit],
        abspath)[0].replace('"', '')
    return user


def get_author_email(commit, abspath):
    ''' Return the email of the person that authored the commit. '''
    user = pagure.lib.git.read_git_lines(
        ['log', '-1', '--pretty=format:"%ae"', commit],
        abspath)[0].replace('"', '')
    return user


def get_commit_subject(commit, abspath):
    ''' Return the subject of the commit. '''
    subject = pagure.lib.git.read_git_lines(
        ['log', '-1', '--pretty=format:"%s"', commit],
        abspath)[0].replace('"', '')
    return subject


def get_repo_name(abspath):
    ''' Return the name of the git repo based on its path.
    '''
    repo_name = '.'.join(
        abspath.rsplit(os.path.sep, 1)[-1].rsplit('.', 1)[:-1])
    return repo_name


def get_repo_namespace(abspath, gitfolder=None):
    ''' Return the name of the git repo based on its path.
    '''
    namespace = None
    if not gitfolder:
        gitfolder = pagure.APP.config['GIT_FOLDER']

    short_path = os.path.realpath(abspath).replace(
        os.path.realpath(gitfolder), '').strip('/')

    if short_path.startswith('forks/'):
        username, projectname = short_path.split('forks/', 1)[1].split('/', 1)
    else:
        projectname = short_path

    if '/' in projectname:
        namespace = projectname.rsplit('/', 1)[0]

    return namespace


def get_username(abspath):
    ''' Return the username of the git repo based on its path.
    '''
    username = None
    repo = os.path.abspath(os.path.join(abspath, '..'))
    if '/forks/' in repo:
        username = repo.split('/forks/', 1)[1].split('/', 1)[0]
    return username


def get_branch_ref(repo, branchname):
    ''' Return the reference to the specified branch or raises an exception.
    '''
    location = pygit2.GIT_BRANCH_LOCAL
    if branchname not in repo.listall_branches():
        branchname = 'origin/%s' % branchname
        location = pygit2.GIT_BRANCH_REMOTE
    branch_ref = repo.lookup_branch(branchname, location)

    if not branch_ref or not branch_ref.resolve():
        raise pagure.exceptions.PagureException(
            'No refs found for %s' % branchname)
    return branch_ref.resolve()


def merge_pull_request(
        session, request, username, request_folder, domerge=True):
    ''' Merge the specified pull-request.
    '''
    if domerge:
        _log.info(
            '%s asked to merge the pull-request: %s', username, request)
    else:
        _log.info(
            '%s asked to diff the pull-request: %s', username, request)

    if request.remote:
        # Get the fork
        repopath = pagure.get_remote_repo_path(
            request.remote_git, request.branch_from)
    else:
        # Get the fork
        repopath = pagure.get_repo_path(request.project_from)

    fork_obj = PagureRepo(repopath)

    # Get the original repo
    parentpath = pagure.get_repo_path(request.project)

    # Clone the original repo into a temp folder
    newpath = tempfile.mkdtemp(prefix='pagure-pr-merge')
    _log.info('  working directory: %s', newpath)
    new_repo = pygit2.clone_repository(parentpath, newpath)

    # Update the start and stop commits in the DB, one last time
    diff_commits = diff_pull_request(
        session, request, fork_obj, PagureRepo(parentpath),
        requestfolder=request_folder, with_diff=False)
    _log.info('  %s commit to merge', len(diff_commits))

    if request.project.settings.get(
            'Enforce_signed-off_commits_in_pull-request', False):
        for commit in diff_commits:
            if 'signed-off-by' not in commit.message.lower():
                shutil.rmtree(newpath)
                _log.info('  Missing a required: signed-off-by: Bailing')
                raise pagure.exceptions.PagureException(
                    'This repo enforces that all commits are '
                    'signed off by their author. ')

    # Checkout the correct branch
    branch_ref = get_branch_ref(new_repo, request.branch)
    if not branch_ref:
        shutil.rmtree(newpath)
        _log.info('  Target branch could not be found')
        raise pagure.exceptions.BranchNotFoundException(
            'Branch %s could not be found in the repo %s' % (
                request.branch, request.project.fullname
            ))

    new_repo.checkout(branch_ref)

    branch = get_branch_ref(fork_obj, request.branch_from)
    if not branch:
        shutil.rmtree(newpath)
        _log.info('  Branch of origin could not be found')
        raise pagure.exceptions.BranchNotFoundException(
            'Branch %s could not be found in the repo %s' % (
                request.branch_from, request.project_from.fullname
                if request.project_from else request.remote_git
            ))

    repo_commit = fork_obj[branch.get_object().hex]

    ori_remote = new_repo.remotes[0]
    # Add the fork as remote repo
    reponame = '%s_%s' % (request.user.user, request.uid)

    _log.info('  Adding remote: %s pointing to: %s', reponame, repopath)
    remote = new_repo.create_remote(reponame, repopath)

    # Fetch the commits
    remote.fetch()

    merge = new_repo.merge(repo_commit.oid)
    _log.debug('  Merge: %s', merge)
    if merge is None:
        mergecode = new_repo.merge_analysis(repo_commit.oid)[0]
        _log.debug('  Mergecode: %s', mergecode)

    refname = '%s:refs/heads/%s' % (branch_ref.name, request.branch)
    if (
            (merge is not None and merge.is_uptodate)
            or  # noqa
            (merge is None and
             mergecode & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE)):

        if domerge:
            _log.info('  PR up to date, closing it')
            pagure.lib.close_pull_request(
                session, request, username,
                requestfolder=request_folder)
            shutil.rmtree(newpath)
            try:
                session.commit()
            except SQLAlchemyError as err:  # pragma: no cover
                session.rollback()
                _log.exception('  Could not merge the PR in the DB')
                pagure.APP.logger.exception(err)
                raise pagure.exceptions.PagureException(
                    'Could not close this pull-request')
            raise pagure.exceptions.PagureException(
                'Nothing to do, changes were already merged')
        else:
            _log.info('  PR up to date, reporting it')
            request.merge_status = 'NO_CHANGE'
            session.commit()
            shutil.rmtree(newpath)
            return 'NO_CHANGE'

    elif (
            (merge is not None and merge.is_fastforward)
            or  # noqa
            (merge is None and
             mergecode & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD)):

        if domerge:
            _log.info('  PR merged using fast-forward')
            head = new_repo.lookup_reference('HEAD').get_object()
            if not request.project.settings.get('always_merge', False):
                if merge is not None:
                    # This is depending on the pygit2 version
                    branch_ref.target = merge.fastforward_oid
                elif merge is None and mergecode is not None:
                    branch_ref.set_target(repo_commit.oid.hex)
                commit = repo_commit.oid.hex
            else:
                tree = new_repo.index.write_tree()
                user_obj = pagure.lib.get_user(session, username)
                author = pygit2.Signature(
                    user_obj.fullname.encode('utf-8'),
                    user_obj.default_email.encode('utf-8'))
                commit = new_repo.create_commit(
                    'refs/heads/%s' % request.branch,
                    author,
                    author,
                    'Merge #%s `%s`' % (request.id, request.title),
                    tree,
                    [head.hex, repo_commit.oid.hex])

            _log.info('  New head: %s', commit)
            PagureRepo.push(ori_remote, refname)
            fork_obj.run_hook(
                head.hex, commit, 'refs/heads/%s' % request.branch,
                username)
        else:
            _log.info('  PR merged using fast-forward, reporting it')
            request.merge_status = 'FFORWARD'
            session.commit()
            shutil.rmtree(newpath)
            return 'FFORWARD'

    else:
        tree = None
        try:
            tree = new_repo.index.write_tree()
        except pygit2.GitError as err:
            _log.exception(
                '  Could not write down the new tree: merge conflicts')
            shutil.rmtree(newpath)
            if domerge:
                _log.info('  Merge conflict: Bailing')
                raise pagure.exceptions.PagureException('Merge conflicts!')
            else:
                _log.info('  Merge conflict, reporting it')
                request.merge_status = 'CONFLICTS'
                session.commit()
                return 'CONFLICTS'

        if domerge:
            _log.info('  Writing down merge commit')
            head = new_repo.lookup_reference('HEAD').get_object()
            _log.info('  Basing on: %s - %s', head.hex, repo_commit.oid.hex)
            user_obj = pagure.lib.get_user(session, username)
            author = pygit2.Signature(
                user_obj.fullname.encode('utf-8'),
                user_obj.default_email.encode('utf-8'))
            commit = new_repo.create_commit(
                'refs/heads/%s' % request.branch,
                author,
                author,
                'Merge #%s `%s`' % (request.id, request.title),
                tree,
                [head.hex, repo_commit.oid.hex])

            _log.info('  New head: %s', commit)
            local_ref = 'refs/heads/_pagure_topush'
            new_repo.create_reference(local_ref, commit)
            refname = '%s:refs/heads/%s' % (local_ref, request.branch)
            PagureRepo.push(ori_remote, refname)
            _log.info('  Pushing to: %s to %s', refname, ori_remote)
            fork_obj.run_hook(
                head.hex, commit, 'refs/heads/%s' % request.branch,
                username)

        else:
            _log.info('  PR can be merged with a merge commit, reporting it')
            request.merge_status = 'MERGE'
            session.commit()
            shutil.rmtree(newpath)
            return 'MERGE'

    # Update status
    _log.info('  Closing the PR in the DB')
    pagure.lib.close_pull_request(
        session, request, username,
        requestfolder=request_folder,
    )
    shutil.rmtree(newpath)

    return 'Changes merged!'


def get_diff_info(repo_obj, orig_repo, branch_from, branch_to):
    ''' Return the info needed to see a diff or make a Pull-Request between
    the two specified repo.

    :arg repo_obj: The pygit2.Repository object of the first git repo
    :arg orig_repo:  The pygit2.Repository object of the second git repo
    :arg branch_from: the name of the branch having the changes, in the
        first git repo
    : arg branch_to: the name of the branch in which we want to merge the
        changes in the second git repo

    '''
    frombranch = repo_obj.lookup_branch(branch_from)
    if not frombranch and not repo_obj.is_empty:
        raise pagure.exceptions.BranchNotFoundException(
            'Branch %s does not exist' % branch_from
        )

    branch = None
    if branch_to:
        branch = orig_repo.lookup_branch(branch_to)
        if not branch and not orig_repo.is_empty:
            raise pagure.exceptions.BranchNotFoundException(
                'Branch %s could not be found in the target repo' % branch_to
            )

    commitid = None
    if frombranch:
        commitid = frombranch.get_object().hex

    diff_commits = []
    diff = None
    orig_commit = None
    if not repo_obj.is_empty and not orig_repo.is_empty:
        if branch:
            orig_commit = orig_repo[branch.get_object().hex]
            main_walker = orig_repo.walk(
                orig_commit.oid.hex, pygit2.GIT_SORT_TIME)

        repo_commit = repo_obj[commitid]
        branch_walker = repo_obj.walk(
            repo_commit.oid.hex, pygit2.GIT_SORT_TIME)

        main_commits = set()
        branch_commits = set()

        while 1:
            com = None
            if branch:
                try:
                    com = main_walker.next()
                    main_commits.add(com.oid.hex)
                except StopIteration:
                    com = None

            try:
                branch_commit = branch_walker.next()
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

        if diff_commits:
            first_commit = repo_obj[diff_commits[-1].oid.hex]
            if len(first_commit.parents) > 0:
                diff = repo_obj.diff(
                    repo_obj.revparse_single(first_commit.parents[0].oid.hex),
                    repo_obj.revparse_single(diff_commits[0].oid.hex)
                )
    elif orig_repo.is_empty and not repo_obj.is_empty:
        if 'master' in repo_obj.listall_branches():
            repo_commit = repo_obj[repo_obj.head.target]
        else:
            branch = repo_obj.lookup_branch(branch_from)
            repo_commit = branch.get_object()

        for commit in repo_obj.walk(
                repo_commit.oid.hex, pygit2.GIT_SORT_TIME):
            diff_commits.append(commit)

        diff = repo_commit.tree.diff_to_tree(swap=True)
    else:
        raise pagure.exceptions.PagureException(
            'Fork is empty, there are no commits to create a pull '
            'request with'
        )

    return(diff, diff_commits, orig_commit)


def diff_pull_request(
        session, request, repo_obj, orig_repo, requestfolder,
        with_diff=True):
    """ Returns the diff and the list of commits between the two git repos
    mentionned in the given pull-request.

    :arg session: The sqlalchemy session to connect to the database
    :arg request: The pagure.lib.model.PullRequest object of the pull-request
        to look into
    :arg repo_obj: The pygit2.Repository object of the first git repo
    :arg orig_repo:  The pygit2.Repository object of the second git repo
    :arg requestfolder: The folder in which are stored the git repositories
        containing the metadata of the different pull-requests
    :arg with_diff: A boolean on whether to return the diff with the list
        of commits (or just the list of commits)

    """

    diff = None
    diff_commits = []
    diff, diff_commits, _ = get_diff_info(
        repo_obj, orig_repo, request.branch_from, request.branch)

    if request.status and diff_commits:
        first_commit = repo_obj[diff_commits[-1].oid.hex]
        # Check if we can still rely on the merge_status
        commenttext = None
        if request.commit_start != first_commit.oid.hex or\
                request.commit_stop != diff_commits[0].oid.hex:
            request.merge_status = None
            if request.commit_start:
                new_commits_count = 0
                commenttext = ""
                for i in diff_commits:
                    if i.oid.hex == request.commit_stop:
                        break
                    new_commits_count = new_commits_count + 1
                    commenttext = '%s * %s\n' % (
                        commenttext, i.message.strip().split('\n')[0])
                if new_commits_count == 1:
                    commenttext = "**%d new commit added**\n\n%s" % (
                        new_commits_count, commenttext)
                else:
                    commenttext = "**%d new commits added**\n\n%s" % (
                        new_commits_count, commenttext)
            if request.commit_start and \
                    request.commit_start != first_commit.oid.hex:
                commenttext = 'rebased'
        request.commit_start = first_commit.oid.hex
        request.commit_stop = diff_commits[0].oid.hex
        session.add(request)
        session.commit()
        if commenttext:
            pagure.lib.add_pull_request_comment(
                session, request,
                commit=None, tree_id=None, filename=None, row=None,
                comment='%s' % commenttext,
                user=request.user.username,
                requestfolder=requestfolder,
                notify=False, notification=True
            )
            session.commit()
        pagure.lib.git.update_git(
            request, repo=request.project,
            repofolder=requestfolder)

    if with_diff:
        return (diff_commits, diff)
    else:
        return diff_commits


def get_git_tags(project):
    """ Returns the list of tags created in the git repositorie of the
    specified project.
    """
    repopath = pagure.get_repo_path(project)
    repo_obj = PagureRepo(repopath)

    tags = [
        tag.split('refs/tags/')[1]
        for tag in repo_obj.listall_references()
        if 'refs/tags/' in tag
    ]

    return tags


def get_git_tags_objects(project):
    """ Returns the list of references of the tags created in the git
    repositorie the specified project.
    The list is sorted using the time of the commit associated to the tag """
    repopath = pagure.get_repo_path(project)
    repo_obj = PagureRepo(repopath)
    tags = {}
    for tag in repo_obj.listall_references():
        if 'refs/tags/' in tag and repo_obj.lookup_reference(tag):
            commit_time = None
            try:
                theobject = repo_obj[repo_obj.lookup_reference(tag).target]
            except ValueError:
                theobject = None
            objecttype = ""
            if isinstance(theobject, pygit2.Tag):
                commit_time = theobject.get_object().commit_time
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
            if objecttype == 'tag':
                head_msg, _, body_msg = tags[commit_time][
                    "object"].message.partition('\n')
                if body_msg.strip().endswith('\n-----END PGP SIGNATURE-----'):
                    body_msg = body_msg.rsplit(
                        '-----BEGIN PGP SIGNATURE-----', 1)[0].strip()
                tags[commit_time]["head_msg"] = head_msg
                tags[commit_time]["body_msg"] = body_msg
    sorted_tags = []

    for tag in sorted(tags, reverse=True):
        sorted_tags.append(tags[tag])

    return sorted_tags


def log_commits_to_db(session, project, commits, gitdir):
    """ Log the given commits to the DB. """
    repo_obj = PagureRepo(gitdir)

    for commitid in commits:
        try:
            commit = repo_obj[commitid]
        except ValueError:
            continue

        try:
            author_obj = pagure.lib.get_user(session, commit.author.email)
        except pagure.exceptions.PagureException:
            author_obj = None

        date_created = arrow.get(commit.commit_time)

        log = model.PagureLog(
            user_id=author_obj.id if author_obj else None,
            user_email=commit.author.email if not author_obj else None,
            project_id=project.id,
            log_type='committed',
            ref_id=commit.oid.hex,
            date=date_created.date(),
            date_created=date_created.datetime
        )
        session.add(log)


def reinit_git(project, repofolder):
    ''' Delete and recreate a git folder
    :args project: SQLAlchemy object of the project
    :args folder: The folder which contains the git repos
    like TICKETS_FOLDER for tickets and REQUESTS_FOLDER for
    pull requests
    '''

    repo_path = os.path.join(repofolder, project.path)
    if not os.path.exists(repo_path):
        return

    # delete that repo
    shutil.rmtree(repo_path)

    # create it again
    pygit2.init_repository(
        repo_path, bare=True,
        mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP
    )


def get_git_branches(project):
    ''' Return a list of branches for the project
    :arg project: The Project instance to get the branches for
    '''
    repo_path = pagure.get_repo_path(project)
    repo_obj = pygit2.Repository(repo_path)
    return repo_obj.listall_branches()
