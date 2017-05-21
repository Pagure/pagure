# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

import os
import os.path
import shutil

from celery import Celery
from celery.result import AsyncResult

import pygit2
import tempfile
import six

import pagure
from pagure import APP
import pagure.lib
import pagure.lib.git


conn = Celery('tasks',
              broker='redis://%s' % APP.config['REDIS_HOST'],
              backend='redis://%s' % APP.config['REDIS_HOST'])


def get_result(uuid):
    return AsyncResult(uuid, conn.backend)


def ret(endpoint, **kwargs):
    toret = {'endpoint': endpoint}
    toret.update(kwargs)
    return toret


@conn.task
def generate_gitolite_acls():
    pagure.lib.git._generate_gitolite_acls()


@conn.task
def create_project(username, namespace, name, add_readme, ignore_existing_repo):
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
    # TODO: This needs enabling, but doesn't work in my env
    #plugin = pagure.lib.plugins.get_plugin('default')
    #dbobj = plugin.db_object()
    #dbobj.active = True
    #dbobj.project_id = project.id
    #session.add(dbobj)
    #session.flush()
    #plugin.set_up(project)
    #plugin.install(project, dbobj)
    #session.commit()

    session.remove()
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
