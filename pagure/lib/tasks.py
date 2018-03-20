# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

import collections
import datetime
import gc
import hashlib
import logging
import os
import os.path
import shutil
import tempfile
import time

from functools import wraps

import arrow
import pygit2
import six

from celery import Celery
from celery.result import AsyncResult
from sqlalchemy.exc import SQLAlchemyError

import pagure.lib
import pagure.lib.git
import pagure.lib.git_auth
import pagure.lib.repo
import pagure.utils
from pagure.config import config as pagure_config

# logging.config.dictConfig(pagure_config.get('LOGGING') or {'version': 1})
_log = logging.getLogger(__name__)


if os.environ.get('PAGURE_BROKER_URL'):
    broker_url = os.environ['PAGURE_BROKER_URL']
elif pagure_config.get('BROKER_URL'):
    broker_url = pagure_config['BROKER_URL']
else:
    broker_url = 'redis://%s' % pagure_config['REDIS_HOST']

conn = Celery('tasks', broker=broker_url, backend=broker_url)
conn.conf.update(pagure_config['CELERY_CONFIG'])


def pagure_task(function):
    """ Simple decorator that is responsible for:
    * Adjusting the status of the task when it starts
    * Creating and cleaning up a SQLAlchemy session
    """

    @wraps(function)
    def decorated_function(self, *args, **kwargs):
        """ Decorated function, actually does the work. """
        if self is not None:
            try:
                self.update_state(state='RUNNING')
            except TypeError:
                pass
        session = pagure.lib.create_session(pagure_config['DB_URL'])
        try:
            return function(self, session, *args, **kwargs)
        finally:
            session.remove()
            gc_clean()
    return decorated_function


def get_result(uuid):
    """ Returns the AsyncResult object for a given task.

    :arg uuid: the unique identifier of the task to retrieve.
    :type uuid: str
    :return: celery.result.AsyncResult

    """
    return AsyncResult(uuid, conn.backend)


def ret(endpoint, **kwargs):
    toret = {'endpoint': endpoint}
    toret.update(kwargs)
    return toret


def gc_clean():
    """ Force a run of the garbage collector. """
    # https://pagure.io/pagure/issue/2302
    gc.collect()


@conn.task(queue=pagure_config.get('GITOLITE_CELERY_QUEUE', None), bind=True)
@pagure_task
def generate_gitolite_acls(
        self, session, namespace=None, name=None, user=None, group=None):
    """ Generate the gitolite configuration file either entirely or for a
    specific project.

    :arg session: SQLAlchemy session object
    :type session: sqlalchemy.orm.session.Session
    :kwarg namespace: the namespace of the project
    :type namespace: None or str
    :kwarg name: the name of the project
    :type name: None or str
    :kwarg user: the user of the project, only set if the project is a fork
    :type user: None or str
    :kwarg group: the group to refresh the members of
    :type group: None or str

    """
    project = None
    if name and name != -1:
        project = pagure.lib._get_project(
            session, namespace=namespace, name=name, user=user,
            case=pagure_config.get('CASE_SENSITIVE', False))

    elif name == -1:
        project = name
    helper = pagure.lib.git_auth.get_git_auth_helper(
        pagure_config['GITOLITE_BACKEND'])
    _log.debug('Got helper: %s', helper)

    group_obj = None
    if group:
        group_obj = pagure.lib.search_groups(session, group_name=group)
    _log.debug(
        'Calling helper: %s with arg: project=%s, group=%s',
        helper, project, group_obj)
    helper.generate_acls(project=project, group=group_obj)

    pagure.lib.update_read_only_mode(session, project, read_only=False)
    try:
        session.commit()
        _log.debug('Project %s is no longer in Read Only Mode', project)
    except SQLAlchemyError:
        session.rollback()
        _log.exception(
            'Failed to unmark read_only for: %s project', project)


@conn.task(queue=pagure_config.get('GITOLITE_CELERY_QUEUE', None), bind=True)
@pagure_task
def delete_project(
        self, session, namespace=None, name=None, user=None, action_user=None):
    """ Delete a project in pagure.

    This is achieved in three steps:
    - Remove the project from gitolite.conf
    - Remove the git repositories on disk
    - Remove the project from the DB

    :arg session: SQLAlchemy session object
    :type session: sqlalchemy.orm.session.Session
    :kwarg namespace: the namespace of the project
    :type namespace: None or str
    :kwarg name: the name of the project
    :type name: None or str
    :kwarg user: the user of the project, only set if the project is a fork
    :type user: None or str
    :kwarg action_user: the user deleting the project
    :type action_user: None or str

    """
    project = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user,
        case=pagure_config.get('CASE_SENSITIVE', False))

    if not project:
        raise RuntimeError(
            'Project: %s/%s from user: %s not found in the DB' % (
                namespace, name, user))

    # Remove the project from gitolite.conf
    helper = pagure.lib.git_auth.get_git_auth_helper(
        pagure_config['GITOLITE_BACKEND'])
    _log.debug('Got helper: %s', helper)

    _log.debug(
        'Calling helper: %s with arg: project=%s', helper, project.fullname)
    helper.remove_acls(session=session, project=project)

    # Remove the git repositories on disk
    paths = []
    for key in [
            'GIT_FOLDER', 'DOCS_FOLDER',
            'TICKETS_FOLDER', 'REQUESTS_FOLDER']:
        if pagure_config[key]:
            path = os.path.join(pagure_config[key], project.path)
            if os.path.exists(path):
                paths.append(path)

    try:
        for path in paths:
            _log.info('Deleting: %s' % path)
            shutil.rmtree(path)
    except (OSError, IOError) as err:
        _log.exception(err)
        raise RuntimeError(
            'Could not delete all the repos from the system')

    for path in paths:
        _log.info('Path: %s - exists: %s' % (path, os.path.exists(path)))

    # Remove the project from the DB
    username = project.user.user
    try:
        project_json = project.to_json(public=True)
        session.delete(project)
        session.commit()
        pagure.lib.notify.log(
            project,
            topic='project.deleted',
            msg=dict(
                project=project_json,
                agent=action_user,
            ),
        )
    except SQLAlchemyError:
        session.rollback()
        _log.exception(
            'Failed to delete project: %s from the DB', project.fullname)

    return ret('ui_ns.view_user', username=username)


@conn.task(bind=True)
@pagure_task
def create_project(self, session, username, namespace, name, add_readme,
                   ignore_existing_repo):
    """ Create a project.

    :arg session: SQLAlchemy session object
    :type session: sqlalchemy.orm.session.Session
    :kwarg username: the user creating the project
    :type user: str
    :kwarg namespace: the namespace of the project
    :type namespace: str
    :kwarg name: the name of the project
    :type name: str
    :kwarg add_readme: a boolean specifying if the project should be
        created with a README file or not
    :type add_readme: bool
    :kwarg ignore_existing_repo: a boolean specifying whether the creation
        of the project should fail if the repo exists on disk or not
    :type ignore_existing_repo: bool

    """
    project = pagure.lib._get_project(
        session, namespace=namespace, name=name,
        case=pagure_config.get('CASE_SENSITIVE', False))

    with project.lock('WORKER'):
        userobj = pagure.lib.search_user(session, username=username)
        gitrepo = os.path.join(pagure_config['GIT_FOLDER'], project.path)

        # Add the readme file if it was asked
        if not add_readme:
            _log.debug('Create git repo at: %s', gitrepo)
            pygit2.init_repository(gitrepo, bare=True)
        else:
            temp_gitrepo_path = tempfile.mkdtemp(prefix='pagure-')
            temp_gitrepo = pygit2.init_repository(temp_gitrepo_path,
                                                  bare=False)
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

        if pagure_config.get('DOCS_FOLDER'):
            docrepo = os.path.join(
                pagure_config['DOCS_FOLDER'], project.path)
            if os.path.exists(docrepo):
                if not ignore_existing_repo:
                    shutil.rmtree(gitrepo)
                    session.remove()
                    raise pagure.exceptions.RepoExistsException(
                        'The docs repo "%s" already exists' % project.path
                    )
            else:
                _log.debug('Create git repo at: %s', docrepo)
                pygit2.init_repository(docrepo, bare=True)

        if pagure_config.get('TICKETS_FOLDER'):
            ticketrepo = os.path.join(
                pagure_config['TICKETS_FOLDER'], project.path)
            if os.path.exists(ticketrepo):
                if not ignore_existing_repo:
                    shutil.rmtree(gitrepo)
                    shutil.rmtree(docrepo)
                    session.remove()
                    raise pagure.exceptions.RepoExistsException(
                        'The tickets repo "%s" already exists' %
                        project.path
                    )
            else:
                _log.debug('Create git repo at: %s', ticketrepo)
                pygit2.init_repository(
                    ticketrepo, bare=True,
                    mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP)

        requestrepo = os.path.join(
            pagure_config['REQUESTS_FOLDER'], project.path)
        if os.path.exists(requestrepo):
            if not ignore_existing_repo:
                shutil.rmtree(gitrepo)
                shutil.rmtree(docrepo)
                shutil.rmtree(ticketrepo)
                session.remove()
                raise pagure.exceptions.RepoExistsException(
                    'The requests repo "%s" already exists' %
                    project.path
                )
        else:
            _log.debug('Create git repo at: %s', requestrepo)
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

    task = generate_gitolite_acls.delay(
        namespace=project.namespace,
        name=project.name,
        user=project.user.user if project.is_fork else None)
    _log.info('Refreshing gitolite config queued in task: %s', task.id)

    return ret('ui_ns.view_repo', repo=name, namespace=namespace)


@conn.task(bind=True)
@pagure_task
def update_git(self, session, name, namespace, user,
               ticketuid=None, requestuid=None):
    """ Update the JSON representation of either a ticket or a pull-request
    depending on the argument specified.
    """
    project = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user,
        case=pagure_config.get('CASE_SENSITIVE', False))

    with project.lock('WORKER'):
        if ticketuid is not None:
            obj = pagure.lib.get_issue_by_uid(session, ticketuid)
            folder = pagure_config['TICKETS_FOLDER']
        elif requestuid is not None:
            obj = pagure.lib.get_request_by_uid(session, requestuid)
            folder = pagure_config['REQUESTS_FOLDER']
        else:
            raise NotImplementedError('No ticket ID or request ID provided')

        if obj is None:
            raise Exception('Unable to find object')

        result = pagure.lib.git._update_git(obj, project, folder)

    return result


@conn.task(bind=True)
@pagure_task
def clean_git(self, session, name, namespace, user, ticketuid):
    """ Remove the JSON representation of a ticket on the git repository
    for tickets.
    """
    project = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user,
        case=pagure_config.get('CASE_SENSITIVE', False))

    with project.lock('WORKER'):
        obj = pagure.lib.get_issue_by_uid(session, ticketuid)
        folder = pagure_config['TICKETS_FOLDER']

        if obj is None:
            raise Exception('Unable to find object')

        result = pagure.lib.git._clean_git(obj, project, folder)

    return result


@conn.task(bind=True)
@pagure_task
def update_file_in_git(self, session, name, namespace, user, branch, branchto,
                       filename, content, message, username, email,
                       runhook=False):
    """ Update a file in the specified git repo.
    """
    userobj = pagure.lib.search_user(session, username=username)
    project = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user,
        case=pagure_config.get('CASE_SENSITIVE', False))

    with project.lock('WORKER'):
        pagure.lib.git._update_file_in_git(
            project, branch, branchto, filename,
            content, message, userobj, email, runhook=runhook)

    return ret('ui_ns.view_commits', repo=project.name, username=user,
               namespace=namespace, branchname=branchto)


@conn.task(bind=True)
@pagure_task
def delete_branch(self, session, name, namespace, user, branchname):
    """ Delete a branch from a git repo.
    """
    project = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user,
        case=pagure_config.get('CASE_SENSITIVE', False))

    with project.lock('WORKER'):
        repo_obj = pygit2.Repository(
            pagure.utils.get_repo_path(project))

        try:
            branch = repo_obj.lookup_branch(branchname)
            branch.delete()
        except pygit2.GitError as err:
            _log.exception(err)

    return ret(
        'ui_ns.view_repo', repo=name, namespace=namespace, username=user)


@conn.task(bind=True)
@pagure_task
def fork(self, session, name, namespace, user_owner, user_forker,
         editbranch, editfile):
    """ Forks the specified project for the specified user.

    :arg namespace: the namespace of the project
    :type namespace: str
    :arg name: the name of the project
    :type name: str
    :arg user_owner: the user of which the project is forked, only set
        if the project is already a fork
    :type user_owner: str
    :arg user_forker: the user forking the project
    :type user_forker: str
    :kwarg editbranch: the name of the branch in which the user asked to
        edit a file
    :type editbranch: str
    :kwarg editfile: the file the user asked to edit
    :type editfile: str

    """
    repo_from = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user_owner,
        case=pagure_config.get('CASE_SENSITIVE', False))

    repo_to = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user_forker,
        case=pagure_config.get('CASE_SENSITIVE', False))

    with repo_to.lock('WORKER'):
        reponame = os.path.join(pagure_config['GIT_FOLDER'], repo_from.path)
        forkreponame = os.path.join(pagure_config['GIT_FOLDER'], repo_to.path)

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

        # Only fork the doc folder if the pagure instance supports the doc
        # service/server.
        if pagure_config.get('DOCS_FOLDER'):
            docrepo = os.path.join(
                pagure_config['DOCS_FOLDER'], repo_to.path)
            if os.path.exists(docrepo):
                shutil.rmtree(forkreponame)
                raise pagure.exceptions.RepoExistsException(
                    'The docs "%s" already exists' % repo_to.path
                )
            pygit2.init_repository(docrepo, bare=True)

        if pagure_config.get('TICKETS_FOLDER'):
            ticketrepo = os.path.join(
                pagure_config['TICKETS_FOLDER'], repo_to.path)
            if os.path.exists(ticketrepo):
                shutil.rmtree(forkreponame)
                shutil.rmtree(docrepo)
                raise pagure.exceptions.RepoExistsException(
                    'The tickets repo "%s" already exists' % repo_to.path
                )
            pygit2.init_repository(
                ticketrepo, bare=True,
                mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP)

        requestrepo = os.path.join(
            pagure_config['REQUESTS_FOLDER'], repo_to.path)
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

    del frepo

    _log.info('Project created, refreshing auth async')
    task = generate_gitolite_acls.delay(
        namespace=repo_to.namespace,
        name=repo_to.name,
        user=repo_to.user.user if repo_to.is_fork else None)
    _log.info('Refreshing gitolite config queued in task: %s', task.id)

    if editfile is None:
        return ret('ui_ns.view_repo', repo=name, namespace=namespace,
                   username=user_forker)
    else:
        return ret('ui_ns.edit_file', repo=name, namespace=namespace,
                   username=user_forker, branchname=editbranch,
                   filename=editfile)


@conn.task(bind=True)
@pagure_task
def pull_remote_repo(self, session, remote_git, branch_from):
    """ Clone a remote git repository locally for remote PRs.
    """

    clonepath = pagure.utils.get_remote_repo_path(
        remote_git, branch_from, ignore_non_exist=True)

    repo = pygit2.clone_repository(
        remote_git, clonepath, checkout_branch=branch_from)

    del repo
    return clonepath


@conn.task(bind=True)
@pagure_task
def refresh_remote_pr(self, session, name, namespace, user, requestid):
    """ Refresh the local clone of a git repository used in a remote
    pull-request.
    """
    project = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user,
        case=pagure_config.get('CASE_SENSITIVE', False))

    request = pagure.lib.search_pull_requests(
        session, project_id=project.id, requestid=requestid)
    _log.debug(
        'refreshing remote pull-request: %s/#%s', request.project.fullname,
        request.id)

    clonepath = pagure.utils.utils.get_remote_repo_path(
        request.remote_git, request.branch_from)

    repo = pagure.lib.repo.PagureRepo(clonepath)
    repo.pull(branch=request.branch_from, force=True)

    refresh_pr_cache.delay(name, namespace, user)
    del repo
    return ret(
        'ui_ns.request_pull', username=user, namespace=namespace,
        repo=name, requestid=requestid)


@conn.task(bind=True)
@pagure_task
def refresh_pr_cache(self, session, name, namespace, user):
    """ Refresh the merge status cached of pull-requests.
    """
    project = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user,
        case=pagure_config.get('CASE_SENSITIVE', False))

    pagure.lib.reset_status_pull_request(session, project)


@conn.task(bind=True)
@pagure_task
def merge_pull_request(self, session, name, namespace, user, requestid,
                       user_merger):
    """ Merge pull-request.
    """
    project = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user,
        case=pagure_config.get('CASE_SENSITIVE', False))

    with project.lock('WORKER'):
        request = pagure.lib.search_pull_requests(
            session, project_id=project.id, requestid=requestid)
        _log.debug(
            'Merging pull-request: %s/#%s', request.project.fullname,
            request.id)
        pagure.lib.git.merge_pull_request(
            session, request, user_merger, pagure_config['REQUESTS_FOLDER'])

    refresh_pr_cache.delay(name, namespace, user)
    return ret(
        'ui_ns.view_repo', repo=name, username=user, namespace=namespace)


@conn.task(bind=True)
@pagure_task
def add_file_to_git(self, session, name, namespace, user, user_attacher,
                    issueuid, filename):
    """ Add a file to the specified git repo.
    """
    project = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user,
        case=pagure_config.get('CASE_SENSITIVE', False))

    with project.lock('WORKER'):
        issue = pagure.lib.get_issue_by_uid(session, issueuid)
        user_attacher = pagure.lib.search_user(session, username=user_attacher)

        from_folder = pagure_config['ATTACHMENTS_FOLDER']
        to_folder = pagure_config['TICKETS_FOLDER']
        _log.info(
            'Adding file %s from %s to %s', filename, from_folder, to_folder)
        pagure.lib.git._add_file_to_git(
            project, issue,
            from_folder,
            to_folder,
            user_attacher,
            filename)


@conn.task(bind=True)
@pagure_task
def project_dowait(self, session, name, namespace, user):
    """ This is a task used to test the locking systems.

    It should never be allowed to be called in production instances, since that
    would allow an attacker to basically DOS a project by calling this
    repeatedly. """
    assert pagure_config.get('ALLOW_PROJECT_DOWAIT', False)

    project = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user,
        case=pagure_config.get('CASE_SENSITIVE', False))

    with project.lock('WORKER'):
        time.sleep(10)

    return ret(
        'ui_ns.view_repo', repo=name, username=user, namespace=namespace)


@conn.task(bind=True)
@pagure_task
def sync_pull_ref(self, session, name, namespace, user, requestid):
    """ Synchronize a pull/ reference from the content in the forked repo,
    allowing local checkout of the pull-request.
    """
    project = pagure.lib._get_project(
        session, namespace=namespace, name=name, user=user,
        case=pagure_config.get('CASE_SENSITIVE', False))

    with project.lock('WORKER'):
        request = pagure.lib.search_pull_requests(
            session, project_id=project.id, requestid=requestid)
        _log.debug(
            'Update pull refs of: %s#%s',
            request.project.fullname, request.id)

        if request.remote:
            # Get the fork
            repopath = pagure.utils.get_remote_repo_path(
                request.remote_git, request.branch_from)
        else:
            # Get the fork
            repopath = pagure.utils.get_repo_path(request.project_from)
        _log.debug('   working on the repo in: %s', repopath)

        repo_obj = pygit2.Repository(repopath)
        pagure.lib.git.update_pull_ref(request, repo_obj)


@conn.task(bind=True)
@pagure_task
def update_checksums_file(self, session, folder, filenames):
    """ Update the checksums file in the release folder of the project.
    """

    sha_file = os.path.join(folder, 'CHECKSUMS')
    new_file = not os.path.exists(sha_file)

    if not new_file:
        with open(sha_file) as stream:
            row = stream.readline().strip()
            if row != '# Generated and updated by pagure':
                # This wasn't generated by pagure, don't touch it!
                return

    algos = {
        'sha256': hashlib.sha256(),
        'sha512': hashlib.sha512(),
    }

    for filename in filenames:
        # for each files computes the different algorythm supported
        with open(os.path.join(folder, filename), "rb") as stream:
            while True:
                buf = stream.read(2 * 2 ** 10)
                if buf:
                    for hasher in algos.values():
                        hasher.update(buf)
                else:
                    break

        # Write them out to the output file
        with open(sha_file, 'a') as stream:
            if new_file:
                stream.write('# Generated and updated by pagure\n')
            for algo in algos:
                stream.write('%s (%s) = %s\n' % (
                    algo.upper(), filename, algos[algo].hexdigest()))


@conn.task(bind=True)
@pagure_task
def commits_author_stats(self, session, repopath):
    """ Returns some statistics about commits made against the specified
    git repository.
    """

    if not os.path.exists(repopath):
        raise ValueError('Git repository not found.')

    repo_obj = pygit2.Repository(repopath)

    stats = collections.defaultdict(int)
    number_of_commits = 0
    authors_email = set()
    for commit in repo_obj.walk(
            repo_obj.head.get_object().oid.hex, pygit2.GIT_SORT_TIME):
        # For each commit record how many times each combination of name and
        # e-mail appears in the git history.
        number_of_commits += 1
        email = commit.author.email
        author = commit.author.name
        stats[(author, email)] += 1

    for (name, email), val in stats.items():
        # For each recorded user info, check if we know the e-mail address of
        # the user.
        user = pagure.lib.search_user(session, email=email)
        if user and (user.default_email != email or user.fullname != name):
            # We know the the user, but the name or e-mail used in Git commit
            # does not match their default e-mail address and full name. Let's
            # merge them into one record.
            stats.pop((name, email))
            stats[(user.fullname, user.default_email)] += val

    # Generate a list of contributors ordered by how many commits they
    # authored. The list consists of tuples with number of commits and people
    # with that number of commits. Each contributor is represented by a name
    # and e-mail address.
    out_stats = collections.defaultdict(list)
    for authors, val in stats.items():
        authors_email.add(authors[1])
        out_stats[val].append(authors)
    out_list = [
        (key, out_stats[key])
        for key in sorted(out_stats, reverse=True)
    ]

    return (
        number_of_commits,
        out_list,
        len(authors_email),
        commit.commit_time
    )


@conn.task(bind=True)
@pagure_task
def commits_history_stats(self, session, repopath):
    """ Returns the evolution of the commits made against the specified
    git repository.
    """

    if not os.path.exists(repopath):
        raise ValueError('Git repository not found.')

    repo_obj = pygit2.Repository(repopath)

    dates = collections.defaultdict(int)
    for commit in repo_obj.walk(
            repo_obj.head.get_object().oid.hex, pygit2.GIT_SORT_TIME):
        delta = datetime.datetime.utcnow() \
            - arrow.get(commit.commit_time).naive
        if delta.days > 365:
            break
        dates[arrow.get(commit.commit_time).date().isoformat()] += 1

    return [(key, dates[key]) for key in sorted(dates)]
