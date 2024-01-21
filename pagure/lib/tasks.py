# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

from __future__ import absolute_import, unicode_literals

import collections
import datetime
import hashlib
import os
import os.path
import subprocess
import time

import arrow
import pygit2
import six
from celery import Celery
from celery.result import AsyncResult
from celery.signals import after_setup_task_logger
from celery.utils.log import get_task_logger
from sqlalchemy.exc import SQLAlchemyError

import pagure.lib.git
import pagure.lib.git_auth
import pagure.lib.link
import pagure.lib.model
import pagure.lib.query
import pagure.lib.repo
import pagure.utils
from pagure.config import config as pagure_config
from pagure.lib.tasks_utils import pagure_task
from pagure.utils import get_parent_repo_path

# logging.config.dictConfig(pagure_config.get('LOGGING') or {'version': 1})
_log = get_task_logger(__name__)


if os.environ.get("PAGURE_BROKER_URL"):
    broker_url = os.environ["PAGURE_BROKER_URL"]
elif pagure_config.get("BROKER_URL"):
    broker_url = pagure_config["BROKER_URL"]
else:
    broker_url = "redis://%s:%d/%d" % (
        pagure_config["REDIS_HOST"],
        pagure_config["REDIS_PORT"],
        pagure_config["REDIS_DB"],
    )

conn = Celery("tasks", broker=broker_url, backend=broker_url)
conn.conf.update(pagure_config["CELERY_CONFIG"])


@after_setup_task_logger.connect
def augment_celery_log(**kwargs):
    pagure.utils.set_up_logging(force=True)


def get_result(uuid):
    """Returns the AsyncResult object for a given task.

    :arg uuid: the unique identifier of the task to retrieve.
    :type uuid: str
    :return: celery.result.AsyncResult

    """
    return AsyncResult(uuid, conn.backend)


def ret(endpoint, **kwargs):
    toret = {"endpoint": endpoint}
    toret.update(kwargs)
    return toret


@conn.task(queue=pagure_config.get("GITOLITE_CELERY_QUEUE", None), bind=True)
@pagure_task
def generate_gitolite_acls(
    self, session, namespace=None, name=None, user=None, group=None
):
    """Generate the gitolite configuration file either entirely or for a
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
        project = pagure.lib.query._get_project(
            session, namespace=namespace, name=name, user=user
        )

    elif name == -1:
        project = name
    helper = pagure.lib.git_auth.get_git_auth_helper()
    _log.debug("Got helper: %s", helper)

    group_obj = None
    if group:
        group_obj = pagure.lib.query.search_groups(session, group_name=group)
    _log.debug(
        "Calling helper: %s with arg: project=%s, group=%s",
        helper,
        project,
        group_obj,
    )
    helper.generate_acls(project=project, group=group_obj)

    pagure.lib.query.update_read_only_mode(session, project, read_only=False)
    try:
        session.commit()
        _log.debug("Project %s is no longer in Read Only Mode", project)
    except SQLAlchemyError:
        session.rollback()
        _log.exception("Failed to unmark read_only for: %s project", project)


@conn.task(queue=pagure_config.get("GITOLITE_CELERY_QUEUE", None), bind=True)
@pagure_task
def gitolite_post_compile_only(self, session):
    """Do gitolite post-processing only. Most importantly, this processes SSH
    keys used by gitolite. This is an optimization task that's supposed to be
    used if you only need to run `gitolite trigger POST_COMPILE` without
    touching any other gitolite configuration
    """
    helper = pagure.lib.git_auth.get_git_auth_helper()
    _log.debug("Got helper: %s", helper)
    if hasattr(helper, "post_compile_only"):
        helper.post_compile_only()
    else:
        helper.generate_acls(project=None)


@conn.task(queue=pagure_config.get("GITOLITE_CELERY_QUEUE", None), bind=True)
@pagure_task
def delete_project(
    self, session, namespace=None, name=None, user=None, action_user=None
):
    """Delete a project in pagure.

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
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )

    if not project:
        raise RuntimeError(
            "Project: %s/%s from user: %s not found in the DB"
            % (namespace, name, user)
        )

    # Remove the project from gitolite.conf
    helper = pagure.lib.git_auth.get_git_auth_helper()
    _log.debug("Got helper: %s", helper)

    _log.debug(
        "Calling helper: %s with arg: project=%s", helper, project.fullname
    )
    helper.remove_acls(session=session, project=project)

    # Remove the git repositories on disk
    pagure.lib.git.delete_project_repos(project)

    # Remove the project from the DB
    username = project.user.user
    try:
        project_json = project.to_json(public=True)
        session.delete(project)
        session.commit()
        pagure.lib.notify.log(
            project,
            topic="project.deleted",
            msg=dict(project=project_json, agent=action_user),
        )
    except SQLAlchemyError:
        session.rollback()
        _log.exception(
            "Failed to delete project: %s from the DB", project.fullname
        )

    return ret("ui_ns.view_user", username=username)


@conn.task(queue=pagure_config.get("FAST_CELERY_QUEUE", None), bind=True)
@pagure_task
def create_project(
    self,
    session,
    username,
    namespace,
    name,
    add_readme,
    ignore_existing_repo,
    default_branch=None,
):
    """Create a project.

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
    :kwarg default_branch: the name of the default branch to create and set
        as default.
    :type default_branch: str or None

    """
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name
    )

    userobj = pagure.lib.query.search_user(session, username=username)

    # Add the readme file if it was asked
    templ = None
    if project.is_fork:
        templ = pagure_config.get("FORK_TEMPLATE_PATH")
    else:
        templ = pagure_config.get("PROJECT_TEMPLATE_PATH")
    if templ:
        if not os.path.exists(templ):
            _log.warning(
                "Invalid git template configured: %s, not found on disk", templ
            )
            templ = None
        else:
            _log.debug("  Using template at: %s", templ)

    # There is a risk for a race-condition here between when the repo is
    # created and when the README gets added. However, this risk is small
    # enough that we will keep this as is for now (esp since it fixes the
    # situation where deleting the project raised an error if it was in the
    # middle of the lock)
    try:
        with project.lock("WORKER"):
            pagure.lib.git.create_project_repos(
                project,
                templ,
                ignore_existing_repo,
            )
    except Exception:
        session.delete(project)
        session.commit()
        raise

    if default_branch:
        path = project.repopath("main")
        repo_obj = pygit2.Repository(path)
        repo_obj.set_head("refs/heads/%s" % default_branch)

    if add_readme:
        with project.lock("WORKER"):
            with pagure.lib.git.TemporaryClone(
                project, "main", "add_readme"
            ) as tempclone:
                temp_gitrepo = tempclone.repo
                if default_branch:
                    temp_gitrepo.set_head("refs/heads/%s" % default_branch)

                # Add README file
                author = userobj.fullname or userobj.user
                author_email = userobj.default_email
                if six.PY2:
                    author = author.encode("utf-8")
                    author_email = author_email.encode("utf-8")
                author = pygit2.Signature(author, author_email)
                content = "# %s\n\n%s" % (name, project.description)
                readme_file = os.path.join(temp_gitrepo.workdir, "README.md")
                with open(readme_file, "wb") as stream:
                    stream.write(content.encode("utf-8"))
                temp_gitrepo.index.add_all()
                temp_gitrepo.index.write()
                tree = temp_gitrepo.index.write_tree()
                temp_gitrepo.create_commit(
                    "HEAD", author, author, "Added the README", tree, []
                )

                master_ref = temp_gitrepo.lookup_reference("HEAD").resolve()
                tempclone.push("pagure", master_ref.name, internal="yes")

    task = generate_gitolite_acls.delay(
        namespace=project.namespace,
        name=project.name,
        user=project.user.user if project.is_fork else None,
    )
    _log.info("Refreshing gitolite config queued in task: %s", task.id)

    return ret("ui_ns.view_repo", repo=name, namespace=namespace)


@conn.task(queue=pagure_config.get("SLOW_CELERY_QUEUE", None), bind=True)
@pagure_task
def update_git(
    self, session, name, namespace, user, ticketuid=None, requestuid=None
):
    """Update the JSON representation of either a ticket or a pull-request
    depending on the argument specified.
    """
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )

    project_lock = "WORKER"
    if ticketuid is not None:
        project_lock = "WORKER_TICKET"
    elif requestuid is not None:
        project_lock = "WORKER_REQUEST"

    with project.lock(project_lock):
        if ticketuid is not None:
            obj = pagure.lib.query.get_issue_by_uid(session, ticketuid)
        elif requestuid is not None:
            obj = pagure.lib.query.get_request_by_uid(session, requestuid)
        else:
            raise NotImplementedError("No ticket ID or request ID provided")

        if obj is None:
            raise Exception("Unable to find object")

        result = pagure.lib.git._update_git(obj, project)

    return result


@conn.task(queue=pagure_config.get("SLOW_CELERY_QUEUE", None), bind=True)
@pagure_task
def clean_git(self, session, name, namespace, user, obj_repotype, obj_uid):
    """Remove the JSON representation of a ticket on the git repository
    for tickets.
    """
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )

    with project.lock("WORKER_TICKET"):
        result = pagure.lib.git._clean_git(project, obj_repotype, obj_uid)

    return result


@conn.task(queue=pagure_config.get("MEDIUM_CELERY_QUEUE", None), bind=True)
@pagure_task
def update_file_in_git(
    self,
    session,
    name,
    namespace,
    user,
    branch,
    branchto,
    filename,
    content,
    message,
    username,
    email,
):
    """Update a file in the specified git repo."""
    userobj = pagure.lib.query.search_user(session, username=username)
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )

    with project.lock("WORKER"):
        pagure.lib.git._update_file_in_git(
            project,
            branch,
            branchto,
            filename,
            content,
            message,
            userobj,
            email,
        )

    return ret(
        "ui_ns.view_commits",
        repo=project.name,
        username=user,
        namespace=namespace,
        branchname=branchto,
    )


@conn.task(queue=pagure_config.get("MEDIUM_CELERY_QUEUE", None), bind=True)
@pagure_task
def delete_branch(self, session, name, namespace, user, branchname):
    """Delete a branch from a git repo."""
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )

    with project.lock("WORKER"):
        repo_obj = pygit2.Repository(pagure.utils.get_repo_path(project))

        try:
            branch = repo_obj.lookup_branch(branchname)
            branch.delete()
        except pygit2.GitError as err:
            _log.exception(err)

    return ret(
        "ui_ns.view_branches", repo=name, namespace=namespace, username=user
    )


@conn.task(queue=pagure_config.get("MEDIUM_CELERY_QUEUE", None), bind=True)
@pagure_task
def fork(
    self,
    session,
    name,
    namespace,
    user_owner,
    user_forker,
    editbranch,
    editfile,
):
    """Forks the specified project for the specified user.

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
    repo_from = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user_owner
    )

    repo_to = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user_forker
    )

    with repo_to.lock("WORKER"):
        pagure.lib.git.create_project_repos(repo_to, None, False)

        with pagure.lib.git.TemporaryClone(
            repo_from, "main", "fork"
        ) as tempclone:
            for branchname in tempclone.repo.branches.remote:
                if (
                    branchname.startswith("origin/")
                    and branchname != "origin/HEAD"
                ):
                    locbranch = branchname[len("origin/") :]
                    if locbranch in tempclone.repo.branches.local:
                        continue
                    branch = tempclone.repo.branches.remote.get(branchname)
                    tempclone.repo.branches.local.create(
                        locbranch, branch.peel()
                    )
            tempclone.change_project_association(repo_to)
            tempclone.mirror("pagure", internal_no_hooks="yes")

        if not repo_to.private:
            # Create the git-daemon-export-ok file on the clone
            http_clone_file = os.path.join(
                repo_to.repopath("main"), "git-daemon-export-ok"
            )
        if not os.path.exists(http_clone_file):
            with open(http_clone_file, "w"):
                pass

        # Finally set the default branch to be the same as the parent
        repo_from_obj = pygit2.Repository(repo_from.repopath("main"))
        repo_to_obj = pygit2.Repository(repo_to.repopath("main"))
        repo_to_obj.set_head(repo_from_obj.lookup_reference("HEAD").target)

        pagure.lib.notify.log(
            repo_to,
            topic="project.forked",
            msg=dict(project=repo_to.to_json(public=True), agent=user_forker),
        )

    _log.info("Project created, refreshing auth async")
    task = generate_gitolite_acls.delay(
        namespace=repo_to.namespace,
        name=repo_to.name,
        user=repo_to.user.user if repo_to.is_fork else None,
    )
    _log.info("Refreshing gitolite config queued in task: %s", task.id)

    if editfile is None:
        return ret(
            "ui_ns.view_repo",
            repo=name,
            namespace=namespace,
            username=user_forker,
        )
    else:
        return ret(
            "ui_ns.edit_file",
            repo=name,
            namespace=namespace,
            username=user_forker,
            branchname=editbranch,
            filename=editfile,
        )


@conn.task(queue=pagure_config.get("FAST_CELERY_QUEUE", None), bind=True)
@pagure_task
def pull_remote_repo(self, session, remote_git, branch_from):
    """Clone a remote git repository locally for remote PRs."""

    clonepath = pagure.utils.get_remote_repo_path(
        remote_git, branch_from, ignore_non_exist=True
    )

    pagure.lib.repo.PagureRepo.clone(
        remote_git, clonepath, checkout_branch=branch_from
    )

    return clonepath


@conn.task(queue=pagure_config.get("MEDIUM_CELERY_QUEUE", None), bind=True)
@pagure_task
def refresh_remote_pr(self, session, name, namespace, user, requestid):
    """Refresh the local clone of a git repository used in a remote
    pull-request.
    """
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )

    request = pagure.lib.query.search_pull_requests(
        session, project_id=project.id, requestid=requestid
    )
    _log.debug(
        "refreshing remote pull-request: %s/#%s",
        request.project.fullname,
        request.id,
    )

    clonepath = pagure.utils.get_remote_repo_path(
        request.remote_git, request.branch_from
    )

    repo = pagure.lib.repo.PagureRepo(clonepath)
    repo.pull(branch=request.branch_from, force=True)

    refresh_pr_cache.delay(name, namespace, user)
    del repo
    return ret(
        "ui_ns.request_pull",
        username=user,
        namespace=namespace,
        repo=name,
        requestid=requestid,
    )


@conn.task(queue=pagure_config.get("FAST_CELERY_QUEUE", None), bind=True)
@pagure_task
def refresh_pr_cache(self, session, name, namespace, user, but_uids=None):
    """Refresh the merge status cached of pull-requests."""
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )

    pagure.lib.query.reset_status_pull_request(
        session, project, but_uids=but_uids
    )


@conn.task(queue=pagure_config.get("FAST_CELERY_QUEUE", None), bind=True)
@pagure_task
def rebase_pull_request(
    self, session, name, namespace, user, requestid, user_rebaser
):
    """Rebase a pull-request."""
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )
    _log.info("Rebase PR: %s of project: %s" % (requestid, project.fullname))

    with project.lock("WORKER"):
        request = pagure.lib.query.search_pull_requests(
            session, project_id=project.id, requestid=requestid
        )
        _log.debug(
            "Rebasing pull-request: %s#%s, uid: %s",
            request.project.fullname,
            request.id,
            request.uid,
        )
        pagure.lib.git.rebase_pull_request(session, request, user_rebaser)

    update_pull_request(request.uid, username=user_rebaser)
    # Schedule refresh of all opened PRs
    pagure.lib.query.reset_status_pull_request(session, request.project)


@conn.task(queue=pagure_config.get("FAST_CELERY_QUEUE", None), bind=True)
@pagure_task
def merge_pull_request(
    self,
    session,
    name,
    namespace,
    user,
    requestid,
    user_merger,
    delete_branch_after=False,
):
    """Merge pull-request."""
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )

    with project.lock("WORKER"):
        request = pagure.lib.query.search_pull_requests(
            session, project_id=project.id, requestid=requestid
        )
        _log.debug(
            "Merging pull-request: %s/#%s",
            request.project.fullname,
            request.id,
        )
        pagure.lib.git.merge_pull_request(session, request, user_merger)

    if delete_branch_after:
        _log.debug(
            "Will delete source branch of pull-request: %s/#%s",
            request.project.fullname,
            request.id,
        )
        owner = (
            request.project_from.user.username
            if request.project_from.parent
            else None
        )
        delete_branch.delay(
            request.project_from.name,
            request.project_from.namespace,
            owner,
            request.branch_from,
        )

    refresh_pr_cache.delay(name, namespace, user)
    return ret(
        "ui_ns.request_pull",
        repo=name,
        requestid=requestid,
        username=user,
        namespace=namespace,
    )


@conn.task(queue=pagure_config.get("FAST_CELERY_QUEUE", None), bind=True)
@pagure_task
def add_file_to_git(
    self, session, name, namespace, user, user_attacher, issueuid, filename
):
    """Add a file to the specified git repo."""
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )

    with project.lock("WORKER"):
        issue = pagure.lib.query.get_issue_by_uid(session, issueuid)
        user_attacher = pagure.lib.query.search_user(
            session, username=user_attacher
        )

        from_folder = pagure_config["ATTACHMENTS_FOLDER"]
        _log.info(
            "Adding file %s from %s to %s",
            filename,
            from_folder,
            project.fullname,
        )
        pagure.lib.git._add_file_to_git(
            project, issue, from_folder, user_attacher, filename
        )


@conn.task(queue=pagure_config.get("MEDIUM_CELERY_QUEUE", None), bind=True)
@pagure_task
def project_dowait(self, session, name, namespace, user):
    """This is a task used to test the locking systems.

    It should never be allowed to be called in production instances, since that
    would allow an attacker to basically DOS a project by calling this
    repeatedly."""
    assert pagure_config.get("ALLOW_PROJECT_DOWAIT", False)

    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )

    with project.lock("WORKER"):
        time.sleep(10)

    return ret(
        "ui_ns.view_repo", repo=name, username=user, namespace=namespace
    )


@conn.task(queue=pagure_config.get("MEDIUM_CELERY_QUEUE", None), bind=True)
@pagure_task
def sync_pull_ref(self, session, name, namespace, user, requestid):
    """Synchronize a pull/ reference from the content in the forked repo,
    allowing local checkout of the pull-request.
    """
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )

    with project.lock("WORKER"):
        request = pagure.lib.query.search_pull_requests(
            session, project_id=project.id, requestid=requestid
        )
        _log.debug(
            "Update pull refs of: %s#%s", request.project.fullname, request.id
        )

        if request.remote:
            # Get the fork
            repopath = pagure.utils.get_remote_repo_path(
                request.remote_git, request.branch_from
            )
        elif request.project_from:
            # Get the fork
            repopath = pagure.utils.get_repo_path(request.project_from)
        else:
            return
        _log.debug("   working on the repo in: %s", repopath)

        repo_obj = pygit2.Repository(repopath)
        pagure.lib.git.update_pull_ref(request, repo_obj)


@conn.task(queue=pagure_config.get("FAST_CELERY_QUEUE", None), bind=True)
@pagure_task
def update_pull_request(self, session, pr_uid, username=None):
    """Updates a pull-request in the DB once a commit was pushed to it in
    git.
    """
    request = pagure.lib.query.get_request_by_uid(session, pr_uid)

    with request.project.lock("WORKER"):

        _log.debug(
            "Updating pull-request: %s#%s",
            request.project.fullname,
            request.id,
        )

        try:
            pagure.lib.git.merge_pull_request(
                session=session,
                request=request,
                username=username,
                domerge=False,
            )
        except pagure.exceptions.PagureException as err:
            _log.debug(err)


@conn.task(queue=pagure_config.get("MEDIUM_CELERY_QUEUE", None), bind=True)
@pagure_task
def update_checksums_file(self, session, folder, filenames):
    """Update the checksums file in the release folder of the project."""

    sha_file = os.path.join(folder, "CHECKSUMS")
    new_file = not os.path.exists(sha_file)

    if not new_file:
        with open(sha_file) as stream:
            row = stream.readline().strip()
            if row != "# Generated and updated by pagure":
                # This wasn't generated by pagure, don't touch it!
                return

    for filename in filenames:
        algos = {"sha256": hashlib.sha256(), "sha512": hashlib.sha512()}
        # for each files computes the different algorythm supported
        with open(os.path.join(folder, filename), "rb") as stream:
            while True:
                buf = stream.read(2 * 2**10)  # fmt: skip
                if buf:
                    for hasher in algos.values():
                        hasher.update(buf)
                else:
                    break

        # Write them out to the output file
        with open(sha_file, "a") as stream:
            if new_file:
                stream.write("# Generated and updated by pagure\n")
                new_file = False
            for algo in sorted(algos):
                stream.write(
                    "%s (%s) = %s\n"
                    % (algo.upper(), filename, algos[algo].hexdigest())
                )


@conn.task(queue=pagure_config.get("FAST_CELERY_QUEUE", None), bind=True)
@pagure_task
def commits_author_stats(self, session, repopath):
    """Returns some statistics about commits made against the specified
    git repository.
    """

    if not os.path.exists(repopath):
        raise ValueError("Git repository not found.")

    repo_obj = pygit2.Repository(repopath)

    stats = collections.defaultdict(int)
    number_of_commits = 0
    authors_email = set()
    for commit in repo_obj.walk(
        repo_obj.head.peel().oid.hex, pygit2.GIT_SORT_NONE
    ):
        # For each commit record how many times each combination of name and
        # e-mail appears in the git history.
        number_of_commits += 1
        email = commit.author.email
        author = commit.author.name
        stats[(author, email)] += 1

    for (name, email), val in list(stats.items()):
        if not email:
            # Author email is missing in the git commit.
            continue
        # For each recorded user info, check if we know the e-mail address of
        # the user.
        user = pagure.lib.query.search_user(session, email=email)
        if user and (user.default_email != email or user.fullname != name):
            # We know the the user, but the name or e-mail used in Git commit
            # does not match their default e-mail address and full name. Let's
            # merge them into one record.
            stats.pop((name, email))
            stats[(user.fullname, user.default_email)] += val

    # Generate a list of contributors ordered by how many commits they
    # authored. The list consists of tuples with number of commits and people
    # with that number of commits. Each contributor is represented by a tuple
    # of name, e-mail address and avatar url.
    out_stats = collections.defaultdict(list)
    for authors, val in stats.items():
        authors_email.add(authors[1])
        out_authors = list(authors)
        out_authors.append(
            pagure.lib.query.avatar_url_from_email(authors[1], size=32)
        )
        out_stats[val].append(tuple(out_authors))
    out_list = [
        (key, out_stats[key]) for key in sorted(out_stats, reverse=True)
    ]

    return (
        number_of_commits,
        out_list,
        len(authors_email),
        commit.commit_time,
    )


@conn.task(queue=pagure_config.get("FAST_CELERY_QUEUE", None), bind=True)
@pagure_task
def commits_history_stats(self, session, repopath):
    """Returns the evolution of the commits made against the specified
    git repository.
    """

    if not os.path.exists(repopath):
        raise ValueError("Git repository not found.")

    repo_obj = pygit2.Repository(repopath)

    dates = collections.defaultdict(int)
    for commit in repo_obj.walk(
        repo_obj.head.peel().oid.hex, pygit2.GIT_SORT_NONE
    ):
        delta = (
            datetime.datetime.utcnow() - arrow.get(commit.commit_time).naive
        )
        if delta.days > 365:
            break
        dates[arrow.get(commit.commit_time).date().isoformat()] += 1

    return [(key, dates[key]) for key in sorted(dates)]


@conn.task(queue=pagure_config.get("MEDIUM_CELERY_QUEUE", None), bind=True)
@pagure_task
def link_pr_to_ticket(self, session, pr_uid):
    """Link the specified pull-request against the ticket(s) mentioned in
    the commits of the pull-request

    """
    _log.info("LINK_PR_TO_TICKET: Linking ticket(s) to PR for: %s" % pr_uid)

    request = pagure.lib.query.get_request_by_uid(session, pr_uid)
    if not request:
        _log.info("LINK_PR_TO_TICKET: Not PR found for: %s" % pr_uid)
        return

    if request.remote:
        repopath = pagure.utils.get_remote_repo_path(
            request.remote_git, request.branch_from
        )
        parentpath = pagure.utils.get_repo_path(request.project)
    elif request.project_from:
        repo_from = request.project_from
        repopath = pagure.utils.get_repo_path(repo_from)
        parentpath = get_parent_repo_path(repo_from)
    else:
        _log.info(
            "LINK_PR_TO_TICKET: PR neither remote, nor with a "
            "project_from, bailing: %s" % pr_uid
        )
        return

    # Drop the existing commit-based relations
    session.query(pagure.lib.model.PrToIssue).filter(
        pagure.lib.model.PrToIssue.pull_request_uid == request.uid
    ).filter(pagure.lib.model.PrToIssue.origin == "intial_comment_pr").delete(
        synchronize_session="fetch"
    )

    repo_obj = pygit2.Repository(repopath)
    orig_repo = pygit2.Repository(parentpath)

    diff_commits = pagure.lib.git.diff_pull_request(
        session, request, repo_obj, orig_repo, with_diff=False, notify=False
    )

    _log.info(
        "LINK_PR_TO_TICKET: Found %s commits in that PR" % len(diff_commits)
    )

    name = request.project.name
    namespace = request.project.namespace
    user = request.project.user.user if request.project.is_fork else None

    for line in pagure.lib.git.read_git_lines(
        ["log", "--no-walk"] + [c.oid.hex for c in diff_commits] + ["--"],
        repopath,
    ):

        line = line.strip()
        for issue in pagure.lib.link.get_relation(
            session, name, user, namespace, line, "fixes", include_prs=False
        ):
            _log.info(
                "LINK_PR_TO_TICKET: Link ticket %s to PRs %s"
                % (issue, request)
            )
            pagure.lib.query.link_pr_issue(
                session, issue, request, origin="commit"
            )

        for issue in pagure.lib.link.get_relation(
            session, name, user, namespace, line, "relates"
        ):
            _log.info(
                "LINK_PR_TO_TICKET: Link ticket %s to PRs %s"
                % (issue, request)
            )
            pagure.lib.query.link_pr_issue(
                session, issue, request, origin="commit"
            )

    try:
        session.commit()
    except SQLAlchemyError:
        _log.exception("Could not link ticket to PR :(")
        session.rollback()


@conn.task(queue=pagure_config.get("MEDIUM_CELERY_QUEUE", None), bind=True)
@pagure_task
def pull_request_ready_branch(self, session, namespace, name, user):
    repo = pagure.lib.query._get_project(
        session, name, user=user, namespace=namespace
    )
    repo_path = pagure.utils.get_repo_path(repo)
    repo_obj = pygit2.Repository(repo_path)

    if repo.is_fork and repo.parent:
        parentreponame = pagure.utils.get_repo_path(repo.parent)
        parent_repo_obj = pygit2.Repository(parentreponame)
    else:
        parent_repo_obj = repo_obj

    branches = {}
    if not repo_obj.is_empty and len(repo_obj.listall_branches()) > 0:
        branch_names = (
            pagure.lib.repo.PagureRepo.get_active_branches(
                repo_path, catch_exception=True
            )
            or repo_obj.listall_branches()
        )
        for branchname in branch_names:
            compare_branch = None
            if (
                not parent_repo_obj.is_empty
                and not parent_repo_obj.head_is_unborn
            ):
                try:
                    if pagure.config.config.get(
                        "PR_TARGET_MATCHING_BRANCH", False
                    ):
                        # find parent branch which is the longest substring of
                        # branch that we're processing
                        compare_branch = ""
                        for parent_branch in parent_repo_obj.branches:
                            if (
                                not repo.is_fork
                                and branchname == parent_branch
                            ):
                                continue
                            if branchname.startswith(parent_branch) and len(
                                parent_branch
                            ) > len(compare_branch):
                                compare_branch = parent_branch
                        compare_branch = (
                            compare_branch or repo_obj.head.shorthand
                        )
                    else:
                        compare_branch = repo_obj.head.shorthand
                except pygit2.GitError:
                    pass  # let compare_branch be None

            # Do not compare a branch to itself
            if (
                not repo.is_fork
                and compare_branch
                and compare_branch == branchname
            ):
                continue

            diff_commits = None
            try:
                _, diff_commits, _ = pagure.lib.git.get_diff_info(
                    repo_obj, parent_repo_obj, branchname, compare_branch
                )
            except pagure.exceptions.PagureException:
                pass

            if diff_commits:
                branches[branchname] = {
                    "commits": len(list(diff_commits)),
                    "target_branch": compare_branch or "master",
                }

    prs = pagure.lib.query.search_pull_requests(
        session, project_id_from=repo.id, status="Open"
    )
    branches_pr = {}
    for pr in prs:
        if pr.branch_from in branches:
            branches_pr[pr.branch_from] = "%s/pull-request/%s" % (
                pr.project.url_path,
                pr.id,
            )
            del branches[pr.branch_from]
    return {"new_branch": branches, "branch_w_pr": branches_pr}


@conn.task(queue=pagure_config.get("MEDIUM_CELERY_QUEUE", None), bind=True)
@pagure_task
def git_garbage_collect(self, session, repopath):
    # libgit2 doesn't support "git gc" and probably never will:
    # https://github.com/libgit2/libgit2/issues/3247
    _log.info("Running 'git gc --auto' for repo %s", repopath)
    subprocess.check_output(["git", "gc", "--auto", "-q"], cwd=repopath)


@conn.task(queue=pagure_config.get("FAST_CELERY_QUEUE", None), bind=True)
@pagure_task
def generate_archive(
    self, session, project, namespace, username, commit, tag, name, archive_fmt
):
    """Generate the archive of the specified project on the specified
    commit with the given name and archive format.
    Currently only support the following format: gzip and tar.gz

    """
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=project, user=username
    )

    _log.debug(
        "Generating archive for %s, commit: %s as: %s.%s",
        project.fullname,
        commit,
        name,
        archive_fmt,
    )

    pagure.lib.git.generate_archive(project, commit, tag, name, archive_fmt)

    if archive_fmt == "gzip":
        endpoint = "ui_ns.get_project_archive_gzip"
    elif archive_fmt == "tar":
        endpoint = "ui_ns.get_project_archive_tar"
    else:
        endpoint = "ui_ns.get_project_archive_tar_gz"
    return ret(
        endpoint,
        repo=project.name,
        ref=commit,
        name=name,
        namespace=project.namespace,
        username=project.user.user if project.is_fork else None,
    )


@conn.task(queue=pagure_config.get("AUTHORIZED_KEYS_QUEUE", None), bind=True)
@pagure_task
def add_key_to_authorized_keys(self, session, ssh_folder, username, sshkey):
    """Add the specified key to the the `authorized_keys` file of the
    specified ssh folder.
    """
    if not os.path.exists(ssh_folder):
        _log.info("No folder '%s' found", ssh_folder)
        return

    fullpath = os.path.join(ssh_folder, "authorized_keys")
    _log.info("Add ssh key for user %s to %s", username, fullpath)
    with open(fullpath, "a") as stream:
        stream.write("\n")
        stream.write(
            "{0} {1}".format(
                pagure_config["SSH_KEYS_OPTIONS"] % {"username": username},
                sshkey.strip(),
            )
        )
    os.chmod(fullpath, 0o600)


@conn.task(queue=pagure_config.get("AUTHORIZED_KEYS_QUEUE", None), bind=True)
@pagure_task
def remove_key_from_authorized_keys(self, session, ssh_folder, sshkey):
    """Remove the specified key from the the `authorized_keys` file of the
    specified ssh folder.
    """
    if not os.path.exists(ssh_folder):
        _log.info("No folder '%s' found", ssh_folder)
        return

    fullpath = os.path.join(ssh_folder, "authorized_keys")
    _log.info("Removing ssh key in %s", fullpath)
    output = []
    with open(fullpath, "r") as stream:
        for row in stream.readlines():
            row = row.strip()
            if sshkey in row:
                continue
            output.append(row)

    with open(fullpath, "w") as stream:
        stream.write("\n".join(output))
    os.chmod(fullpath, 0o600)
