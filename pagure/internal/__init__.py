# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

Internal endpoints.

"""

from __future__ import absolute_import, unicode_literals

import collections
import logging
import os
from functools import wraps

import flask
import pygit2
import werkzeug.utils
from sqlalchemy.exc import SQLAlchemyError

PV = flask.Blueprint("internal_ns", __name__, url_prefix="/pv")

import pagure  # noqa: E402
import pagure.exceptions  # noqa: E402
import pagure.forms  # noqa: E402
import pagure.lib.git  # noqa: E402
import pagure.lib.query  # noqa: E402
import pagure.lib.tasks  # noqa: E402
import pagure.ui.fork  # noqa: E402
import pagure.utils  # noqa: E402
from pagure.config import config as pagure_config  # noqa: E402

_log = logging.getLogger(__name__)
_auth_log = logging.getLogger("pagure_auth")


MERGE_OPTIONS = {
    "NO_CHANGE": {
        "short_code": "No changes",
        "message": "Nothing to change, git is up to date",
    },
    "FFORWARD": {
        "short_code": "Ok",
        "message": "The pull-request can be merged and fast-forwarded",
    },
    "CONFLICTS": {
        "short_code": "Conflicts",
        "message": "The pull-request cannot be merged due to conflicts",
    },
    "MERGE": {
        "short_code": "With merge",
        "message": "The pull-request can be merged with a merge commit",
    },
}


def internal_access_only(function):
    """Decorator used to check if the request is iternal or not.

    The request must either come from one of the addresses listed
    in IP_ALLOWED_INTERNAL or it must have the "Authentication"
    header set to "token <admin_token>" and the token must
    have "internal_access" ACL.
    """

    @wraps(function)
    def decorated_function(*args, **kwargs):
        """Wrapped function actually checking if the request is local."""
        ip_allowed = pagure_config.get(
            "IP_ALLOWED_INTERNAL", ["127.0.0.1", "localhost", "::1"]
        )
        if "Authorization" in flask.request.headers:
            res = pagure.utils.check_api_acls(acls=["internal_access"])
            if res:
                return res
        elif flask.request.remote_addr not in ip_allowed:
            _log.debug(
                "IP: %s is not in the list of allowed IPs: %s "
                "and 'Authorization' header not provided"
                % (flask.request.remote_addr, ip_allowed)
            )
            flask.abort(403)
        return function(*args, **kwargs)

    return decorated_function


@PV.route("/ssh/lookupkey/", methods=["POST"])
@internal_access_only
def lookup_ssh_key():
    """Looks up an SSH key by search_key for keyhelper.py"""
    search_key = flask.request.form["search_key"]
    username = flask.request.form.get("username")
    _auth_log.info(
        "User is trying to access pagure using the ssh key: %s -- "
        "|user: %s|IP: %s|method: N/A|repo: N/A|query: N/A"
        % (search_key, username, flask.request.remote_addr)
    )
    key = pagure.lib.query.find_ssh_key(flask.g.session, search_key, username)

    if not key:
        return flask.jsonify({"found": False})

    result = {"found": True, "public_key": key.public_ssh_key}

    if key.user:
        result["username"] = key.user.username
    elif key.project:
        result["username"] = "deploykey_%s_%s" % (
            werkzeug.utils.secure_filename(key.project.fullname),
            key.id,
        )
    else:
        return flask.jsonify({"found": False})

    return flask.jsonify(result)


@PV.route("/ssh/checkaccess/", methods=["POST"])
@internal_access_only
def check_ssh_access():
    """Determines whether a user has read access to the requested repo."""
    gitdir = flask.request.form["gitdir"]
    remoteuser = flask.request.form["username"]
    _auth_log.info(
        "User is asking to access a project via ssh -- "
        "|user: %s|IP: %s|method: N/A|repo: %s|query: N/A"
        % (remoteuser, flask.request.remote_addr, gitdir)
    )

    # Build a fake path so we can use get_repo_info_from_path
    path = os.path.join(pagure_config["GIT_FOLDER"], gitdir)
    _auth_log.info(
        "%s asks to access %s (path: %s) via ssh" % (remoteuser, gitdir, path)
    )
    _log.info(
        "%s asks to access %s (path: %s) via ssh" % (remoteuser, gitdir, path)
    )
    (
        repotype,
        project_user,
        namespace,
        repo,
    ) = pagure.lib.git.get_repo_info_from_path(path, hide_notfound=True)

    _auth_log.info(
        "%s asks to access the %s repo of %s/%s from user %s"
        % (remoteuser, repotype, namespace, repo, project_user)
    )
    _log.info(
        "%s asks to access the %s repo of %s/%s from user %s"
        % (remoteuser, repotype, namespace, repo, project_user)
    )

    if repo is None:
        _log.info("Project name could not be extracted from path")
        _auth_log.info(
            "The path specified by the user could not be matched with a "
            "project -- "
            "|user: %s|IP: %s|method: N/A|repo: %s|query: N/A"
            % (remoteuser, flask.request.remote_addr, gitdir)
        )
        return flask.jsonify({"access": False})

    project = pagure.lib.query.get_authorized_project(
        flask.g.session,
        repo,
        user=project_user,
        namespace=namespace,
        asuser=remoteuser,
    )

    if not project:
        _auth_log.info(
            "User tried to access a private project they don't have access "
            "to -- |user: %s|IP: %s|method: N/A|repo: %s|query: N/A"
            % (remoteuser, flask.request.remote_addr, gitdir)
        )
        _log.info("Project not found with this path")
        return flask.jsonify({"access": False})

    _auth_log.info("Checking ACLs on project: %s" % project.fullname)
    _log.info("Checking ACLs on project: %s" % project.fullname)

    if repotype not in ["main", "docs"] and not pagure.utils.is_repo_user(
        project, remoteuser
    ):
        # Deploy keys are not allowed on ticket and PR repos but they are
        # allowed for main and docs repos.
        _log.info("%s is not a contributor to this project" % remoteuser)
        _auth_log.info(
            "User tried to access a project they do not have access to -- "
            "|user: %s|IP: %s|method: N/A|repo: %s|query: N/A"
            % (remoteuser, flask.request.remote_addr, gitdir)
        )
        return flask.jsonify({"access": False})

    _auth_log.info(
        "Read access granted to %s on: %s" % (remoteuser, project.fullname)
    )
    _log.info(
        "Read access granted to %s on: %s" % (remoteuser, project.fullname)
    )
    return flask.jsonify(
        {
            "access": True,
            "reponame": gitdir,
            "repospanner_reponame": project._repospanner_repo_name(repotype)
            if project.is_on_repospanner
            else None,
            "repopath": path,
            "repotype": repotype,
            "region": project.repospanner_region,
            "project_name": project.name,
            "project_user": project.user.username if project.is_fork else None,
            "project_namespace": project.namespace,
        }
    )


@PV.route("/pull-request/comment/", methods=["PUT"])
@internal_access_only
def pull_request_add_comment():
    """Add a comment to a pull-request."""
    pform = pagure.forms.ProjectCommentForm(meta={"csrf": False})
    if not pform.validate_on_submit():
        flask.abort(400, description="Invalid request")

    objid = pform.objid.data
    useremail = pform.useremail.data

    request = pagure.lib.query.get_request_by_uid(
        flask.g.session, request_uid=objid
    )

    if not request:
        flask.abort(404, description="Pull-request not found")

    form = pagure.forms.AddPullRequestCommentForm(meta={"csrf": False})

    if not form.validate_on_submit():
        flask.abort(400, description="Invalid request")

    commit = form.commit.data or None
    tree_id = form.tree_id.data or None
    filename = form.filename.data or None
    row = form.row.data or None
    comment = form.comment.data

    try:
        message = pagure.lib.query.add_pull_request_comment(
            flask.g.session,
            request=request,
            commit=commit,
            tree_id=tree_id,
            filename=filename,
            row=row,
            comment=comment,
            user=useremail,
        )
        flask.g.session.commit()
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        _log.exception(err)
        flask.abort(
            500, description="Error when saving the request to the database"
        )

    return flask.jsonify({"message": message})


@PV.route("/ticket/comment/", methods=["PUT"])
@internal_access_only
def ticket_add_comment():
    """Add a comment to an issue."""
    pform = pagure.forms.ProjectCommentForm(meta={"csrf": False})
    if not pform.validate_on_submit():
        flask.abort(400, description="Invalid request")

    objid = pform.objid.data
    useremail = pform.useremail.data

    issue = pagure.lib.query.get_issue_by_uid(flask.g.session, issue_uid=objid)

    if issue is None:
        flask.abort(404, description="Issue not found")

    user_obj = pagure.lib.query.search_user(flask.g.session, email=useremail)
    admin = False
    if user_obj:
        admin = user_obj.user == issue.project.user.user or (
            user_obj.user in [user.user for user in issue.project.committers]
        )

    if (
        issue.private
        and user_obj
        and not admin
        and not issue.user.user == user_obj.username
    ):
        flask.abort(
            403,
            description="This issue is private and you are not allowed "
            "to view it",
        )

    form = pagure.forms.CommentForm(meta={"csrf": False})

    if not form.validate_on_submit():
        flask.abort(400, description="Invalid request")

    comment = form.comment.data

    try:
        message = pagure.lib.query.add_issue_comment(
            flask.g.session,
            issue=issue,
            comment=comment,
            user=useremail,
            notify=True,
        )
        flask.g.session.commit()
    except SQLAlchemyError as err:  # pragma: no cover
        flask.g.session.rollback()
        _log.exception(err)
        flask.abort(
            500, description="Error when saving the request to the database"
        )

    return flask.jsonify({"message": message})


@PV.route("/pull-request/merge", methods=["POST"])
def mergeable_request_pull():
    """Returns if the specified pull-request can be merged or not."""
    force = flask.request.form.get("force", False)
    if force is not False:
        force = True

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        response = flask.jsonify(
            {"code": "CONFLICTS", "message": "Invalid input submitted"}
        )
        response.status_code = 400
        return response

    requestid = flask.request.form.get("requestid")

    request = pagure.lib.query.get_request_by_uid(
        flask.g.session, request_uid=requestid
    )

    if not request:
        response = flask.jsonify(
            {"code": "CONFLICTS", "message": "Pull-request not found"}
        )
        response.status_code = 404
        return response

    merge_status = request.merge_status
    if not merge_status or force:
        username = None
        if flask.g.authenticated:
            username = flask.g.fas_user.username
        try:
            merge_status = pagure.lib.git.merge_pull_request(
                session=flask.g.session,
                request=request,
                username=username,
                domerge=False,
            )
        except pygit2.GitError as err:
            response = flask.jsonify(
                {"code": "CONFLICTS", "message": "%s" % err}
            )
            response.status_code = 409
            return response
        except pagure.exceptions.PagureException as err:
            response = flask.jsonify(
                {"code": "CONFLICTS", "message": "%s" % err}
            )
            response.status_code = 500
            return response

    threshold = request.project.settings.get(
        "Minimum_score_to_merge_pull-request", -1
    )
    if threshold > 0 and int(request.score) < int(threshold):
        response = flask.jsonify(
            {
                "code": "CONFLICTS",
                "message": "Pull-Request does not meet the minimal "
                "number of review required: %s/%s"
                % (request.score, threshold),
            }
        )
        response.status_code = 400
        return response

    return flask.jsonify(pagure.utils.get_merge_options(request, merge_status))


@PV.route("/pull-request/ready", methods=["POST"])
def get_pull_request_ready_branch():
    """Return the list of branches that have commits not in the main
    branch/repo (thus for which one could open a PR) and the number of
    commits that differ.
    """
    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        response = flask.jsonify(
            {"code": "ERROR", "message": "Invalid input submitted"}
        )
        response.status_code = 400
        return response

    args_reponame = flask.request.form.get("repo", "").strip() or None
    args_namespace = flask.request.form.get("namespace", "").strip() or None
    args_user = flask.request.form.get("repouser", "").strip() or None

    repo = pagure.lib.query.get_authorized_project(
        flask.g.session,
        args_reponame,
        namespace=args_namespace,
        user=args_user,
    )

    if not repo:
        response = flask.jsonify(
            {
                "code": "ERROR",
                "message": "No repo found with the information provided",
            }
        )
        response.status_code = 404
        return response

    if repo.is_fork and repo.parent:
        if not repo.parent.settings.get("pull_requests", True):
            response = flask.jsonify(
                {
                    "code": "ERROR",
                    "message": "Pull-request have been disabled for this repo",
                }
            )
            response.status_code = 400
            return response
    else:
        if not repo.settings.get("pull_requests", True):
            response = flask.jsonify(
                {
                    "code": "ERROR",
                    "message": "Pull-request have been disabled for this repo",
                }
            )
            response.status_code = 400
            return response
    task = pagure.lib.tasks.pull_request_ready_branch.delay(
        namespace=args_namespace, name=args_reponame, user=args_user
    )

    return flask.jsonify({"code": "OK", "task": task.id})


@PV.route("/<repo>/issue/template", methods=["POST"])
@PV.route("/<namespace>/<repo>/issue/template", methods=["POST"])
@PV.route("/fork/<username>/<repo>/issue/template", methods=["POST"])
@PV.route(
    "/fork/<username>/<namespace>/<repo>/issue/template", methods=["POST"]
)
def get_ticket_template(repo, namespace=None, username=None):
    """Return the template asked for the specified project"""

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        response = flask.jsonify(
            {"code": "ERROR", "message": "Invalid input submitted"}
        )
        response.status_code = 400
        return response

    template = flask.request.args.get("template", None)
    if not template:
        response = flask.jsonify(
            {"code": "ERROR", "message": "No template provided"}
        )
        response.status_code = 400
        return response

    repo = pagure.lib.query.get_authorized_project(
        flask.g.session, repo, user=username, namespace=namespace
    )

    if not repo.settings.get("issue_tracker", True):
        response = flask.jsonify(
            {
                "code": "ERROR",
                "message": "No issue tracker found for this project",
            }
        )
        response.status_code = 404
        return response

    ticketrepopath = repo.repopath("tickets")
    content = None
    if os.path.exists(ticketrepopath):
        ticketrepo = pygit2.Repository(ticketrepopath)
        if not ticketrepo.is_empty and not ticketrepo.head_is_unborn:
            commit = ticketrepo[ticketrepo.head.target]
            # Get the asked template
            content_file = pagure.utils.__get_file_in_tree(
                ticketrepo,
                commit.tree,
                ["templates", "%s.md" % template],
                bail_on_tree=True,
            )
            if content_file:
                content, _ = pagure.doc_utils.convert_readme(
                    content_file.data, "md"
                )
    if content:
        response = flask.jsonify({"code": "OK", "message": content})
    else:
        response = flask.jsonify(
            {"code": "ERROR", "message": "No such template found"}
        )
        response.status_code = 404
    return response


@PV.route("/branches/commit/", methods=["POST"])
def get_branches_of_commit():
    """Return the list of branches that have the specified commit in"""
    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        response = flask.jsonify(
            {"code": "ERROR", "message": "Invalid input submitted"}
        )
        response.status_code = 400
        return response

    commit_id = flask.request.form.get("commit_id", "").strip() or None
    if not commit_id:
        response = flask.jsonify(
            {"code": "ERROR", "message": "No commit id submitted"}
        )
        response.status_code = 400
        return response

    repo = pagure.lib.query.get_authorized_project(
        flask.g.session,
        flask.request.form.get("repo", "").strip() or None,
        user=flask.request.form.get("repouser", "").strip() or None,
        namespace=flask.request.form.get("namespace", "").strip() or None,
    )

    if not repo:
        response = flask.jsonify(
            {
                "code": "ERROR",
                "message": "No repo found with the information provided",
            }
        )
        response.status_code = 404
        return response

    repopath = repo.repopath("main")

    if not os.path.exists(repopath):
        response = flask.jsonify(
            {
                "code": "ERROR",
                "message": "No git repo found with the information provided",
            }
        )
        response.status_code = 404
        return response

    repo_obj = pygit2.Repository(repopath)

    try:
        commit_id in repo_obj
    except ValueError:
        response = flask.jsonify(
            {
                "code": "ERROR",
                "message": "This commit could not be found in this repo",
            }
        )
        response.status_code = 404
        return response

    branches = []
    if not repo_obj.head_is_unborn:
        compare_branch = repo_obj.lookup_branch(repo_obj.head.shorthand)
    else:
        compare_branch = None

    for branchname in repo_obj.listall_branches():
        branch = repo_obj.lookup_branch(branchname)

        if not repo_obj.is_empty and len(repo_obj.listall_branches()) > 1:

            merge_commit = None

            if compare_branch:
                merge_commit_obj = repo_obj.merge_base(
                    compare_branch.peel().hex, branch.peel().hex
                )

                if merge_commit_obj:
                    merge_commit = merge_commit_obj.hex

            repo_commit = repo_obj[branch.peel().hex]

            for commit in repo_obj.walk(
                repo_commit.oid.hex, pygit2.GIT_SORT_NONE
            ):
                if commit.oid.hex == merge_commit:
                    break
                if commit.oid.hex == commit_id:
                    branches.append(branchname)
                    break

    # If we didn't find the commit in any branch and there is one, then it
    # is in the default branch.
    if not branches and compare_branch:
        branches.append(compare_branch.branch_name)

    return flask.jsonify({"code": "OK", "branches": branches})


@PV.route("/branches/heads/", methods=["POST"])
def get_branches_head():
    """Return the heads of each branch in the repo, using the following
    structure:
    {
        code: 'OK',
        branches: {
            name : commit,
            ...
        },
        heads: {
            commit : [branch, ...],
            ...
        }
    }
    """
    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        response = flask.jsonify(
            {"code": "ERROR", "message": "Invalid input submitted"}
        )
        response.status_code = 400
        return response

    repo = pagure.lib.query.get_authorized_project(
        flask.g.session,
        flask.request.form.get("repo", "").strip() or None,
        namespace=flask.request.form.get("namespace", "").strip() or None,
        user=flask.request.form.get("repouser", "").strip() or None,
    )

    if not repo:
        response = flask.jsonify(
            {
                "code": "ERROR",
                "message": "No repo found with the information provided",
            }
        )
        response.status_code = 404
        return response

    repopath = repo.repopath("main")

    if not os.path.exists(repopath):
        response = flask.jsonify(
            {
                "code": "ERROR",
                "message": "No git repo found with the information provided",
            }
        )
        response.status_code = 404
        return response

    repo_obj = pygit2.Repository(repopath)

    branches = {}
    if not repo_obj.is_empty and len(repo_obj.listall_branches()) > 1:
        for branchname in repo_obj.listall_branches():
            branch = repo_obj.lookup_branch(branchname)
            branches[branchname] = branch.peel().hex

    # invert the dict
    heads = collections.defaultdict(list)
    for branch, commit in branches.items():
        heads[commit].append(branch)

    return flask.jsonify({"code": "OK", "branches": branches, "heads": heads})


@PV.route("/task/<taskid>", methods=["GET"])
def task_info(taskid):
    """Return the results of the specified task or a 418 if the task is
    still being processed.
    """
    task = pagure.lib.tasks.get_result(taskid)

    if task.ready():
        result = task.get(timeout=0, propagate=False)
        if isinstance(result, Exception):
            result = "%s" % result
        return flask.jsonify({"results": result})
    else:
        flask.abort(418)


@PV.route("/stats/commits/authors", methods=["POST"])
def get_stats_commits():
    """Return statistics about the commits made on the specified repo."""
    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        response = flask.jsonify(
            {"code": "ERROR", "message": "Invalid input submitted"}
        )
        response.status_code = 400
        return response

    repo = pagure.lib.query.get_authorized_project(
        flask.g.session,
        flask.request.form.get("repo", "").strip() or None,
        namespace=flask.request.form.get("namespace", "").strip() or None,
        user=flask.request.form.get("repouser", "").strip() or None,
    )

    if not repo:
        response = flask.jsonify(
            {
                "code": "ERROR",
                "message": "No repo found with the information provided",
            }
        )
        response.status_code = 404
        return response

    repopath = repo.repopath("main")

    task = pagure.lib.tasks.commits_author_stats.delay(repopath)

    return flask.jsonify(
        {
            "code": "OK",
            "message": "Stats asked",
            "url": flask.url_for("internal_ns.task_info", taskid=task.id),
            "task_id": task.id,
        }
    )


@PV.route("/stats/commits/trend", methods=["POST"])
def get_stats_commits_trend():
    """Return evolution of the commits made on the specified repo."""
    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        response = flask.jsonify(
            {"code": "ERROR", "message": "Invalid input submitted"}
        )
        response.status_code = 400
        return response

    repo = pagure.lib.query.get_authorized_project(
        flask.g.session,
        flask.request.form.get("repo", "").strip() or None,
        namespace=flask.request.form.get("namespace", "").strip() or None,
        user=flask.request.form.get("repouser", "").strip() or None,
    )

    if not repo:
        response = flask.jsonify(
            {
                "code": "ERROR",
                "message": "No repo found with the information provided",
            }
        )
        response.status_code = 404
        return response

    repopath = repo.repopath("main")

    task = pagure.lib.tasks.commits_history_stats.delay(repopath)

    return flask.jsonify(
        {
            "code": "OK",
            "message": "Stats asked",
            "url": flask.url_for("internal_ns.task_info", taskid=task.id),
            "task_id": task.id,
        }
    )


@PV.route("/<repo>/family", methods=["POST"])
@PV.route("/<namespace>/<repo>/family", methods=["POST"])
@PV.route("/fork/<username>/<repo>/family", methods=["POST"])
@PV.route("/fork/<username>/<namespace>/<repo>/family", methods=["POST"])
def get_project_family(repo, namespace=None, username=None):
    """Return the family of projects for the specified project

    {
        code: 'OK',
        family: [
        ]
    }
    """

    allows_pr = flask.request.form.get("allows_pr", "").lower().strip() in [
        "1",
        "true",
    ]
    allows_issues = flask.request.form.get(
        "allows_issues", ""
    ).lower().strip() in ["1", "true"]

    form = pagure.forms.ConfirmationForm()
    if not form.validate_on_submit():
        response = flask.jsonify(
            {"code": "ERROR", "message": "Invalid input submitted"}
        )
        response.status_code = 400
        return response

    repo = pagure.lib.query.get_authorized_project(
        flask.g.session, repo, user=username, namespace=namespace
    )

    if not repo:
        response = flask.jsonify(
            {
                "code": "ERROR",
                "message": "No repo found with the information provided",
            }
        )
        response.status_code = 404
        return response

    if allows_pr:
        family = [
            p.url_path
            for p in pagure.lib.query.get_project_family(flask.g.session, repo)
            if p.settings.get("pull_requests", True)
        ]
    elif allows_issues:
        family = [
            p.url_path
            for p in pagure.lib.query.get_project_family(flask.g.session, repo)
            if p.settings.get("issue_tracker", True)
        ]
    else:
        family = [
            p.url_path
            for p in pagure.lib.query.get_project_family(flask.g.session, repo)
        ]

    return flask.jsonify({"code": "OK", "family": family})
