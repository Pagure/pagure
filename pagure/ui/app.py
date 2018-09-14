# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Farhaan Bukhsh <farhaan.bukhsh@gmail.com>

"""

from __future__ import unicode_literals

import datetime
import logging
from math import ceil

import flask
from sqlalchemy.exc import SQLAlchemyError

import pagure.exceptions
import pagure.lib
import pagure.lib.git
import pagure.forms
import pagure.ui.filters
from pagure.config import config as pagure_config
from pagure.flask_app import _get_user, admin_session_timedout
from pagure.ui import UI_NS
from pagure.utils import (
    authenticated,
    is_safe_url,
    login_required,
    get_task_redirect_url,
    is_true,
)


_log = logging.getLogger(__name__)


def _filter_acls(repos, acl, user):
    """ Filter the given list of repositories to return only the ones where
    the user has the specified acl.
    """
    if acl.lower() == "main admin":
        repos = [repo for repo in repos if user.username == repo.user.username]
    elif acl.lower() == "ticket" or "commit" or "admin":
        repos = [
            repo for repo in repos if user in repo.contributors[acl.lower()]
        ]

    return repos


@UI_NS.route("/browse/projects", endpoint="browse_projects")
@UI_NS.route("/browse/projects/", endpoint="browse_projects")
@UI_NS.route("/")
def index():
    """ Front page of the application.
    """
    if authenticated() and flask.request.path == "/":
        return flask.redirect(flask.url_for("ui_ns.userdash_projects"))

    sorting = flask.request.args.get("sorting") or None
    page = flask.request.args.get("page", 1)
    try:
        page = int(page)
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    limit = pagure_config["ITEM_PER_PAGE"]
    start = limit * (page - 1)

    private = None
    if authenticated():
        private = flask.g.fas_user.username

    repos = pagure.lib.search_projects(
        flask.g.session,
        fork=False,
        start=start,
        limit=limit,
        sort=sorting,
        private=private,
    )

    num_repos = pagure.lib.search_projects(
        flask.g.session, fork=False, private=private, count=True
    )
    total_page = int(ceil(num_repos / float(limit)) if num_repos > 0 else 1)

    return flask.render_template(
        "index.html",
        select="projects",
        repos=repos,
        repos_length=num_repos,
        total_page=total_page,
        page=page,
        sorting=sorting,
    )


def get_userdash_common(user):
    userdash_counts = {}

    userdash_counts["repos_length"] = pagure.lib.list_users_projects(
        flask.g.session,
        username=flask.g.fas_user.username,
        exclude_groups=None,
        fork=False,
        private=flask.g.fas_user.username,
        count=True,
    )

    userdash_counts["forks_length"] = pagure.lib.search_projects(
        flask.g.session,
        username=flask.g.fas_user.username,
        fork=True,
        private=flask.g.fas_user.username,
        count=True,
    )

    userdash_counts["watchlist_length"] = len(
        pagure.lib.user_watch_list(
            flask.g.session,
            user=flask.g.fas_user.username,
            exclude_groups=pagure_config.get("EXCLUDE_GROUP_INDEX"),
        )
    )

    userdash_counts["groups_length"] = len(user.groups)

    search_data = pagure.lib.list_users_projects(
        flask.g.session,
        username=flask.g.fas_user.username,
        private=flask.g.fas_user.username,
    )

    return userdash_counts, search_data


@UI_NS.route("/dashboard/projects/")
@UI_NS.route("/dashboard/projects")
@login_required
def userdash_projects():
    """ User Dashboard page listing projects for the user
    """
    user = _get_user(username=flask.g.fas_user.username)
    userdash_counts, search_data = get_userdash_common(user)

    groups = []

    for group in user.groups:
        groups.append(
            pagure.lib.search_groups(
                flask.g.session, group_name=group, group_type="user"
            )
        )

    acl = flask.request.args.get("acl", "").strip().lower() or None
    search_pattern = flask.request.args.get("search_pattern", None)
    if search_pattern == "":
        search_pattern = None

    limit = pagure_config["ITEM_PER_PAGE"]

    repopage = flask.request.args.get("repopage", 1)
    try:
        repopage = int(repopage)
        if repopage < 1:
            repopage = 1
    except ValueError:
        repopage = 1

    pattern = "*" + search_pattern + "*" if search_pattern else search_pattern

    start = limit * (repopage - 1)
    repos = pagure.lib.list_users_projects(
        flask.g.session,
        username=flask.g.fas_user.username,
        exclude_groups=None,
        fork=False,
        pattern=pattern,
        private=flask.g.fas_user.username,
        start=start,
        limit=limit,
        acls=[acl] if acl else None,
    )

    filtered_repos_count = pagure.lib.list_users_projects(
        flask.g.session,
        username=flask.g.fas_user.username,
        exclude_groups=None,
        fork=False,
        pattern=pattern,
        private=flask.g.fas_user.username,
        count=True,
        acls=[acl] if acl else None,
    )

    repo_list = []
    for repo in repos:
        access = ""
        if repo.user.user == user.username:
            access = "main admin"
        else:
            for repoaccess in repo.contributors:
                for repouser in repo.contributors[repoaccess]:
                    if repouser.username == user.username:
                        access = repoaccess
        grouplist = []
        for group in groups:
            if repo in group.projects:
                thegroup = {"group_name": "", "access": ""}
                thegroup["group_name"] = group.group_name
                for a in repo.contributor_groups:
                    for gr in repo.contributor_groups[a]:
                        if group.group_name == gr.group_name:
                            thegroup["access"] = a
                grouplist.append(thegroup)
        repo_list.append(
            {"repo": repo, "grouplist": grouplist, "access": access}
        )

    total_repo_page = int(
        ceil(filtered_repos_count / float(limit))
        if filtered_repos_count > 0
        else 1
    )

    return flask.render_template(
        "userdash_projects.html",
        username=flask.g.fas_user.username,
        user=user,
        select="projects",
        repo_list=repo_list,
        repopage=repopage,
        total_repo_page=total_repo_page,
        userdash_counts=userdash_counts,
        search_data=search_data,
        acl=acl,
        filtered_repos_count=filtered_repos_count,
        search_pattern=search_pattern,
    )


@UI_NS.route("/dashboard/activity/")
@UI_NS.route("/dashboard/activity")
@login_required
def userdash_activity():
    """ User Dashboard page listing user activity
    """
    user = _get_user(username=flask.g.fas_user.username)
    userdash_counts, search_data = get_userdash_common(user)

    messages = pagure.lib.get_watchlist_messages(
        flask.g.session, user, limit=20
    )

    return flask.render_template(
        "userdash_activity.html",
        username=flask.g.fas_user.username,
        user=user,
        select="activity",
        messages=messages,
        userdash_counts=userdash_counts,
        search_data=search_data,
    )


@UI_NS.route("/dashboard/groups/")
@UI_NS.route("/dashboard/groups")
@login_required
def userdash_groups():
    """ User Dashboard page listing a user's groups
    """
    user = _get_user(username=flask.g.fas_user.username)
    userdash_counts, search_data = get_userdash_common(user)

    groups = []

    for group in user.groups:
        groups.append(
            pagure.lib.search_groups(
                flask.g.session, group_name=group, group_type="user"
            )
        )

    return flask.render_template(
        "userdash_groups.html",
        username=flask.g.fas_user.username,
        user=user,
        select="groups",
        groups=groups,
        userdash_counts=userdash_counts,
        search_data=search_data,
    )


@UI_NS.route("/dashboard/forks/")
@UI_NS.route("/dashboard/forks")
@login_required
def userdash_forks():
    """ Forks tab of the user dashboard
    """
    user = _get_user(username=flask.g.fas_user.username)
    userdash_counts, search_data = get_userdash_common(user)

    limit = pagure_config["ITEM_PER_PAGE"]

    # FORKS
    forkpage = flask.request.args.get("forkpage", 1)
    try:
        forkpage = int(forkpage)
        if forkpage < 1:
            forkpage = 1
    except ValueError:
        forkpage = 1

    start = limit * (forkpage - 1)
    forks = pagure.lib.search_projects(
        flask.g.session,
        username=flask.g.fas_user.username,
        fork=True,
        private=flask.g.fas_user.username,
        start=start,
        limit=limit,
    )

    total_fork_page = int(
        ceil(userdash_counts["forks_length"] / float(limit))
        if userdash_counts["forks_length"] > 0
        else 1
    )

    return flask.render_template(
        "userdash_forks.html",
        username=flask.g.fas_user.username,
        user=user,
        select="forks",
        forks=forks,
        forkpage=forkpage,
        total_fork_page=total_fork_page,
        userdash_counts=userdash_counts,
        search_data=search_data,
    )


@UI_NS.route("/dashboard/watchlist/")
@UI_NS.route("/dashboard/watchlist")
@login_required
def userdash_watchlist():
    """ User Dashboard page for a user's watchlist
    """

    watch_list = pagure.lib.user_watch_list(
        flask.g.session,
        user=flask.g.fas_user.username,
        exclude_groups=pagure_config.get("EXCLUDE_GROUP_INDEX"),
    )

    user = _get_user(username=flask.g.fas_user.username)
    userdash_counts, search_data = get_userdash_common(user)

    return flask.render_template(
        "userdash_watchlist.html",
        username=flask.g.fas_user.username,
        user=user,
        select="watchlist",
        watch_list=watch_list,
        userdash_counts=userdash_counts,
        search_data=search_data,
    )


def index_auth():
    """ Front page for authenticated user.
    """
    user = _get_user(username=flask.g.fas_user.username)

    acl = flask.request.args.get("acl", "").strip().lower() or None

    repopage = flask.request.args.get("repopage", 1)
    try:
        repopage = int(repopage)
        if repopage < 1:
            repopage = 1
    except ValueError:
        repopage = 1

    limit = pagure_config["ITEM_PER_PAGE"]

    # PROJECTS
    start = limit * (repopage - 1)
    repos = pagure.lib.search_projects(
        flask.g.session,
        username=flask.g.fas_user.username,
        exclude_groups=pagure_config.get("EXCLUDE_GROUP_INDEX"),
        fork=False,
        private=flask.g.fas_user.username,
        start=start,
        limit=limit,
    )
    if repos and acl:
        repos = _filter_acls(repos, acl, user)

    repos_length = pagure.lib.search_projects(
        flask.g.session,
        username=flask.g.fas_user.username,
        exclude_groups=pagure_config.get("EXCLUDE_GROUP_INDEX"),
        fork=False,
        private=flask.g.fas_user.username,
        count=True,
    )
    total_repo_page = int(
        ceil(repos_length / float(limit)) if repos_length > 0 else 1
    )

    # FORKS
    forkpage = flask.request.args.get("forkpage", 1)
    try:
        forkpage = int(forkpage)
        if forkpage < 1:
            forkpage = 1
    except ValueError:
        forkpage = 1

    start = limit * (forkpage - 1)
    forks = pagure.lib.search_projects(
        flask.g.session,
        username=flask.g.fas_user.username,
        fork=True,
        private=flask.g.fas_user.username,
        start=start,
        limit=limit,
    )

    forks_length = pagure.lib.search_projects(
        flask.g.session,
        username=flask.g.fas_user.username,
        fork=True,
        private=flask.g.fas_user.username,
        start=start,
        limit=limit,
        count=True,
    )
    total_fork_page = int(
        ceil(forks_length / float(limit)) if forks_length > 0 else 1
    )

    watch_list = pagure.lib.user_watch_list(
        flask.g.session,
        user=flask.g.fas_user.username,
        exclude_groups=pagure_config.get("EXCLUDE_GROUP_INDEX"),
    )

    return flask.render_template(
        "userdash_projects.html",
        username=flask.g.fas_user.username,
        user=user,
        forks=forks,
        repos=repos,
        watch_list=watch_list,
        repopage=repopage,
        repos_length=repos_length,
        total_repo_page=total_repo_page,
        forkpage=forkpage,
        forks_length=forks_length,
        total_fork_page=total_fork_page,
    )


@UI_NS.route("/search/")
@UI_NS.route("/search")
def search():
    """ Search this pagure instance for projects or users.
    """
    stype = flask.request.args.get("type", "projects")
    term = flask.request.args.get("term")
    page = flask.request.args.get("page", 1)
    direct = is_true(flask.request.values.get("direct", False))

    try:
        page = int(page)
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    if direct:
        return flask.redirect(flask.url_for("ui_ns.view_repo", repo="") + term)

    if stype == "projects":
        return flask.redirect(
            flask.url_for("ui_ns.view_projects", pattern=term)
        )
    elif stype == "projects_forks":
        return flask.redirect(
            flask.url_for("view_projects", pattern=term, forks=True)
        )
    elif stype == "groups":
        return flask.redirect(flask.url_for("ui_ns.view_group", group=term))
    else:
        return flask.redirect(flask.url_for("ui_ns.view_users", username=term))


@UI_NS.route("/users/")
@UI_NS.route("/users")
@UI_NS.route("/users/<username>")
def view_users(username=None):
    """ Present the list of users.
    """
    page = flask.request.args.get("page", 1)
    try:
        page = int(page)
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    users = pagure.lib.search_user(flask.g.session, pattern=username)

    private = False
    # Condition to check non-authorized user should't be able to access private
    # project of other users
    if authenticated() and username == flask.g.fas_user.username:
        private = flask.g.fas_user.username

    limit = pagure_config["ITEM_PER_PAGE"]
    start = limit * (page - 1)
    end = limit * page
    users_length = len(users)
    users = users[start:end]

    total_page = int(ceil(users_length / float(limit)))

    for user in users:
        repos_length = pagure.lib.search_projects(
            flask.g.session,
            username=user.user,
            fork=False,
            count=True,
            private=private,
        )

        forks_length = pagure.lib.search_projects(
            flask.g.session,
            username=user.user,
            fork=True,
            count=True,
            private=private,
        )
        user.repos_length = repos_length
        user.forks_length = forks_length

    return flask.render_template(
        "user_list.html",
        users=users,
        users_length=users_length,
        total_page=total_page,
        page=page,
        select="users",
    )


@UI_NS.route("/projects/")
@UI_NS.route("/projects")
@UI_NS.route("/projects/<pattern>")
@UI_NS.route("/projects/<namespace>/<pattern>")
def view_projects(pattern=None, namespace=None):
    """ Present the list of projects.
    """
    forks = flask.request.args.get("forks")
    page = flask.request.args.get("page", 1)

    try:
        page = int(page)
        if page < 1:
            page = 1
    except ValueError:
        page = 1

    select = "projects"
    # If forks is specified, we want both forks and projects
    if is_true(forks):
        forks = None
        select = "projects_forks"
    else:
        forks = False
    private = False

    if authenticated():
        private = flask.g.fas_user.username

    limit = pagure_config["ITEM_PER_PAGE"]
    start = limit * (page - 1)

    projects = pagure.lib.search_projects(
        flask.g.session,
        pattern=pattern,
        namespace=namespace,
        fork=forks,
        start=start,
        limit=limit,
        private=private,
    )

    if len(projects) == 1:
        flask.flash("Only one result found, redirecting you to it")
        return flask.redirect(
            flask.url_for(
                "ui_ns.view_repo",
                repo=projects[0].name,
                namespace=projects[0].namespace,
                username=projects[0].user.username
                if projects[0].is_fork
                else None,
            )
        )

    projects_length = pagure.lib.search_projects(
        flask.g.session,
        pattern=pattern,
        namespace=namespace,
        fork=forks,
        count=True,
        private=private,
    )

    total_page = int(ceil(projects_length / float(limit)))

    return flask.render_template(
        "index.html",
        repos=projects,
        repos_length=projects_length,
        total_page=total_page,
        page=page,
        select=select,
    )


def get_userprofile_common(user):
    userprofile_counts = {}

    userprofile_counts["repos_length"] = pagure.lib.search_projects(
        flask.g.session,
        username=user.username,
        fork=False,
        exclude_groups=None,
        private=False,
        count=True,
    )

    userprofile_counts["forks_length"] = pagure.lib.search_projects(
        flask.g.session,
        username=user.username,
        fork=True,
        private=False,
        count=True,
    )

    return userprofile_counts


@UI_NS.route("/user/<username>/")
@UI_NS.route("/user/<username>")
def view_user(username):
    """ Front page of a specific user.
    """
    user = _get_user(username=username)

    # public profile, so never show private repos,
    # even if the user is viewing themself
    private = False

    owned_repos = pagure.lib.list_users_projects(
        flask.g.session,
        username=username,
        exclude_groups=None,
        fork=False,
        private=private,
        limit=6,
        acls=["main admin"],
    )

    userprofile_common = get_userprofile_common(user)

    return flask.render_template(
        "userprofile_overview.html",
        username=username,
        user=user,
        owned_repos=owned_repos,
        repos_length=userprofile_common["repos_length"],
        forks_length=userprofile_common["forks_length"],
        select="overview",
    )


@UI_NS.route("/user/<username>/projects/")
@UI_NS.route("/user/<username>/projects")
def userprofile_projects(username):
    """ Public Profile view of a user's projects.
    """
    user = _get_user(username=username)

    repopage = flask.request.args.get("repopage", 1)
    try:
        repopage = int(repopage)
        if repopage < 1:
            repopage = 1
    except ValueError:
        repopage = 1

    limit = pagure_config["ITEM_PER_PAGE"]
    repo_start = limit * (repopage - 1)

    repos = pagure.lib.search_projects(
        flask.g.session,
        username=username,
        fork=False,
        exclude_groups=pagure_config.get("EXCLUDE_GROUP_INDEX"),
        start=repo_start,
        limit=limit,
        private=False,
    )

    userprofile_common = get_userprofile_common(user)
    total_page_repos = int(
        ceil(userprofile_common["repos_length"] / float(limit))
    )

    return flask.render_template(
        "userprofile_projects.html",
        username=username,
        user=user,
        repos=repos,
        total_page_repos=total_page_repos,
        repopage=repopage,
        repos_length=userprofile_common["repos_length"],
        forks_length=userprofile_common["forks_length"],
        select="projects",
    )


@UI_NS.route("/user/<username>/forks/")
@UI_NS.route("/user/<username>/forks")
def userprofile_forks(username):
    """ Public Profile view of a user's forks.
    """
    user = _get_user(username=username)

    forkpage = flask.request.args.get("forkpage", 1)
    try:
        forkpage = int(forkpage)
        if forkpage < 1:
            forkpage = 1
    except ValueError:
        forkpage = 1

    limit = pagure_config["ITEM_PER_PAGE"]
    fork_start = limit * (forkpage - 1)

    forks = pagure.lib.search_projects(
        flask.g.session,
        username=username,
        fork=True,
        start=fork_start,
        limit=limit,
        private=False,
    )

    userprofile_common = get_userprofile_common(user)
    total_page_forks = int(
        ceil(userprofile_common["forks_length"] / float(limit))
    )

    return flask.render_template(
        "userprofile_forks.html",
        username=username,
        user=user,
        forks=forks,
        total_page_forks=total_page_forks,
        forkpage=forkpage,
        repos_length=userprofile_common["repos_length"],
        forks_length=userprofile_common["forks_length"],
        select="forks",
    )


# original view_user()
@UI_NS.route("/user2/<username>/")
@UI_NS.route("/user2/<username>")
def view_user2(username):
    """ Front page of a specific user.
    """
    user = _get_user(username=username)

    acl = flask.request.args.get("acl", "").strip().lower() or None

    repopage = flask.request.args.get("repopage", 1)
    try:
        repopage = int(repopage)
        if repopage < 1:
            repopage = 1
    except ValueError:
        repopage = 1

    forkpage = flask.request.args.get("forkpage", 1)
    try:
        forkpage = int(forkpage)
        if forkpage < 1:
            forkpage = 1
    except ValueError:
        forkpage = 1

    limit = pagure_config["ITEM_PER_PAGE"]
    repo_start = limit * (repopage - 1)
    fork_start = limit * (forkpage - 1)

    private = False
    if authenticated() and username == flask.g.fas_user.username:
        private = flask.g.fas_user.username

    repos = pagure.lib.search_projects(
        flask.g.session,
        username=username,
        fork=False,
        exclude_groups=pagure_config.get("EXCLUDE_GROUP_INDEX"),
        start=repo_start,
        limit=limit,
        private=private,
    )

    if repos and acl:
        repos = _filter_acls(repos, acl, user)

    repos_length = pagure.lib.search_projects(
        flask.g.session,
        username=username,
        fork=False,
        exclude_groups=pagure_config.get("EXCLUDE_GROUP_INDEX"),
        private=private,
        count=True,
    )

    forks = pagure.lib.search_projects(
        flask.g.session,
        username=username,
        fork=True,
        start=fork_start,
        limit=limit,
        private=private,
    )

    forks_length = pagure.lib.search_projects(
        flask.g.session,
        username=username,
        fork=True,
        private=private,
        count=True,
    )

    total_page_repos = int(ceil(repos_length / float(limit)))
    total_page_forks = int(ceil(forks_length / float(limit)))

    return flask.render_template(
        "userprofile_overview.html",
        username=username,
        user=user,
        repos=repos,
        total_page_repos=total_page_repos,
        forks=forks,
        total_page_forks=total_page_forks,
        repopage=repopage,
        forkpage=forkpage,
        repos_length=repos_length,
        forks_length=forks_length,
    )


@UI_NS.route("/user/<username>/requests/")
@UI_NS.route("/user/<username>/requests")
def view_user_requests(username):
    """ Shows the pull-requests for the specified user.
    """
    user = _get_user(username=username)

    requests = pagure.lib.get_pull_request_of_user(
        flask.g.session, username=username
    )

    userprofile_common = get_userprofile_common(user)

    return flask.render_template(
        "userprofile_pullrequests.html",
        username=username,
        user=user,
        requests=requests,
        select="requests",
        repos_length=userprofile_common["repos_length"],
        forks_length=userprofile_common["forks_length"],
    )


@UI_NS.route("/user/<username>/issues/")
@UI_NS.route("/user/<username>/issues")
def view_user_issues(username):
    """
    Shows the issues created or assigned to the specified user.

    :param username: The username to retrieve the issues for
    :type  username: str
    """

    if not pagure_config.get("ENABLE_TICKETS", True):
        flask.abort(404, "Tickets have been disabled on this pagure instance")

    user = _get_user(username=username)
    userprofile_common = get_userprofile_common(user)

    return flask.render_template(
        "userprofile_issues.html",
        username=username,
        user=user,
        repos_length=userprofile_common["repos_length"],
        forks_length=userprofile_common["forks_length"],
        select="issues",
    )


@UI_NS.route("/user/<username>/stars/")
@UI_NS.route("/user/<username>/stars")
def userprofile_starred(username):
    """
    Shows the starred projects of the specified user.

    :arg username: The username whose stars we have to retrieve
    """

    user = _get_user(username=username)
    userprofile_common = get_userprofile_common(user)

    return flask.render_template(
        "userprofile_starred.html",
        username=username,
        user=user,
        repos=[star.project for star in user.stars],
        repos_length=userprofile_common["repos_length"],
        forks_length=userprofile_common["forks_length"],
        select="starred",
    )


@UI_NS.route("/user/<username>/groups/")
@UI_NS.route("/user/<username>/groups")
def userprofile_groups(username):
    """
    Shows the groups of a user
    """

    user = _get_user(username=username)
    userprofile_common = get_userprofile_common(user)

    groups = []
    for groupname in user.groups:
        groups.append(
            pagure.lib.search_groups(flask.g.session, group_name=groupname)
        )

    return flask.render_template(
        "userprofile_groups.html",
        username=username,
        user=user,
        groups=groups,
        repos_length=userprofile_common["repos_length"],
        forks_length=userprofile_common["forks_length"],
        select="groups",
    )


@UI_NS.route("/new/", methods=("GET", "POST"))
@UI_NS.route("/new", methods=("GET", "POST"))
@login_required
def new_project():
    """ Form to create a new project.
    """
    user = pagure.lib.search_user(
        flask.g.session, username=flask.g.fas_user.username
    )

    if not pagure_config.get(
        "ENABLE_NEW_PROJECTS", True
    ) or not pagure_config.get("ENABLE_UI_NEW_PROJECTS", True):
        flask.abort(
            404,
            "Creation of new project is not allowed on this \
                pagure instance",
        )

    namespaces = pagure_config["ALLOWED_PREFIX"][:]
    if user:
        namespaces.extend([grp for grp in user.groups])
    if pagure_config.get("USER_NAMESPACE", False):
        namespaces.insert(0, flask.g.fas_user.username)

    form = pagure.forms.ProjectForm(namespaces=namespaces)

    if form.validate_on_submit():
        name = form.name.data
        description = form.description.data
        url = form.url.data
        avatar_email = form.avatar_email.data
        create_readme = form.create_readme.data
        private = False
        if pagure_config.get("PRIVATE_PROJECTS", False):
            private = form.private.data
        namespace = form.namespace.data
        if namespace:
            namespace = namespace.strip()
        if form.repospanner_region:
            repospanner_region = form.repospanner_region.data
        else:
            repospanner_region = None

        try:
            task = pagure.lib.new_project(
                flask.g.session,
                name=name,
                private=private,
                description=description,
                namespace=namespace,
                repospanner_region=repospanner_region,
                url=url,
                avatar_email=avatar_email,
                user=flask.g.fas_user.username,
                blacklist=pagure_config["BLACKLISTED_PROJECTS"],
                allowed_prefix=pagure_config["ALLOWED_PREFIX"],
                add_readme=create_readme,
                userobj=user,
                prevent_40_chars=pagure_config.get(
                    "OLD_VIEW_COMMIT_ENABLED", False
                ),
                user_ns=pagure_config.get("USER_NAMESPACE", False),
            )
            flask.g.session.commit()
            return pagure.utils.wait_for_task(task)
        except pagure.exceptions.PagureException as err:
            flask.flash(str(err), "error")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(str(err), "error")

    return flask.render_template("new_project.html", form=form)


@UI_NS.route("/wait/<taskid>")
def wait_task(taskid):
    """ Shows a wait page until the task finishes. """
    task = pagure.lib.tasks.get_result(taskid)

    is_js = is_true(flask.request.args.get("js"))

    prev = flask.request.args.get("prev")
    if not is_safe_url(prev):
        prev = flask.url_for("index")

    count = flask.request.args.get("count", 0)
    try:
        count = int(count)
        if count < 1:
            count = 0
    except ValueError:
        count = 0

    if task.ready():
        if is_js:
            flask.abort(417)
        return flask.redirect(get_task_redirect_url(task, prev))
    else:
        if is_js:
            return flask.jsonify({"count": count + 1, "status": task.status})

        return flask.render_template(
            "waiting.html", task=task, count=count, prev=prev
        )


@UI_NS.route("/settings/", methods=("GET", "POST"))
@UI_NS.route("/settings", methods=("GET", "POST"))
@login_required
def user_settings():
    """ Update the user settings.
    """
    if admin_session_timedout():
        return flask.redirect(
            flask.url_for("auth_login", next=flask.request.url)
        )

    user = _get_user(username=flask.g.fas_user.username)

    form = pagure.forms.UserSettingsForm()
    if form.validate_on_submit() and pagure_config.get("LOCAL_SSH_KEY", True):
        ssh_key = form.ssh_key.data

        try:
            message = "Nothing to update"
            if user.public_ssh_key != ssh_key:
                pagure.lib.update_user_ssh(
                    flask.g.session,
                    user=user,
                    ssh_key=ssh_key,
                    keydir=pagure_config.get("GITOLITE_KEYDIR", None),
                    update_only=True,
                )
                flask.g.session.commit()
                message = "Public ssh key updated"
            flask.flash(message)
            return flask.redirect(flask.url_for("ui_ns.user_settings"))
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(str(err), "error")
    elif flask.request.method == "GET":
        form.ssh_key.data = user.public_ssh_key

    return flask.render_template("user_settings.html", user=user, form=form)


@UI_NS.route("/settings/usersettings", methods=["POST"])
@login_required
def update_user_settings():
    """ Update the user's settings set in the settings page.
    """
    if admin_session_timedout():
        if flask.request.method == "POST":
            flask.flash("Action canceled, try it again", "error")
        return flask.redirect(
            flask.url_for("auth_login", next=flask.request.url)
        )

    user = _get_user(username=flask.g.fas_user.username)

    form = pagure.forms.ConfirmationForm()

    if form.validate_on_submit():
        settings = {}
        for key in flask.request.form:
            if key == "csrf_token":
                continue
            settings[key] = flask.request.form[key]

        try:
            message = pagure.lib.update_user_settings(
                flask.g.session, settings=settings, user=user.username
            )
            flask.g.session.commit()
            flask.flash(message)
        except pagure.exceptions.PagureException as msg:
            flask.g.session.rollback()
            flask.flash(msg, "error")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(str(err), "error")

    return flask.redirect(flask.url_for("ui_ns.user_settings"))


@UI_NS.route("/markdown/", methods=["POST"])
def markdown_preview():
    """ Return the provided markdown text in html.

    The text has to be provided via the parameter 'content' of a POST query.
    """
    form = pagure.forms.ConfirmationForm()
    if form.validate_on_submit():
        return pagure.ui.filters.markdown_filter(flask.request.form["content"])
    else:
        flask.abort(400, "Invalid request")


@UI_NS.route("/settings/email/drop", methods=["POST"])
@login_required
def remove_user_email():
    """ Remove the specified email from the logged in user.
    """
    if admin_session_timedout():
        return flask.redirect(
            flask.url_for("auth_login", next=flask.request.url)
        )

    user = _get_user(username=flask.g.fas_user.username)

    if len(user.emails) == 1:
        flask.flash("You must always have at least one email", "error")
        return flask.redirect(flask.url_for("ui_ns.user_settings"))

    form = pagure.forms.UserEmailForm()

    if form.validate_on_submit():
        email = form.email.data
        useremails = [mail.email for mail in user.emails]

        if email not in useremails:
            flask.flash(
                "You do not have the email: %s, nothing to remove" % email,
                "error",
            )
            return flask.redirect(flask.url_for("ui_ns.user_settings"))

        for mail in user.emails:
            if mail.email == email:
                user.emails.remove(mail)
                break
        try:
            flask.g.session.commit()
            flask.flash("Email removed")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("Email could not be removed", "error")

    return flask.redirect(flask.url_for("ui_ns.user_settings"))


@UI_NS.route("/settings/email/add/", methods=["GET", "POST"])
@UI_NS.route("/settings/email/add", methods=["GET", "POST"])
@login_required
def add_user_email():
    """ Add a new email for the logged in user.
    """
    if admin_session_timedout():
        return flask.redirect(
            flask.url_for("auth_login", next=flask.request.url)
        )

    user = _get_user(username=flask.g.fas_user.username)

    form = pagure.forms.UserEmailForm(
        emails=[mail.email for mail in user.emails]
    )
    if form.validate_on_submit():
        email = form.email.data

        try:
            pagure.lib.add_user_pending_email(flask.g.session, user, email)
            flask.g.session.commit()
            flask.flash("Email pending validation")
            return flask.redirect(flask.url_for("ui_ns.user_settings"))
        except pagure.exceptions.PagureException as err:
            flask.flash(str(err), "error")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("Email could not be added", "error")

    return flask.render_template("user_emails.html", user=user, form=form)


@UI_NS.route("/settings/email/default", methods=["POST"])
@login_required
def set_default_email():
    """ Set the default email address of the user.
    """
    if admin_session_timedout():
        return flask.redirect(
            flask.url_for("auth_login", next=flask.request.url)
        )

    user = _get_user(username=flask.g.fas_user.username)

    form = pagure.forms.UserEmailForm()
    if form.validate_on_submit():
        email = form.email.data
        useremails = [mail.email for mail in user.emails]

        if email not in useremails:
            flask.flash(
                "You do not have the email: %s, nothing to set" % email,
                "error",
            )

            return flask.redirect(flask.url_for("ui_ns.user_settings"))

        user.default_email = email

        try:
            flask.g.session.commit()
            flask.flash("Default email set to: %s" % email)
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("Default email could not be set", "error")

    return flask.redirect(flask.url_for("ui_ns.user_settings"))


@UI_NS.route("/settings/email/resend", methods=["POST"])
@login_required
def reconfirm_email():
    """ Re-send the email address of the user.
    """
    if admin_session_timedout():
        return flask.redirect(
            flask.url_for("auth_login", next=flask.request.url)
        )

    user = _get_user(username=flask.g.fas_user.username)

    form = pagure.forms.UserEmailForm()
    if form.validate_on_submit():
        email = form.email.data

        try:
            pagure.lib.resend_pending_email(flask.g.session, user, email)
            flask.g.session.commit()
            flask.flash("Confirmation email re-sent")
        except pagure.exceptions.PagureException as err:
            flask.flash(str(err), "error")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("Confirmation email could not be re-sent", "error")

    return flask.redirect(flask.url_for("ui_ns.user_settings"))


@UI_NS.route("/settings/email/confirm/<token>/")
@UI_NS.route("/settings/email/confirm/<token>")
def confirm_email(token):
    """ Confirm a new email.
    """
    if admin_session_timedout():
        return flask.redirect(
            flask.url_for("auth_login", next=flask.request.url)
        )

    email = pagure.lib.search_pending_email(flask.g.session, token=token)
    if not email:
        flask.flash("No email associated with this token.", "error")
    else:
        try:
            pagure.lib.add_email_to_user(
                flask.g.session, email.user, email.email
            )
            flask.g.session.delete(email)
            flask.g.session.commit()
            flask.flash("Email validated")
        except pagure.exceptions.PagureException as err:
            flask.flash(str(err), "error")
            _log.exception(err)
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            flask.flash(
                "Could not set the account as active in the db, "
                "please report this error to an admin",
                "error",
            )
            _log.exception(err)

    return flask.redirect(flask.url_for("ui_ns.user_settings"))


@UI_NS.route("/ssh_info/")
@UI_NS.route("/ssh_info")
def ssh_hostkey():
    """ Endpoint returning information about the SSH hostkey and fingerprint
    of the current pagure instance.
    """
    return flask.render_template("doc_ssh_keys.html")


@UI_NS.route("/settings/token/new/", methods=("GET", "POST"))
@UI_NS.route("/settings/token/new", methods=("GET", "POST"))
@login_required
def add_api_user_token():
    """ Create an user token (not project specific).
    """
    if admin_session_timedout():
        if flask.request.method == "POST":
            flask.flash("Action canceled, try it again", "error")
        return flask.redirect(
            flask.url_for("auth_login", next=flask.request.url)
        )

    # Ensure the user is in the DB at least
    user = _get_user(username=flask.g.fas_user.username)

    acls = pagure.lib.get_acls(
        flask.g.session, restrict=pagure_config.get("CROSS_PROJECT_ACLS")
    )
    form = pagure.forms.NewTokenForm(acls=acls)

    if form.validate_on_submit():
        try:
            msg = pagure.lib.add_token_to_user(
                flask.g.session,
                project=None,
                description=form.description.data.strip() or None,
                acls=form.acls.data,
                username=user.username,
            )
            flask.g.session.commit()
            flask.flash(msg)
            return flask.redirect(
                flask.url_for("ui_ns.user_settings") + "#nav-api-tab"
            )
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash("API key could not be added", "error")

    # When form is displayed after an empty submission, show an error.
    if form.errors.get("acls"):
        flask.flash("You must select at least one permission.", "error")

    return flask.render_template(
        "add_token.html", select="settings", form=form, acls=acls
    )


@UI_NS.route("/settings/token/revoke/<token_id>/", methods=["POST"])
@UI_NS.route("/settings/token/revoke/<token_id>", methods=["POST"])
@login_required
def revoke_api_user_token(token_id):
    """ Revoke a user token (ie: not project specific).
    """
    if admin_session_timedout():
        flask.flash("Action canceled, try it again", "error")
        url = flask.url_for(".user_settings")
        return flask.redirect(flask.url_for("auth_login", next=url))

    token = pagure.lib.get_api_token(flask.g.session, token_id)

    if not token or token.user.username != flask.g.fas_user.username:
        flask.abort(404, "Token not found")

    form = pagure.forms.ConfirmationForm()

    if form.validate_on_submit():
        try:
            if token.expiration >= datetime.datetime.utcnow():
                token.expiration = datetime.datetime.utcnow()
                flask.g.session.add(token)
            flask.g.session.commit()
            flask.flash("Token revoked")
        except SQLAlchemyError as err:  # pragma: no cover
            flask.g.session.rollback()
            _log.exception(err)
            flask.flash(
                "Token could not be revoked, please contact an admin", "error"
            )

    return flask.redirect(
        flask.url_for("ui_ns.user_settings") + "#nav-api-token"
    )


@UI_NS.route("/settings/forcelogout/", methods=("POST",))
@UI_NS.route("/settings/forcelogout", methods=("POST",))
@login_required
def force_logout():
    """ Set refuse_sessions_before, logging the user out everywhere
    """
    if admin_session_timedout():
        flask.flash("Action canceled, try it again", "error")
        return flask.redirect(
            flask.url_for("auth_login", next=flask.request.url)
        )

    # we just need an empty form here to validate that csrf token is present
    form = pagure.forms.PagureForm()
    if form.validate_on_submit():
        # Ensure the user is in the DB at least
        user = _get_user(username=flask.g.fas_user.username)

        user.refuse_sessions_before = datetime.datetime.utcnow()
        flask.g.session.commit()
        flask.flash("All active sessions logged out")
    return flask.redirect(flask.url_for("ui_ns.user_settings"))
