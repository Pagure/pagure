# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

import gc
import os
import os.path
import shutil

from celery import Celery
from celery.result import AsyncResult

import pygit2
import tempfile
import six

import logging

import pagure
from pagure import APP
import pagure.lib
import pagure.lib.git

_log = logging.getLogger(__name__)


if os.environ.get('PAGURE_BROKER_URL'):
    broker_url = os.environ['PAGURE_BROKER_URL']
else:
    broker_url = 'redis://%s' % APP.config['REDIS_HOST']

conn = Celery('tasks', broker=broker_url, backend=broker_url)
conn.conf.update(APP.config['CELERY_CONFIG'])


def get_result(uuid):
    return AsyncResult(uuid, conn.backend)


def ret(endpoint, **kwargs):
    toret = {'endpoint': endpoint}
    toret.update(kwargs)
    return toret


def gc_clean():
    # https://pagure.io/pagure/issue/2302
    gc.collect()


@conn.task
def generate_gitolite_acls():
    pagure.lib.git._generate_gitolite_acls()
    gc_clean()


@conn.task
def create_project(username, namespace, name, add_readme,
                   ignore_existing_repo):
    session = pagure.lib.create_session()

    project = pagure.lib._get_project(session, namespace=namespace,
                                      name=name, with_lock=True)
    userobj = pagure.lib.search_user(session, username=username)
    gitrepo = os.path.join(APP.config['GIT_FOLDER'], project.path)

    # Add the readme file if it was asked
    if not add_readme:
        pygit2.init_repository(gitrepo, bare=True)
    else:
        temp_gitrepo_path = tempfile.mkdtemp(prefix='pagure-')
        temp_gitrepo = pygit2.init_repository(temp_gitrepo_path, bare=False)
        author = userobj.fullname or userobj.user
        author_email = userobj.default_email
        if six.PY2:
            author = author.encode('utf-8')
            author_email = author_email.encode('utf-8')
        author = pygit2.Signature(author, author_email)
        content = u"# %s\n\n%s" % (name, project.description)
        readme_file = os.path.join(temp_gitrepo.workdir, "README.md")
        with open(readme_file, 'wb') as stream:
            stream.write(content.encode('utf-8'))
        temp_gitrepo.index.add_all()
        temp_gitrepo.index.write()
        tree = temp_gitrepo.index.write_tree()
        temp_gitrepo.create_commit(
            'HEAD', author, author, 'Added the README', tree, [])
        pygit2.clone_repository(temp_gitrepo_path, gitrepo, bare=True)
        shutil.rmtree(temp_gitrepo_path)

    # Make the repo exportable via apache
    http_clone_file = os.path.join(gitrepo, 'git-daemon-export-ok')
    if not os.path.exists(http_clone_file):
        with open(http_clone_file, 'w') as stream:
            pass

    docrepo = os.path.join(APP.config['DOCS_FOLDER'], project.path)
    if os.path.exists(docrepo):
        if not ignore_existing_repo:
            shutil.rmtree(gitrepo)
            raise pagure.exceptions.RepoExistsException(
                'The docs repo "%s" already exists' % project.path
            )
    else:
        pygit2.init_repository(docrepo, bare=True)

    ticketrepo = os.path.join(APP.config['TICKETS_FOLDER'], project.path)
    if os.path.exists(ticketrepo):
        if not ignore_existing_repo:
            shutil.rmtree(gitrepo)
            shutil.rmtree(docrepo)
            raise pagure.exceptions.RepoExistsException(
                'The tickets repo "%s" already exists' % project.path
            )
    else:
        pygit2.init_repository(
            ticketrepo, bare=True,
            mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP)

    requestrepo = os.path.join(APP.config['REQUESTS_FOLDER'], project.path)
    if os.path.exists(requestrepo):
        if not ignore_existing_repo:
            shutil.rmtree(gitrepo)
            shutil.rmtree(docrepo)
            shutil.rmtree(ticketrepo)
            raise pagure.exceptions.RepoExistsException(
                'The requests repo "%s" already exists' % project.path
            )
    else:
        pygit2.init_repository(
            requestrepo, bare=True,
            mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP)

    # Install the default hook
    plugin = pagure.lib.plugins.get_plugin('default')
    dbobj = plugin.db_object()
    dbobj.active = True
    dbobj.project_id = project.id
    session.add(dbobj)
    session.flush()
    plugin.set_up(project)
    plugin.install(project, dbobj)
    session.commit()

    session.remove()
    gc_clean()

    generate_gitolite_acls.delay()
    return ret('view_repo', repo=name, namespace=namespace)


@conn.task
def update_git(name, namespace, user, ticketuid=None, requestuid=None):
    session = pagure.lib.create_session()

    project = pagure.lib._get_project(session, namespace=namespace, name=name,
                                      user=user, with_lock=True)
    if ticketuid is not None:
        obj = pagure.lib.get_issue_by_uid(session, ticketuid)
        folder = APP.config['TICKETS_FOLDER']
    elif requestuid is not None:
        obj = pagure.lib.get_request_by_uid(session, requestuid)
        folder = APP.config['REQUESTS_FOLDER']
    else:
        raise NotImplementedError('No ticket ID or request ID provided')

    if obj is None:
        raise Exception('Unable to find object')

    result = pagure.lib.git._update_git(obj, project, folder)
    session.remove()
    gc_clean()
    return result


@conn.task
def clean_git(name, namespace, user, ticketuid):
    session = pagure.lib.create_session()

    project = pagure.lib._get_project(session, namespace=namespace, name=name,
                                      user=user, with_lock=True)
    obj = pagure.lib.get_issue_by_uid(session, ticketuid)
    folder = APP.config['TICKETS_FOLDER']

    if obj is None:
        raise Exception('Unable to find object')

    result = pagure.lib.git._clean_git(obj, project, folder)
    session.remove()
    return result


@conn.task
def update_file_in_git(name, namespace, user, branch, branchto, filename,
                       content, message, username, email):
    session = pagure.lib.create_session()

    userobj = pagure.lib.search_user(session, username=username)
    project = pagure.lib._get_project(session, namespace=namespace, name=name,
                                      user=user, with_lock=True)

    pagure.lib.git._update_file_in_git(project, branch, branchto, filename,
                                       content, message, userobj, email)

    session.remove()
    return ret('view_commits', repo=project.name, username=user,
               namespace=namespace, branchname=branchto)


@conn.task
def delete_branch(name, namespace, user, branchname):
    session = pagure.lib.create_session()

    project = pagure.lib._get_project(session, namespace=namespace, name=name,
                                      user=user, with_lock=True)
    repo_obj = pygit2.Repository(pagure.get_repo_path(project))

    try:
        branch = repo_obj.lookup_branch(branchname)
        branch.delete()
    except pygit2.GitError as err:
        _log.exception(err)

    session.remove()
    return ret('view_repo', repo=name, namespace=namespace, username=user)


@conn.task
def fork(name, namespace, user_owner, user_forker, editbranch, editfile):
    session = pagure.lib.create_session()

    repo_from = pagure.lib._get_project(session, namespace=namespace,
                                        name=name, user=user_owner)
    repo_to = pagure.lib._get_project(session, namespace=namespace, name=name,
                                      user=user_forker, with_lock=True)

    reponame = os.path.join(APP.config['GIT_FOLDER'], repo_from.path)
    forkreponame = os.path.join(APP.config['GIT_FOLDER'], repo_to.path)

    frepo = pygit2.clone_repository(reponame, forkreponame, bare=True)
    # Clone all the branches as well
    for branch in frepo.listall_branches(pygit2.GIT_BRANCH_REMOTE):
        branch_obj = frepo.lookup_branch(branch, pygit2.GIT_BRANCH_REMOTE)
        branchname = branch_obj.branch_name.replace(
            branch_obj.remote_name, '', 1)[1:]
        if branchname in frepo.listall_branches(pygit2.GIT_BRANCH_LOCAL):
            continue
        frepo.create_branch(branchname, frepo.get(branch_obj.target.hex))

    # Create the git-daemon-export-ok file on the clone
    http_clone_file = os.path.join(forkreponame, 'git-daemon-export-ok')
    if not os.path.exists(http_clone_file):
        with open(http_clone_file, 'w'):
            pass

    docrepo = os.path.join(APP.config['DOCS_FOLDER'], repo_to.path)
    if os.path.exists(docrepo):
        shutil.rmtree(forkreponame)
        raise pagure.exceptions.RepoExistsException(
            'The docs "%s" already exists' % repo_to.path
        )
    pygit2.init_repository(docrepo, bare=True)

    ticketrepo = os.path.join(APP.config['TICKETS_FOLDER'], repo_to.path)
    if os.path.exists(ticketrepo):
        shutil.rmtree(forkreponame)
        shutil.rmtree(docrepo)
        raise pagure.exceptions.RepoExistsException(
            'The tickets repo "%s" already exists' % repo_to.path
        )
    pygit2.init_repository(
        ticketrepo, bare=True,
        mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP)

    requestrepo = os.path.join(APP.config['REQUESTS_FOLDER'], repo_to.path)
    if os.path.exists(requestrepo):
        shutil.rmtree(forkreponame)
        shutil.rmtree(docrepo)
        shutil.rmtree(ticketrepo)
        raise pagure.exceptions.RepoExistsException(
            'The requests repo "%s" already exists' % repo_to.path
        )
    pygit2.init_repository(
        requestrepo, bare=True,
        mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP)

    pagure.lib.notify.log(
        repo_to,
        topic='project.forked',
        msg=dict(
            project=repo_to.to_json(public=True),
            agent=user_forker,
        ),
    )

    session.remove()
    del frepo
    gc_clean()
    generate_gitolite_acls.delay()

    if editfile is None:
        return ret('view_repo', repo=name, namespace=namespace,
                   username=user_forker)
    else:
        return ret('edit_file', repo=name, namespace=namespace,
                   username=user_forker, branchname=editbranch,
                   filename=editfile)


@conn.task
def pull_remote_repo(remote_git, branch_from):
    clonepath = pagure.get_remote_repo_path(remote_git, branch_from,
                                            ignore_non_exist=True)
    repo = pygit2.clone_repository(
        remote_git, clonepath, checkout_branch=branch_from)

    del repo
    gc_clean()
    return clonepath


@conn.task
def refresh_pr_cache(name, namespace, user):
    session = pagure.lib.create_session()

    project = pagure.lib._get_project(session, namespace=namespace,
                                      name=name, user=user)

    pagure.lib.reset_status_pull_request(session, project)

    session.remove()
    gc_clean()


@conn.task
def merge_pull_request(name, namespace, user, requestid, user_merger):
    session = pagure.lib.create_session()

    project = pagure.lib._get_project(session, namespace=namespace,
                                      name=name, user=user, with_lock=True)
    request = pagure.lib.search_pull_requests(
        session, project_id=project.id, requestid=requestid)

    pagure.lib.git.merge_pull_request(
        session, request, user_merger, APP.config['REQUESTS_FOLDER'])

    refresh_pr_cache.delay(name, namespace, user)
    session.remove()
    gc_clean()
    return ret('view_repo', repo=name, username=user, namespace=namespace)


@conn.task
def add_file_to_git(name, namespace, user, user_attacher, issueuid, filename):
    session = pagure.lib.create_session()

    project = pagure.lib._get_project(session, namespace=namespace,
                                      name=name, user=user)
    issue = pagure.lib.get_issue_by_uid(session, issueuid)
    user_attacher = pagure.lib.search_user(session, username=user_attacher)

    pagure.lib.git._add_file_to_git(
        project, issue, APP.config['ATTACHMENTS_FOLDER'],
        APP.config['TICKETS_FOLDER'], user_attacher, filename)

    session.remove()
    gc_clean()
