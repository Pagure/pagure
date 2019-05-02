# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import arrow
import datetime
import collections
import logging
import json
import operator
import re
import pygit2
import os

import six
import sqlalchemy as sa

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import backref
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import relation
from sqlalchemy.orm import validates

import pagure.exceptions
from pagure.config import config as pagure_config
from pagure.lib.model_base import BASE
from pagure.lib.plugins import get_plugin_tables
from pagure.utils import is_true


_log = logging.getLogger(__name__)

# hit w/ all the id field we use
# pylint: disable=invalid-name
# pylint: disable=too-few-public-methods
# pylint: disable=no-init
# pylint: disable=too-many-lines


def create_tables(db_url, alembic_ini=None, acls=None, debug=False):
    """ Create the tables in the database using the information from the
    url obtained.

    :arg db_url, URL used to connect to the database. The URL contains
        information with regards to the database engine, the host to
        connect to, the user and password and the database name.
          ie: <engine>://<user>:<password>@<host>/<dbname>
    :kwarg alembic_ini, path to the alembic ini file. This is necessary
        to be able to use alembic correctly, but not for the unit-tests.
    :kwarg debug, a boolean specifying whether we should have the verbose
        output of sqlalchemy or not.
    :return a session that can be used to query the database.

    """
    if db_url.startswith("postgres"):  # pragma: no cover
        engine = create_engine(db_url, echo=debug, client_encoding="utf8")
    else:  # pragma: no cover
        engine = create_engine(db_url, echo=debug)

    get_plugin_tables()
    BASE.metadata.create_all(engine)
    # engine.execute(collection_package_create_view(driver=engine.driver))
    if db_url.startswith("sqlite:"):
        # Ignore the warning about con_record
        # pylint: disable=unused-argument
        def _fk_pragma_on_connect(dbapi_con, _):  # pragma: no cover
            """ Tries to enforce referential constraints on sqlite. """
            dbapi_con.execute("pragma foreign_keys=ON")

        sa.event.listen(engine, "connect", _fk_pragma_on_connect)

    if alembic_ini is not None:  # pragma: no cover
        # then, load the Alembic configuration and generate the
        # version table, "stamping" it with the most recent rev:

        # Ignore the warning missing alembic
        # pylint: disable=import-error
        from alembic.config import Config
        from alembic import command

        alembic_cfg = Config(alembic_ini)
        command.stamp(alembic_cfg, "head")

    scopedsession = scoped_session(sessionmaker(bind=engine))
    BASE.metadata.bind = scopedsession
    # Insert the default data into the db
    create_default_status(scopedsession, acls=acls)
    return scopedsession


def create_default_status(session, acls=None):
    """ Insert the defaults status in the status tables.
    """

    statuses = ["Open", "Closed"]
    for status in statuses:
        ticket_stat = StatusIssue(status=status)
        session.add(ticket_stat)
        try:
            session.commit()
        except SQLAlchemyError:  # pragma: no cover
            session.rollback()
            _log.debug("Status %s could not be added", ticket_stat)

    for status in ["Open", "Closed", "Merged"]:
        pr_stat = StatusPullRequest(status=status)
        session.add(pr_stat)
        try:
            session.commit()
        except SQLAlchemyError:  # pragma: no cover
            session.rollback()
            _log.debug("Status %s could not be added", pr_stat)

    for grptype in ["user", "admin"]:
        grp_type = PagureGroupType(group_type=grptype)
        session.add(grp_type)
        try:
            session.commit()
        except SQLAlchemyError:  # pragma: no cover
            session.rollback()
            _log.debug("Type %s could not be added", grptype)

    acls = acls or {}
    keys = sorted(list(acls.keys()))
    for acl in keys:
        item = ACL(name=acl, description=acls[acl])
        session.add(item)
        try:
            session.commit()
        except SQLAlchemyError:  # pragma: no cover
            session.rollback()
            _log.debug("ACL %s could not be added", acl)

    for access in ["ticket", "commit", "admin"]:
        access_obj = AccessLevels(access=access)
        session.add(access_obj)
        try:
            session.commit()
        except SQLAlchemyError:
            session.rollback()
            _log.debug("Access level %s could not be added", access)


def arrow_ts(value):
    return "%s" % arrow.get(value).timestamp


class AccessLevels(BASE):
    """ Different access levels a user/group can have for a project """

    __tablename__ = "access_levels"

    access = sa.Column(sa.String(255), primary_key=True)


class StatusIssue(BASE):
    """ Stores the status a ticket can have.

    Table -- status_issue
    """

    __tablename__ = "status_issue"

    id = sa.Column(sa.Integer, primary_key=True)
    status = sa.Column(sa.String(255), nullable=False, unique=True)


class StatusPullRequest(BASE):
    """ Stores the status a pull-request can have.

    Table -- status_issue
    """

    __tablename__ = "status_pull_requests"

    id = sa.Column(sa.Integer, primary_key=True)
    status = sa.Column(sa.String(255), nullable=False, unique=True)


class User(BASE):
    """ Stores information about users.

    Table -- users
    """

    __tablename__ = "users"
    id = sa.Column(sa.Integer, primary_key=True)
    user = sa.Column(sa.String(255), nullable=False, unique=True, index=True)
    fullname = sa.Column(sa.String(255), nullable=False, index=True)
    default_email = sa.Column(sa.Text, nullable=False)
    _settings = sa.Column(sa.Text, nullable=True)

    password = sa.Column(sa.Text, nullable=True)
    token = sa.Column(sa.String(50), nullable=True)
    created = sa.Column(sa.DateTime, nullable=False, default=sa.func.now())
    updated_on = sa.Column(
        sa.DateTime,
        nullable=False,
        default=sa.func.now(),
        onupdate=sa.func.now(),
    )

    refuse_sessions_before = sa.Column(
        sa.DateTime, nullable=True, default=None
    )

    # Relations
    group_objs = relation(
        "PagureGroup",
        secondary="pagure_user_group",
        primaryjoin="users.c.id==pagure_user_group.c.user_id",
        secondaryjoin="pagure_group.c.id==pagure_user_group.c.group_id",
        backref="users",
    )
    session = relation("PagureUserVisit", backref="user")

    @property
    def username(self):
        """ Return the username. """
        return self.user

    @property
    def html_title(self):
        """ Return the ``fullname (username)`` or simply ``username`` to be
        used in the html templates.
        """
        if self.fullname:
            return "%s (%s)" % (self.fullname, self.user)
        else:
            return self.user

    @property
    def groups(self):
        """ Return the list of Group.group_name in which the user is. """
        return [group.group_name for group in self.group_objs]

    @property
    def settings(self):
        """ Return the dict stored as string in the database as an actual
        dict object.
        """
        default = {"cc_me_to_my_actions": False}

        if self._settings:
            current = json.loads(self._settings)
            # Update the current dict with the new keys
            for key in default:
                if key not in current:
                    current[key] = default[key]
                elif is_true(current[key]):
                    current[key] = True
            return current
        else:
            return default

    @settings.setter
    def settings(self, settings):
        """ Ensures the settings are properly saved. """
        self._settings = json.dumps(settings)

    def __repr__(self):
        """ Return a string representation of this object. """

        return "User: %s - name %s" % (self.id, self.user)

    def to_json(self, public=False):
        """ Return a representation of the User in a dictionary. """
        output = {"name": self.user, "fullname": self.fullname}
        if not public:
            output["default_email"] = self.default_email
            output["emails"] = sorted([email.email for email in self.emails])

        return output


class UserEmail(BASE):
    """ Stores email information about the users.

    Table -- user_emails
    """

    __tablename__ = "user_emails"
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    email = sa.Column(sa.String(255), nullable=False, unique=True)

    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref(
            "emails", cascade="delete, delete-orphan", single_parent=True
        ),
    )


class UserEmailPending(BASE):
    """ Stores email information about the users.

    Table -- user_emails_pending
    """

    __tablename__ = "user_emails_pending"
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    email = sa.Column(sa.String(255), nullable=False, unique=True)
    token = sa.Column(sa.String(50), nullable=True)
    created = sa.Column(sa.DateTime, nullable=False, default=sa.func.now())

    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref(
            "emails_pending",
            cascade="delete, delete-orphan",
            single_parent=True,
        ),
    )


class Project(BASE):
    """ Stores the projects.

    Table -- projects
    """

    __tablename__ = "projects"

    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    namespace = sa.Column(sa.String(255), nullable=True, index=True)
    name = sa.Column(sa.String(255), nullable=False, index=True)
    description = sa.Column(sa.Text, nullable=True)
    url = sa.Column(sa.Text, nullable=True)
    _settings = sa.Column(sa.Text, nullable=True)
    # The hook_token is used to sign the notification sent via web-hook
    hook_token = sa.Column(sa.String(40), nullable=False, unique=True)
    avatar_email = sa.Column(sa.Text, nullable=True)
    is_fork = sa.Column(sa.Boolean, default=False, nullable=False)
    read_only = sa.Column(sa.Boolean, default=True, nullable=False)
    parent_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE"),
        nullable=True,
    )
    _priorities = sa.Column(sa.Text, nullable=True)
    default_priority = sa.Column(sa.Text, nullable=True)
    _milestones = sa.Column(sa.Text, nullable=True)
    _milestones_keys = sa.Column(sa.Text, nullable=True)
    _quick_replies = sa.Column(sa.Text, nullable=True)
    _reports = sa.Column(sa.Text, nullable=True)
    _notifications = sa.Column(sa.Text, nullable=True)
    _close_status = sa.Column(sa.Text, nullable=True)
    _block_users = sa.Column(sa.Text, nullable=True)
    mirrored_from = sa.Column(sa.Text, nullable=True)
    mirrored_from_last_log = sa.Column(sa.Text, nullable=True)

    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    date_modified = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    parent = relation(
        "Project",
        remote_side=[id],
        backref=backref(
            "forks", order_by=str("(projects.c.date_created).desc()")
        ),
    )
    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref="projects",
    )
    private = sa.Column(sa.Boolean, nullable=False, default=False)
    repospanner_region = sa.Column(sa.Text, nullable=True)

    users = relation(
        "User",
        secondary="user_projects",
        primaryjoin="projects.c.id==user_projects.c.project_id",
        secondaryjoin="users.c.id==user_projects.c.user_id",
        backref="co_projects",
    )

    admins = relation(
        "User",
        secondary="user_projects",
        primaryjoin="projects.c.id==user_projects.c.project_id",
        secondaryjoin="and_(users.c.id==user_projects.c.user_id,\
                user_projects.c.access=='admin')",
        backref="co_projects_admins",
        viewonly=True,
    )

    committers = relation(
        "User",
        secondary="user_projects",
        primaryjoin="projects.c.id==user_projects.c.project_id",
        secondaryjoin="and_(users.c.id==user_projects.c.user_id,\
                or_(user_projects.c.access=='commit',\
                    user_projects.c.access=='admin'))",
        backref="co_projects_committers",
        viewonly=True,
    )

    groups = relation(
        "PagureGroup",
        secondary="projects_groups",
        primaryjoin="projects.c.id==projects_groups.c.project_id",
        secondaryjoin="pagure_group.c.id==projects_groups.c.group_id",
        backref=backref(
            "projects",
            order_by=str(
                "func.lower(projects.c.namespace).desc(), "
                "func.lower(projects.c.name)"
            ),
        ),
        order_by="PagureGroup.group_name.asc()",
    )

    admin_groups = relation(
        "PagureGroup",
        secondary="projects_groups",
        primaryjoin="projects.c.id==projects_groups.c.project_id",
        secondaryjoin="and_(pagure_group.c.id==projects_groups.c.group_id,\
                projects_groups.c.access=='admin')",
        backref="projects_admin_groups",
        order_by="PagureGroup.group_name.asc()",
        viewonly=True,
    )

    committer_groups = relation(
        "PagureGroup",
        secondary="projects_groups",
        primaryjoin="projects.c.id==projects_groups.c.project_id",
        secondaryjoin="and_(pagure_group.c.id==projects_groups.c.group_id,\
                or_(projects_groups.c.access=='admin',\
                    projects_groups.c.access=='commit'))",
        backref="projects_committer_groups",
        order_by="PagureGroup.group_name.asc()",
        viewonly=True,
    )

    def __repr__(self):
        return "Project(%s, name:%s, namespace:%s, url:%s, is_fork:%s,\
                parent_id:%s)" % (
            self.id,
            self.name,
            self.namespace,
            self.url,
            self.is_fork,
            self.parent_id,
        )

    @property
    def isa(self):
        """ A string to allow finding out that this is a project. """
        return "project"

    @property
    def mail_id(self):
        """ Return a unique representation of the project as string that
        can be used when sending emails.
        """
        return "%s-project-%s" % (self.fullname, self.id)

    @property
    def is_on_repospanner(self):
        """ Returns whether this repo is on repoSpanner. """
        return self.repospanner_region is not None

    @property
    def path(self):
        """ Return the name of the git repo on the filesystem. """
        return "%s.git" % self.fullname

    def repospanner_repo_info(self, repotype, region=None):
        """ Returns info for getting a repoSpanner repo for a project.

        Args:
            repotype (string): Type of repository
            region (string): If repo is not on repoSpanner, return url as if
                it was in this region. Used for migrating to repoSpanner.
        Return type: (url, dict): First is the clone url, then a dict with
            the regioninfo.
        """
        if not self.is_on_repospanner and region is None:
            raise ValueError("Repo %s is not on repoSpanner" % self.fullname)
        if self.is_on_repospanner and region is not None:
            raise ValueError(
                "Repo %s is already on repoSpanner" % self.fullname
            )
        if region is None:
            region = self.repospanner_region
        regioninfo = pagure_config["REPOSPANNER_REGIONS"].get(region)
        if not regioninfo:
            raise ValueError(
                "Invalid repoSpanner region %s looked up" % region
            )

        url = "%s/repo/%s.git" % (
            regioninfo["url"],
            self._repospanner_repo_name(repotype, region),
        )
        return url, regioninfo

    def _repospanner_repo_name(self, repotype, region=None):
        """ Returns the name of a repo as named in repoSpanner.

        Args:
            repotype (string): Type of repository
            region (string): repoSpanner region name
        Return type: (string)
        """
        if region is None:
            region = self.repospanner_region
        return os.path.join(
            pagure_config["REPOSPANNER_REGIONS"][region].get(
                "repo_prefix", ""
            ),
            repotype,
            self.fullname,
        )

    def repopath(self, repotype):
        """ Return the full repository path of the git repo on the filesystem.

        If the repository is on repoSpanner, this will be a pseudo repository,
        which is "git repo enough" to be considered a valid repo, but any
        access should go through a repoSpanner enlightened libgit2.
        """
        if self.is_on_repospanner:
            pseudopath = os.path.join(
                pagure_config["REPOSPANNER_PSEUDO_FOLDER"], repotype, self.path
            )
            if not os.path.exists(pseudopath):
                repourl, regioninfo = self.repospanner_repo_info(repotype)
                fake = pygit2.init_repository(pseudopath, bare=True)
                fake.config["repospanner.url"] = repourl
                fake.config["repospanner.cert"] = regioninfo["push_cert"][
                    "cert"
                ]
                fake.config["repospanner.key"] = regioninfo["push_cert"]["key"]
                fake.config["repospanner.cacert"] = regioninfo["ca"]
                fake.config["repospanner.enabled"] = True
                del fake
            return pseudopath

        maindir = None
        if repotype == "main":
            maindir = pagure_config["GIT_FOLDER"]
        elif repotype == "docs":
            maindir = pagure_config["DOCS_FOLDER"]
        elif repotype == "tickets":
            maindir = pagure_config["TICKETS_FOLDER"]
        elif repotype == "requests":
            maindir = pagure_config["REQUESTS_FOLDER"]
        else:
            return ValueError("Repotype %s is invalid" % repotype)
        if maindir is None:
            if repotype == "main":
                raise Exception("No maindir for main repos?")
            return None
        return os.path.join(maindir, self.path)

    @property
    def fullname(self):
        """ Return the name of the git repo as user/project if it is a
        project forked, otherwise it returns the project name.
        """
        str_name = self.name
        if self.namespace:
            str_name = "%s/%s" % (self.namespace, str_name)
        if self.is_fork:
            str_name = "forks/%s/%s" % (self.user.user, str_name)
        return str_name

    @property
    def url_path(self):
        """ Return the path at which this project can be accessed in the
        web UI.
        """
        path = self.name
        if self.namespace:
            path = "%s/%s" % (self.namespace, path)
        if self.is_fork:
            path = "fork/%s/%s" % (self.user.user, path)
        return path

    @property
    def tags_text(self):
        """ Return the list of tags in a simple text form. """
        return [tag.tag for tag in self.tags]

    @property
    def settings(self):
        """ Return the dict stored as string in the database as an actual
        dict object.
        """
        default = {
            "issue_tracker": True,
            "project_documentation": False,
            "pull_requests": True,
            "Only_assignee_can_merge_pull-request": False,
            "Minimum_score_to_merge_pull-request": -1,
            "Web-hooks": None,
            "Enforce_signed-off_commits_in_pull-request": False,
            "always_merge": False,
            "issues_default_to_private": False,
            "fedmsg_notifications": True,
            "stomp_notifications": True,
            "mqtt_notifications": True,
            "pull_request_access_only": False,
            "notify_on_pull-request_flag": False,
            "notify_on_commit_flag": False,
            "issue_tracker_read_only": False,
            "disable_non_fast-forward_merges": False,
            "open_metadata_access_to_all": False,
        }

        if self._settings:
            current = json.loads(self._settings)
            # Update the current dict with the new keys
            for key in default:
                if key not in current:
                    current[key] = default[key]
                elif key == "Minimum_score_to_merge_pull-request":
                    current[key] = int(current[key])
                elif is_true(current[key]):
                    current[key] = True
            # Update the current dict, removing the old keys
            for key in sorted(current):
                if key not in default:
                    del current[key]
            return current
        else:
            return default

    @settings.setter
    def settings(self, settings):
        """ Ensures the settings are properly saved. """
        self._settings = json.dumps(settings)

    @property
    def milestones(self):
        """ Return the dict stored as string in the database as an actual
        dict object.
        """
        milestones = {}

        if self._milestones:

            def _convert_to_dict(value):
                if isinstance(value, dict):
                    return value
                else:
                    return {"date": value, "active": True}

            milestones = dict(
                [
                    (k, _convert_to_dict(v))
                    for k, v in json.loads(self._milestones).items()
                ]
            )

        return milestones

    @milestones.setter
    def milestones(self, milestones):
        """ Ensures the milestones are properly saved. """
        self._milestones = json.dumps(milestones)

    @property
    def milestones_keys(self):
        """ Return the list of milestones so we can keep the order consistent.
        """
        milestones_keys = {}

        if self._milestones_keys:
            milestones_keys = json.loads(self._milestones_keys)

        return milestones_keys

    @milestones_keys.setter
    def milestones_keys(self, milestones_keys):
        """ Ensures the milestones keys are properly saved. """
        self._milestones_keys = json.dumps(milestones_keys)

    @property
    def priorities(self):
        """ Return the dict stored as string in the database as an actual
        dict object.
        """
        priorities = {}

        if self._priorities:
            priorities = json.loads(self._priorities)

        return priorities

    @priorities.setter
    def priorities(self, priorities):
        """ Ensures the priorities are properly saved. """
        self._priorities = json.dumps(priorities)

    @property
    def block_users(self):
        """ Return the dict stored as string in the database as an actual
        dict object.
        """
        block_users = []

        if self._block_users:
            block_users = json.loads(self._block_users)

        return block_users

    @block_users.setter
    def block_users(self, block_users):
        """ Ensures the block_users are properly saved. """
        self._block_users = json.dumps(block_users)

    @property
    def quick_replies(self):
        """ Return a list of quick replies available for pull requests and
        issues.
        """
        quick_replies = []

        if self._quick_replies:
            quick_replies = json.loads(self._quick_replies)

        return quick_replies

    @quick_replies.setter
    def quick_replies(self, quick_replies):
        """ Ensures the quick replies are properly saved. """
        self._quick_replies = json.dumps(quick_replies)

    @property
    def notifications(self):
        """ Return the dict stored as string in the database as an actual
        dict object.
        """
        notifications = {}

        if self._notifications:
            notifications = json.loads(self._notifications)

        return notifications

    @notifications.setter
    def notifications(self, notifications):
        """ Ensures the notifications are properly saved. """
        self._notifications = json.dumps(notifications)

    @property
    def reports(self):
        """ Return the dict stored as string in the database as an actual
        dict object.
        """
        reports = {}

        if self._reports:
            reports = json.loads(self._reports)

        return reports

    @reports.setter
    def reports(self, reports):
        """ Ensures the reports are properly saved. """
        self._reports = json.dumps(reports)

    @property
    def close_status(self):
        """ Return the dict stored as string in the database as an actual
        dict object.
        """
        close_status = []

        if self._close_status:
            close_status = json.loads(self._close_status)

        return close_status

    @close_status.setter
    def close_status(self, close_status):
        """ Ensures the different close status are properly saved. """
        self._close_status = json.dumps(close_status)

    @property
    def open_requests(self):
        """ Returns the number of open pull-requests for this project. """
        return (
            BASE.metadata.bind.query(PullRequest)
            .filter(self.id == PullRequest.project_id)
            .filter(PullRequest.status == "Open")
            .count()
        )

    @property
    def open_tickets(self):
        """ Returns the number of open tickets for this project. """
        return (
            BASE.metadata.bind.query(Issue)
            .filter(self.id == Issue.project_id)
            .filter(Issue.status == "Open")
            .count()
        )

    @property
    def open_tickets_public(self):
        """ Returns the number of open tickets for this project. """
        return (
            BASE.metadata.bind.query(Issue)
            .filter(self.id == Issue.project_id)
            .filter(Issue.status == "Open")
            .filter(Issue.private == False)  # noqa: E712
            .count()
        )

    @property
    def contributors(self):
        """ Return the dict presenting the different contributors of the
        project based on their access level.
        """
        contributors = collections.defaultdict(list)

        for user in self.user_projects:
            contributors[user.access].append(user.user)

        return contributors

    @property
    def contributor_groups(self):
        """ Return the dict presenting the different contributors of the
        project based on their access level.
        """
        contributors = collections.defaultdict(list)

        for group in self.projects_groups:
            contributors[group.access].append(group.group)

        return contributors

    def get_project_users(self, access, combine=True):
        """ Returns the list of users/groups of the project according
        to the given access.

        :arg access: the access level to query for, can be: 'admin',
            'commit' or 'ticket'.
        :type access: string
        :arg combine: The access levels have some hierarchy -
            like: all the users having commit access also has
            ticket access and the admins have all the access
            that commit and ticket access users have. If combine
            is set to False, this function will only return those
            users which have the given access and no other access.
            ex: if access is 'ticket' and combine is True, it will
            return all the users with ticket access which includes
            all the committers and admins. If combine were False,
            it would have returned only the users with ticket access
            and would not have included committers and admins.
        :type combine: boolean
        """

        if access not in ["admin", "commit", "ticket"]:
            raise pagure.exceptions.AccessLevelNotFound(
                "The access level does not exist"
            )

        if combine:
            if access == "admin":
                return self.admins
            elif access == "commit":
                return self.committers
            elif access == "ticket":
                return self.users
        else:
            if access == "admin":
                return self.admins
            elif access == "commit":
                committers = set(self.committers)
                admins = set(self.admins)
                return list(committers - admins)
            elif access == "ticket":
                committers = set(self.committers)
                admins = set(self.admins)
                users = set(self.users)
                return list(users - committers - admins)

    def get_project_groups(self, access, combine=True):
        """ Returns the list of groups of the project according
        to the given access.

        :arg access: the access level to query for, can be: 'admin',
            'commit' or 'ticket'.
        :type access: string
        :arg combine: The access levels have some hierarchy -
            like: all the groups having commit access also has
            ticket access and the admin_groups have all the access
            that committer_groups and ticket access groups have.
            If combine is set to False, this function will only return
            those groups which have the given access and no other access.
            ex: if access is 'ticket' and combine is True, it will
            return all the groups with ticket access which includes
            all the committer_groups and admin_groups. If combine were False,
            it would have returned only the groups with ticket access
            and would not have included committer_groups and admin_groups.
        :type combine: boolean
        """

        if access not in ["admin", "commit", "ticket"]:
            raise pagure.exceptions.AccessLevelNotFound(
                "The access level does not exist"
            )

        if combine:
            if access == "admin":
                return self.admin_groups
            elif access == "commit":
                return self.committer_groups
            elif access == "ticket":
                return self.groups
        else:
            if access == "admin":
                return self.admin_groups
            elif access == "commit":
                committers = set(self.committer_groups)
                admins = set(self.admin_groups)
                return list(committers - admins)
            elif access == "ticket":
                committers = set(self.committer_groups)
                admins = set(self.admin_groups)
                groups = set(self.groups)
                return list(groups - committers - admins)

    @property
    def access_users(self):
        """ Return a dictionary with all user access
        """
        return {
            "admin": self.get_project_users(access="admin", combine=False),
            "commit": self.get_project_users(access="commit", combine=False),
            "ticket": self.get_project_users(access="ticket", combine=False),
        }

    @property
    def access_users_json(self):
        json_access_users = {"owner": [self.user.username]}
        for access, users in self.access_users.items():
            json_access_users[access] = []
            for user in users:
                json_access_users[access].append(user.user)

        return json_access_users

    @property
    def access_groups_json(self):
        json_access_groups = {}
        for access, groups in self.access_groups.items():
            json_access_groups[access] = []
            for group in groups:
                json_access_groups[access].append(group.group_name)

        return json_access_groups

    @property
    def access_groups(self):
        """ Return a dictionary with all group access
        """
        return {
            "admin": self.get_project_groups(access="admin", combine=False),
            "commit": self.get_project_groups(access="commit", combine=False),
            "ticket": self.get_project_groups(access="ticket", combine=False),
        }

    def lock(self, ltype):
        """ Get a SQL lock of type ltype for the current project.
        """
        return ProjectLocker(self, ltype)

    def to_json(self, public=False, api=False):
        """ Return a representation of the project as JSON.
        """
        custom_keys = [[key.name, key.key_type] for key in self.issue_keys]

        output = {
            "id": self.id,
            "name": self.name,
            "fullname": self.fullname,
            "url_path": self.url_path,
            "description": self.description,
            "namespace": self.namespace,
            "parent": self.parent.to_json(public=public, api=api)
            if self.parent
            else None,
            "date_created": arrow_ts(self.date_created),
            "date_modified": arrow_ts(self.date_modified),
            "user": self.user.to_json(public=public),
            "access_users": self.access_users_json,
            "access_groups": self.access_groups_json,
            "tags": self.tags_text,
            "priorities": self.priorities,
            "custom_keys": custom_keys,
            "close_status": self.close_status,
            "milestones": self.milestones,
        }
        if not api and not public:
            output["settings"] = self.settings

        return output


class ProjectLock(BASE):
    """ Table used to define project-specific locks.

    Table -- project_locks
    """

    __tablename__ = "project_locks"

    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        primary_key=True,
    )
    lock_type = sa.Column(
        sa.Enum(
            "WORKER", "WORKER_TICKET", "WORKER_REQUEST", name="lock_type_enum"
        ),
        nullable=False,
        primary_key=True,
    )


class ProjectLocker(object):
    """ This is used as a context manager to lock a project.

    This is used as a context manager to make it very explicit when we unlock
    the project, and so that we unlock even if an exception occurs.
    """

    def __init__(self, project, ltype):
        self.session = None
        self.lock = None
        self.project_id = project.id
        self.ltype = ltype

    def __enter__(self):
        from pagure.lib.model_base import create_session

        self.session = create_session()

        _log.info("Grabbing lock for %d", self.project_id)
        query = (
            self.session.query(ProjectLock)
            .filter(ProjectLock.project_id == self.project_id)
            .filter(ProjectLock.lock_type == self.ltype)
            .with_for_update(nowait=False, read=False)
        )

        try:
            self.lock = query.one()
        except Exception:
            pl = ProjectLock(project_id=self.project_id, lock_type=self.ltype)
            self.session.add(pl)
            self.session.commit()
            self.lock = query.one()

        assert self.lock is not None
        _log.info("Got lock for %d: %s", self.project_id, self.lock)

    def __exit__(self, *exargs):
        _log.info("Releasing lock for %d", self.project_id)
        self.session.remove()
        _log.info("Released lock for %d", self.project_id)


class ProjectUser(BASE):
    """ Stores the user of a projects.

    Table -- user_projects
    """

    __tablename__ = "user_projects"
    __table_args__ = (sa.UniqueConstraint("project_id", "user_id", "access"),)

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE"),
        nullable=False,
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    access = sa.Column(
        sa.String(255),
        sa.ForeignKey(
            "access_levels.access", onupdate="CASCADE", ondelete="CASCADE"
        ),
        nullable=False,
    )

    project = relation(
        "Project",
        remote_side=[Project.id],
        backref=backref(
            "user_projects", cascade="delete,delete-orphan", single_parent=True
        ),
    )

    user = relation("User", backref="user_projects")


class SSHKey(BASE):
    """ Stores information about SSH keys.

    Every instance needs to either have user_id set (SSH key for a specific
    user) or project_id ("deploy key" for a specific project).

    Table -- sshkeys
    """

    __tablename__ = "sshkeys"
    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    pushaccess = sa.Column(sa.Boolean, nullable=False, default=False)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    public_ssh_key = sa.Column(sa.Text, nullable=False)
    ssh_short_key = sa.Column(sa.Text, nullable=False)
    ssh_search_key = sa.Column(
        sa.String(length=60), nullable=False, index=True, unique=True
    )
    creator_user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    # Validations
    # These two validators are intended to make sure an SSHKey is either
    # assigned to a Project or a User, but not both.
    @validates("project_id")
    def validate_project_id(self, key, value):
        """ Validates that user_id is not set. """
        if self.user_id is not None:
            raise ValueError("SSHKey can't have both project and user")
        return value

    @validates("user_id")
    def validate_user_id(self, key, value):
        """ Validates that project_id is not set. """
        if self.project_id is not None:
            raise ValueError("SSHKey can't have both user and project")
        return value

    # Relations
    project = relation(
        "Project",
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref(
            "deploykeys", cascade="delete, delete-orphan", single_parent=True
        ),
    )

    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref(
            "sshkeys", cascade="delete, delete-orphan", single_parent=True
        ),
    )

    creator_user = relation(
        "User", foreign_keys=[creator_user_id], remote_side=[User.id]
    )


class Issue(BASE):
    """ Stores the issues reported on a project.

    Table -- issues
    """

    __tablename__ = "issues"

    id = sa.Column(sa.Integer, primary_key=True)
    uid = sa.Column(sa.String(32), unique=True, nullable=False)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE"),
        primary_key=True,
    )
    title = sa.Column(sa.Text, nullable=False)
    content = sa.Column(sa.Text(), nullable=False)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    assignee_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    status = sa.Column(
        sa.String(255),
        sa.ForeignKey("status_issue.status", onupdate="CASCADE"),
        default="Open",
        nullable=False,
    )
    private = sa.Column(sa.Boolean, nullable=False, default=False)
    priority = sa.Column(sa.Integer, nullable=True, default=None)
    milestone = sa.Column(sa.String(255), nullable=True, default=None)
    close_status = sa.Column(sa.Text, nullable=True)
    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    last_updated = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    closed_at = sa.Column(sa.DateTime, nullable=True)
    closed_by_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=True,
    )

    project = relation(
        "Project",
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref("issues", cascade="delete, delete-orphan"),
        single_parent=True,
    )

    user = relation(
        "User", foreign_keys=[user_id], remote_side=[User.id], backref="issues"
    )
    assignee = relation(
        "User",
        foreign_keys=[assignee_id],
        remote_side=[User.id],
        backref="assigned_issues",
    )

    parents = relation(
        "Issue",
        secondary="issue_to_issue",
        primaryjoin="issues.c.uid==issue_to_issue.c.child_issue_id",
        secondaryjoin="issue_to_issue.c.parent_issue_id==issues.c.uid",
        backref="children",
    )

    tags = relation(
        "TagColored",
        secondary="tags_issues_colored",
        primaryjoin="issues.c.uid==tags_issues_colored.c.issue_uid",
        secondaryjoin="tags_issues_colored.c.tag_id==tags_colored.c.id",
        viewonly=True,
    )

    closed_by = relation(
        "User",
        foreign_keys=[closed_by_id],
        remote_side=[User.id],
        backref="closed_issues",
    )

    def __repr__(self):
        return "Issue(%s, project:%s, user:%s, title:%s)" % (
            self.id,
            self.project.name,
            self.user.user,
            self.title,
        )

    @property
    def attachments(self):
        """ Return a list of attachment tuples: (LINK, FILENAME, DISPLAY_NAME,
        DATE) """

        def extract_info(text):
            """ Return a tuple containing the link, file name, and the
            "display" file name from the markdown attachment link """
            pattern_md = re.compile(r"^\[\!(.*)\]")
            pattern_link = re.compile(r"\(([^)]+)\)")
            pattern_file = re.compile(r"\[([^]]+)\]")

            try:
                md_link = pattern_md.search(text).group(1)
                link = pattern_link.search(md_link).group(1)
                filename = pattern_file.search(md_link).group(1)
                if md_link is None or link is None or filename is None:
                    # No match, return the original string
                    return (text, text, text)
                if len(filename) > 50:
                    # File name is too long to display, truncate it.
                    display_name = filename[:50] + "..."
                else:
                    display_name = filename
            except AttributeError:
                # Search failed, return the original string
                return (text, text, text)
            return (link, filename, display_name)

        attachments = []
        if self.content:
            # Check the initial issue description for attachments
            lines = self.content.split("\n")
            for line in lines:
                if line and line != "" and line.startswith("[!["):
                    link, filename, display_name = extract_info(line)
                    attachments.append(
                        (
                            link,
                            filename,
                            display_name,
                            self.date_created.strftime("%Y-%m-%d %H:%M:%S"),
                            None,
                        )
                    )
        if self.comments:
            # Check the comments for attachments
            for comment in self.comments:
                if comment.id == 0:
                    comment_text = comment.content
                else:
                    comment_text = comment.comment
                lines = comment_text.split("\n")
                for line in lines:
                    if line and line != "" and line.startswith("[!["):
                        link, filename, display_name = extract_info(line)
                        attachments.append(
                            (
                                link,
                                filename,
                                display_name,
                                comment.date_created.strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                ),
                                "%s" % comment.id,
                            )
                        )
        return attachments

    @property
    def isa(self):
        """ A string to allow finding out that this is an issue. """
        return "issue"

    @property
    def repotype(self):
        """ A string returning the repotype for repopath() calls. """
        return "tickets"

    @property
    def mail_id(self):
        """ Return a unique reprensetation of the issue as string that
        can be used when sending emails.
        """
        return "%s-ticket-%s" % (self.project.name, self.uid)

    @property
    def tags_text(self):
        """ Return the list of tags in a simple text form. """
        return [tag.tag for tag in self.tags]

    @property
    def depending_text(self):
        """ Return the list of issue this issue depends on in simple text. """
        return [issue.id for issue in self.parents]

    @property
    def blocking_text(self):
        """ Return the list of issue this issue blocks on in simple text. """
        return [issue.id for issue in self.children]

    @property
    def user_comments(self):
        """ Return user comments only, filter it from notifications
        """
        return [
            comment for comment in self.comments if not comment.notification
        ]

    @property
    def sortable_priority(self):
        """ Return an empty string if no priority is set allowing issues to
        be sorted using this attribute. """
        return self.priority if self.priority else ""

    def to_json(self, public=False, with_comments=True, with_project=False):
        """ Returns a dictionary representation of the issue.

        """
        custom_fields = [
            dict(
                name=field.key.name,
                key_type=field.key.key_type,
                value=field.value,
                key_data=field.key.key_data,
            )
            for field in self.other_fields
        ]

        output = {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "status": self.status,
            "close_status": self.close_status,
            "date_created": arrow_ts(self.date_created),
            "last_updated": arrow_ts(self.last_updated),
            "closed_at": arrow_ts(self.closed_at) if self.closed_at else None,
            "user": self.user.to_json(public=public),
            "private": self.private,
            "tags": self.tags_text,
            "depends": ["%s" % item for item in self.depending_text],
            "blocks": ["%s" % item for item in self.blocking_text],
            "assignee": self.assignee.to_json(public=public)
            if self.assignee
            else None,
            "priority": self.priority,
            "milestone": self.milestone,
            "custom_fields": custom_fields,
            "closed_by": self.closed_by.to_json(public=public)
            if self.closed_by
            else None,
        }

        comments = []
        if with_comments:
            for comment in self.comments:
                comments.append(comment.to_json(public=public))

        output["comments"] = comments

        if with_project:
            output["project"] = self.project.to_json(public=public, api=True)

        return output


class IssueToIssue(BASE):
    """ Stores the parent/child relationship between two issues.

    Table -- issue_to_issue
    """

    __tablename__ = "issue_to_issue"

    parent_issue_id = sa.Column(
        sa.String(32),
        sa.ForeignKey("issues.uid", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    child_issue_id = sa.Column(
        sa.String(32),
        sa.ForeignKey("issues.uid", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )


class PrToIssue(BASE):
    """ Stores the associations between issues and pull-requests.

    Table -- pr_to_issue
    """

    __tablename__ = "pr_to_issue"

    pull_request_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            "pull_requests.uid", ondelete="CASCADE", onupdate="CASCADE"
        ),
        primary_key=True,
    )
    issue_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey("issues.uid", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    origin = sa.Column(sa.String(32), index=True)


class IssueComment(BASE):
    """ Stores the comments made on a commit/file.

    Table -- issue_comments
    """

    __tablename__ = "issue_comments"

    id = sa.Column(sa.Integer, primary_key=True)
    issue_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey("issues.uid", ondelete="CASCADE", onupdate="CASCADE"),
        index=True,
    )
    comment = sa.Column(sa.Text(), nullable=False)
    parent_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("issue_comments.id", onupdate="CASCADE"),
        nullable=True,
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )

    notification = sa.Column(sa.Boolean, default=False, nullable=False)
    edited_on = sa.Column(sa.DateTime, nullable=True)
    editor_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=True,
    )

    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    issue = relation(
        "Issue",
        foreign_keys=[issue_uid],
        remote_side=[Issue.uid],
        backref=backref(
            "comments",
            cascade="delete, delete-orphan",
            order_by=str("IssueComment.date_created"),
        ),
    )
    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref="comment_issues",
    )
    editor = relation("User", foreign_keys=[editor_id], remote_side=[User.id])

    _reactions = sa.Column(sa.Text, nullable=True)

    @property
    def mail_id(self):
        """ Return a unique reprensetation of the issue as string that
        can be used when sending emails.
        """
        return "%s-ticket-%s-%s" % (
            self.issue.project.name,
            self.issue.uid,
            self.id,
        )

    @property
    def parent(self):
        """ Return the parent, in this case the issue object. """
        return self.issue

    @property
    def reactions(self):
        """ Return the reactions stored as a string in the database parsed as
        an actual dict object.
        """
        if self._reactions:
            return json.loads(self._reactions)
        return {}

    @reactions.setter
    def reactions(self, reactions):
        """ Ensures that reactions are properly saved. """
        self._reactions = json.dumps(reactions)

    def to_json(self, public=False):
        """ Returns a dictionary representation of the issue.

        """
        output = {
            "id": self.id,
            "comment": self.comment,
            "parent": self.parent_id,
            "date_created": arrow_ts(self.date_created),
            "user": self.user.to_json(public=public),
            "edited_on": arrow_ts(self.edited_on) if self.edited_on else None,
            "editor": self.editor.to_json(public=public)
            if self.editor_id
            else None,
            "notification": self.notification,
            "reactions": self.reactions,
        }
        return output


class IssueKeys(BASE):
    """ Stores the custom keys a project can use on issues.

    Table -- issue_keys
    """

    __tablename__ = "issue_keys"

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    name = sa.Column(sa.String(255), nullable=False)
    key_type = sa.Column(sa.String(255), nullable=False)
    key_data = sa.Column(sa.Text())
    key_notify = sa.Column(sa.Boolean, default=False, nullable=False)

    __table_args__ = (sa.UniqueConstraint("project_id", "name"),)

    project = relation(
        "Project",
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref(
            "issue_keys", cascade="delete, delete-orphan", single_parent=True
        ),
    )

    def __lt__(self, other):
        if hasattr(other, "name"):
            return self.name.__lt__(other.name)

    @property
    def data(self):
        """ Return the list of items """
        if self.key_data:
            return json.loads(self.key_data)
        else:
            return None

    @data.setter
    def data(self, data_obj):
        """ Store the list data in JSON. """
        if data_obj is None:
            self.key_data = None
        else:
            self.key_data = json.dumps(data_obj)


class IssueValues(BASE):
    """ Stores the values of the custom keys set by project on issues.

    Table -- issue_values
    """

    __tablename__ = "issue_values"

    key_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("issue_keys.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    issue_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey("issues.uid", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    value = sa.Column(sa.Text(), nullable=False)

    issue = relation(
        "Issue",
        foreign_keys=[issue_uid],
        remote_side=[Issue.uid],
        backref=backref(
            "other_fields", cascade="delete, delete-orphan", single_parent=True
        ),
    )

    key = relation(
        "IssueKeys",
        foreign_keys=[key_id],
        remote_side=[IssueKeys.id],
        backref=backref("values", cascade="delete, delete-orphan"),
    )


class Tag(BASE):
    """ Stores the tags.

    Table -- tags
    """

    __tablename__ = "tags"

    tag = sa.Column(sa.String(255), primary_key=True)
    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )


class TagIssue(BASE):
    """ Stores the tag associated with an issue.

    Table -- tags_issues
    """

    __tablename__ = "tags_issues"

    tag = sa.Column(
        sa.String(255),
        sa.ForeignKey("tags.tag", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    issue_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey("issues.uid", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    issue = relation(
        "Issue",
        foreign_keys=[issue_uid],
        remote_side=[Issue.uid],
        backref=backref(
            "old_tags", cascade="delete, delete-orphan", single_parent=True
        ),
    )

    def __repr__(self):
        return "TagIssue(issue:%s, tag:%s)" % (self.issue.id, self.tag)


class TagColored(BASE):
    """ Stores the colored tags.

    Table -- tags_colored
    """

    __tablename__ = "tags_colored"

    id = sa.Column(sa.Integer, primary_key=True)
    tag = sa.Column(sa.String(255), nullable=False)
    tag_description = sa.Column(sa.String(255), default="")
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    tag_color = sa.Column(sa.String(25), default="DeepSkyBlue")
    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    __table_args__ = (sa.UniqueConstraint("project_id", "tag"),)

    project = relation(
        "Project",
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref(
            "tags_colored", cascade="delete,delete-orphan", single_parent=True
        ),
    )

    def __repr__(self):
        return "TagColored(id: %s, tag:%s, tag_description:%s, color:%s)" % (
            self.id,
            self.tag,
            self.tag_description,
            self.tag_color,
        )


class TagIssueColored(BASE):
    """ Stores the colored tag associated with an issue.

    Table -- tags_issues_colored
    """

    __tablename__ = "tags_issues_colored"

    tag_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            "tags_colored.id", ondelete="CASCADE", onupdate="CASCADE"
        ),
        primary_key=True,
    )
    issue_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey("issues.uid", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    issue = relation(
        "Issue",
        foreign_keys=[issue_uid],
        remote_side=[Issue.uid],
        backref=backref(
            "tags_issues_colored", cascade="delete, delete-orphan"
        ),
    )
    tag = relation(
        "TagColored", foreign_keys=[tag_id], remote_side=[TagColored.id]
    )

    def __repr__(self):
        return "TagIssueColored(issue:%s, tag:%s, project:%s)" % (
            self.issue.id,
            self.tag.tag,
            self.tag.project.fullname,
        )


class TagProject(BASE):
    """ Stores the tag associated with a project.

    Table -- tags_projects
    """

    __tablename__ = "tags_projects"

    tag = sa.Column(
        sa.String(255),
        sa.ForeignKey("tags.tag", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    project = relation(
        "Project",
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref(
            "tags", cascade="delete, delete-orphan", single_parent=True
        ),
    )

    def __repr__(self):
        return "TagProject(project:%s, tag:%s)" % (
            self.project.fullname,
            self.tag,
        )


class PullRequest(BASE):
    """ Stores the pull requests created on a project.

    Table -- pull_requests
    """

    __tablename__ = "pull_requests"

    id = sa.Column(sa.Integer, primary_key=True)
    uid = sa.Column(sa.String(32), unique=True, nullable=False)
    title = sa.Column(sa.Text, nullable=False)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", ondelete="CASCADE", onupdate="CASCADE"),
        primary_key=True,
    )
    branch = sa.Column(sa.Text(), nullable=False)
    project_id_from = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    remote_git = sa.Column(sa.Text(), nullable=True)
    branch_from = sa.Column(sa.Text(), nullable=False)
    commit_start = sa.Column(sa.Text(), nullable=True)
    commit_stop = sa.Column(sa.Text(), nullable=True)
    initial_comment = sa.Column(sa.Text(), nullable=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    assignee_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    merge_status = sa.Column(
        sa.Enum(
            "NO_CHANGE",
            "FFORWARD",
            "CONFLICTS",
            "MERGE",
            name="merge_status_enum",
        ),
        nullable=True,
    )

    # While present this column isn't used anywhere yet
    private = sa.Column(sa.Boolean, nullable=False, default=False)

    status = sa.Column(
        sa.String(255),
        sa.ForeignKey("status_pull_requests.status", onupdate="CASCADE"),
        default="Open",
        nullable=False,
    )
    closed_by_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=True,
    )
    closed_at = sa.Column(sa.DateTime, nullable=True)

    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    updated_on = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    last_updated = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    project = relation(
        "Project",
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref("requests", cascade="delete, delete-orphan"),
        single_parent=True,
    )
    project_from = relation(
        "Project", foreign_keys=[project_id_from], remote_side=[Project.id]
    )

    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref="pull_requests",
    )
    assignee = relation(
        "User",
        foreign_keys=[assignee_id],
        remote_side=[User.id],
        backref="assigned_requests",
    )
    closed_by = relation(
        "User",
        foreign_keys=[closed_by_id],
        remote_side=[User.id],
        backref="closed_requests",
    )

    tags = relation(
        "TagColored",
        secondary="tags_pull_requests",
        primaryjoin="pull_requests.c.uid==tags_pull_requests.c.request_uid",
        secondaryjoin="tags_pull_requests.c.tag_id==tags_colored.c.id",
        viewonly=True,
    )

    related_issues = relation(
        "Issue",
        secondary="pr_to_issue",
        primaryjoin="pull_requests.c.uid==pr_to_issue.c.pull_request_uid",
        secondaryjoin="pr_to_issue.c.issue_uid==issues.c.uid",
        backref=backref(
            "related_prs", order_by=str("pull_requests.c.id.desc()")
        ),
    )

    def __repr__(self):
        return "PullRequest(%s, project:%s, user:%s, title:%s)" % (
            self.id,
            self.project.name,
            self.user.user,
            self.title,
        )

    @property
    def isa(self):
        """ A string to allow finding out that this is an pull-request. """
        return "pull-request"

    @property
    def repotype(self):
        """ A string returning the repotype for repopath() calls. """
        return "requests"

    @property
    def mail_id(self):
        """ Return a unique reprensetation of the issue as string that
        can be used when sending emails.
        """
        return "%s-pull-request-%s" % (self.project.name, self.uid)

    @property
    def tags_text(self):
        """ Return the list of tags in a simple text form. """
        return [tag.tag for tag in self.tags]

    @property
    def discussion(self):
        """ Return the list of comments related to the pull-request itself,
        ie: not related to a specific commit.
        """
        return [comment for comment in self.comments if not comment.commit_id]

    @property
    def flags_stats(self):
        """ Return some stats about the flags associated with this PR.
        """
        flags = self.flags
        flags.reverse()

        # Only keep the last flag from each service
        tmp = {}
        for flag in flags:
            tmp[flag.username] = flag

        output = collections.defaultdict(list)
        for flag in tmp.values():
            output[flag.status].append(flag)

        return output

    @property
    def score(self):
        """ Return the review score of the pull-request by checking the
        number of +1, -1, :thumbup: and :thumbdown: in the comment of the
        pull-request.
        This includes only the main comments not the inline ones.

        An user can only give one +1 and one -1.
        """
        votes = {}
        for comment in self.discussion:
            for word in ["+1", ":thumbsup:"]:
                if word in comment.comment:
                    votes[comment.user_id] = 1
                    break
            for word in ["-1", ":thumbsdown:"]:
                if word in comment.comment:
                    votes[comment.user_id] = -1
                    break

        return sum(votes.values())

    @property
    def threshold_reached(self):
        """ Return whether the pull-request has reached the threshold above
        which it is allowed to be merged, if the project requests a minimal
        score on pull-request, otherwise returns None.

        """
        threshold = self.project.settings.get(
            "Minimum_score_to_merge_pull-request", -1
        )
        if threshold is None or threshold < 0:
            return None
        else:
            return int(self.score) >= int(threshold)

    @property
    def remote(self):
        """ Return whether the current PullRequest is a remote pull-request
        or not.
        """
        return self.remote_git is not None

    @property
    def user_comments(self):
        """ Return user comments only, filter it from notifications
        """
        return [
            comment for comment in self.comments if not comment.notification
        ]

    def to_json(self, public=False, api=False, with_comments=True):
        """ Returns a dictionary representation of the pull-request.

        """
        output = {
            "id": self.id,
            "uid": self.uid,
            "title": self.title,
            "branch": self.branch,
            "project": self.project.to_json(public=public, api=api),
            "branch_from": self.branch_from,
            "repo_from": self.project_from.to_json(public=public, api=api)
            if self.project_from
            else None,
            "remote_git": self.remote_git,
            "date_created": arrow_ts(self.date_created),
            "updated_on": arrow_ts(self.updated_on),
            "last_updated": arrow_ts(self.last_updated),
            "closed_at": arrow_ts(self.closed_at) if self.closed_at else None,
            "user": self.user.to_json(public=public),
            "assignee": self.assignee.to_json(public=public)
            if self.assignee
            else None,
            "status": self.status,
            "commit_start": self.commit_start,
            "commit_stop": self.commit_stop,
            "closed_by": self.closed_by.to_json(public=public)
            if self.closed_by
            else None,
            "initial_comment": self.initial_comment,
            "cached_merge_status": self.merge_status or "unknown",
            "threshold_reached": self.threshold_reached,
            "tags": self.tags_text,
        }

        comments = []
        if with_comments:
            for comment in self.comments:
                comments.append(comment.to_json(public=public))

        output["comments"] = comments

        return output


class PullRequestComment(BASE):
    """ Stores the comments made on a pull-request.

    Table -- pull_request_comments
    """

    __tablename__ = "pull_request_comments"

    id = sa.Column(sa.Integer, primary_key=True)
    pull_request_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            "pull_requests.uid", ondelete="CASCADE", onupdate="CASCADE"
        ),
        nullable=False,
    )
    commit_id = sa.Column(sa.String(40), nullable=True, index=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    filename = sa.Column(sa.Text, nullable=True)
    line = sa.Column(sa.Integer, nullable=True)
    tree_id = sa.Column(sa.String(40), nullable=True)
    comment = sa.Column(sa.Text(), nullable=False)
    parent_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("pull_request_comments.id", onupdate="CASCADE"),
        nullable=True,
    )
    notification = sa.Column(sa.Boolean, default=False, nullable=False)
    edited_on = sa.Column(sa.DateTime, nullable=True)
    editor_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=True,
    )

    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref(
            "pull_request_comments",
            order_by=str("PullRequestComment.date_created"),
        ),
    )
    pull_request = relation(
        "PullRequest",
        backref=backref(
            "comments",
            cascade="delete, delete-orphan",
            order_by=str("PullRequestComment.date_created"),
        ),
        foreign_keys=[pull_request_uid],
        remote_side=[PullRequest.uid],
    )
    editor = relation("User", foreign_keys=[editor_id], remote_side=[User.id])

    _reactions = sa.Column(sa.Text, nullable=True)

    @property
    def mail_id(self):
        """ Return a unique representation of the issue as string that
        can be used when sending emails.
        """
        return "%s-pull-request-%s-%s" % (
            self.pull_request.project.name,
            self.pull_request.uid,
            self.id,
        )

    @property
    def parent(self):
        """ Return the parent, in this case the pull_request object. """
        return self.pull_request

    @property
    def reactions(self):
        """ Return the reactions stored as a string in the database parsed as
        an actual dict object.
        """
        if self._reactions:
            return json.loads(self._reactions)
        return {}

    @reactions.setter
    def reactions(self, reactions):
        """ Ensures that reactions are properly saved. """
        self._reactions = json.dumps(reactions)

    def to_json(self, public=False):
        """ Return a dict representation of the pull-request comment. """

        return {
            "id": self.id,
            "commit": self.commit_id,
            "tree": self.tree_id,
            "filename": self.filename,
            "line": self.line,
            "comment": self.comment,
            "parent": self.parent_id,
            "date_created": arrow_ts(self.date_created),
            "user": self.user.to_json(public=public),
            "edited_on": arrow_ts(self.edited_on) if self.edited_on else None,
            "editor": self.editor.to_json(public=public)
            if self.editor_id
            else None,
            "notification": self.notification,
            "reactions": self.reactions,
        }


class PullRequestFlag(BASE):
    """ Stores the flags attached to a pull-request.

    Table -- pull_request_flags
    """

    __tablename__ = "pull_request_flags"

    id = sa.Column(sa.Integer, primary_key=True)
    uid = sa.Column(sa.String(32), nullable=False)
    pull_request_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            "pull_requests.uid", ondelete="CASCADE", onupdate="CASCADE"
        ),
        nullable=False,
    )
    token_id = sa.Column(
        sa.String(64),
        sa.ForeignKey("tokens.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
    )
    status = sa.Column(sa.String(32), nullable=False)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    username = sa.Column(sa.Text(), nullable=False)
    percent = sa.Column(sa.Integer(), nullable=True)
    comment = sa.Column(sa.Text(), nullable=False)
    url = sa.Column(sa.Text(), nullable=False)

    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    date_updated = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    __table_args__ = (sa.UniqueConstraint("uid", "pull_request_uid"),)

    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref(
            "pull_request_flags", order_by=str("PullRequestFlag.date_created")
        ),
    )

    pull_request = relation(
        "PullRequest",
        backref=backref(
            "flags",
            order_by=str("(pull_request_flags.c.date_created).desc()"),
            cascade="delete, delete-orphan",
        ),
        foreign_keys=[pull_request_uid],
        remote_side=[PullRequest.uid],
    )

    @property
    def mail_id(self):
        """ Return a unique representation of the flag as string that
        can be used when sending emails.
        """
        return "%s-pull-request-%s-%s" % (
            self.pull_request.project.name,
            self.pull_request.uid,
            self.id,
        )

    def to_json(self, public=False):
        """ Returns a dictionary representation of the pull-request.

        """
        output = {
            "pull_request_uid": self.pull_request_uid,
            "username": self.username,
            "percent": self.percent,
            "comment": self.comment,
            "status": self.status,
            "url": self.url,
            "date_created": arrow_ts(self.date_created),
            "date_updated": arrow_ts(self.date_updated),
            "user": self.user.to_json(public=public),
        }

        return output


class CommitFlag(BASE):
    """ Stores the flags attached to a commit.

    Table -- commit_flags
    """

    __tablename__ = "commit_flags"

    id = sa.Column(sa.Integer, primary_key=True)
    commit_hash = sa.Column(sa.String(40), index=True, nullable=False)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_id = sa.Column(
        sa.String(64), sa.ForeignKey("tokens.id"), nullable=False
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    uid = sa.Column(sa.String(32), nullable=False)
    status = sa.Column(sa.String(32), nullable=False)
    username = sa.Column(sa.Text(), nullable=False)
    percent = sa.Column(sa.Integer(), nullable=True)
    comment = sa.Column(sa.Text(), nullable=False)
    url = sa.Column(sa.Text(), nullable=False)

    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    date_updated = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )

    __table_args__ = (sa.UniqueConstraint("commit_hash", "uid"),)

    project = relation(
        "Project",
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref("commit_flags", cascade="delete, delete-orphan"),
        single_parent=True,
    )

    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref(
            "commit_flags", order_by=str("CommitFlag.date_created")
        ),
    )

    @property
    def isa(self):
        """ A string to allow finding out that this is a commit flag. """
        return "commit-flag"

    @property
    def mail_id(self):
        """ Return a unique representation of the flag as string that
        can be used when sending emails.
        """
        return "%s-commit-%s-%s" % (
            self.project.name,
            self.project.id,
            self.id,
        )

    def to_json(self, public=False):
        """ Returns a dictionary representation of the commit flag.

        """
        output = {
            "commit_hash": self.commit_hash,
            "username": self.username,
            "percent": self.percent,
            "comment": self.comment,
            "status": self.status,
            "url": self.url,
            "date_created": arrow_ts(self.date_created),
            "date_updated": arrow_ts(self.date_updated),
            "user": self.user.to_json(public=public),
        }

        return output


class TagPullRequest(BASE):
    """ Stores the tag associated with an pull-request.

    Table -- tags_pull_requests
    """

    __tablename__ = "tags_pull_requests"

    tag_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            "tags_colored.id", ondelete="CASCADE", onupdate="CASCADE"
        ),
        primary_key=True,
    )
    request_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            "pull_requests.uid", ondelete="CASCADE", onupdate="CASCADE"
        ),
        primary_key=True,
    )
    date_created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    pull_request = relation(
        "PullRequest",
        foreign_keys=[request_uid],
        remote_side=[PullRequest.uid],
        backref=backref("tags_pr_colored", cascade="delete, delete-orphan"),
    )
    tag = relation(
        "TagColored", foreign_keys=[tag_id], remote_side=[TagColored.id]
    )

    def __repr__(self):
        return "TagPullRequest(PR:%s, tag:%s)" % (
            self.pull_request.id,
            self.tag,
        )


class PagureGroupType(BASE):
    """
    A list of the type a group can have definition.
    """

    # names like "Group", "Order" and "User" are reserved words in SQL
    # so we set the name to something safe for SQL
    __tablename__ = "pagure_group_type"

    group_type = sa.Column(sa.String(16), primary_key=True)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    def __repr__(self):
        """ Return a string representation of this object. """

        return "GroupType: %s" % (self.group_type)


class PagureGroup(BASE):
    """
    An ultra-simple group definition.
    """

    # names like "Group", "Order" and "User" are reserved words in SQL
    # so we set the name to something safe for SQL
    __tablename__ = "pagure_group"

    id = sa.Column(sa.Integer, primary_key=True)
    group_name = sa.Column(sa.String(255), nullable=False, unique=True)
    display_name = sa.Column(sa.String(255), nullable=False, unique=True)
    description = sa.Column(sa.String(255), nullable=True)
    group_type = sa.Column(
        sa.String(16),
        sa.ForeignKey("pagure_group_type.group_type"),
        default="user",
        nullable=False,
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    creator = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref("groups_created"),
    )

    def __repr__(self):
        """ Return a string representation of this object. """

        return "Group: %s - name %s" % (self.id, self.group_name)

    def to_json(self, public=False):
        """ Returns a dictionary representation of the pull-request.

        """
        output = {
            "name": self.group_name,
            "display_name": self.display_name,
            "description": self.description,
            "group_type": self.group_type,
            "creator": self.creator.to_json(public=public),
            "date_created": arrow_ts(self.created),
            "members": [user.username for user in self.users],
        }

        return output


class ProjectGroup(BASE):
    """
    Association table linking the projects table to the pagure_group table.
    This allow linking projects to groups.
    """

    __tablename__ = "projects_groups"

    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        primary_key=True,
    )
    group_id = sa.Column(
        sa.Integer, sa.ForeignKey("pagure_group.id"), primary_key=True
    )
    access = sa.Column(
        sa.String(255),
        sa.ForeignKey(
            "access_levels.access", onupdate="CASCADE", ondelete="CASCADE"
        ),
        nullable=False,
    )

    project = relation(
        "Project",
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref(
            "projects_groups",
            cascade="delete,delete-orphan",
            single_parent=True,
        ),
    )

    group = relation("PagureGroup", backref="projects_groups")

    # Constraints
    __table_args__ = (sa.UniqueConstraint("project_id", "group_id"),)


class Star(BASE):
    """ Stores users association with the all the projects which
    they have starred

    Table -- star
    """

    __tablename__ = "stargazers"
    __table_args__ = (
        sa.UniqueConstraint(
            "project_id",
            "user_id",
            name="uq_stargazers_project_id_user_id_key",
        ),
    )

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref("stars", cascade="delete, delete-orphan"),
    )
    project = relation(
        "Project",
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref("stargazers", cascade="delete, delete-orphan"),
    )


class Watcher(BASE):
    """ Stores the user of a projects.

    Table -- watchers
    """

    __tablename__ = "watchers"
    __table_args__ = (sa.UniqueConstraint("project_id", "user_id"),)

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE"),
        nullable=False,
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    watch_issues = sa.Column(sa.Boolean, nullable=False, default=False)
    watch_commits = sa.Column(sa.Boolean, nullable=False, default=False)

    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref("watchers", cascade="delete, delete-orphan"),
    )

    project = relation(
        "Project",
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref("watchers", cascade="delete, delete-orphan"),
    )


@six.python_2_unicode_compatible
class PagureLog(BASE):
    """
    Log user's actions.
    """

    __tablename__ = "pagure_logs"

    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_email = sa.Column(sa.String(255), nullable=True, index=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    issue_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey("issues.uid", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    pull_request_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            "pull_requests.uid", ondelete="CASCADE", onupdate="CASCADE"
        ),
        nullable=True,
        index=True,
    )
    log_type = sa.Column(sa.Text, nullable=False)
    ref_id = sa.Column(sa.Text, nullable=False)
    date = sa.Column(
        sa.Date, nullable=False, default=datetime.datetime.utcnow, index=True
    )
    date_created = sa.Column(
        sa.DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        index=True,
    )

    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref("logs", cascade="delete, delete-orphan"),
    )
    project = relation(
        "Project",
        foreign_keys=[project_id],
        remote_side=[Project.id],
        backref=backref("logs", cascade="delete, delete-orphan"),
    )
    issue = relation(
        "Issue", foreign_keys=[issue_uid], remote_side=[Issue.uid]
    )
    pull_request = relation(
        "PullRequest",
        foreign_keys=[pull_request_uid],
        remote_side=[PullRequest.uid],
    )

    def to_json(self, public=False):
        """ Returns a dictionary representation of the issue.

        """
        output = {
            "id": self.id,
            "type": self.log_type,
            "ref_id": self.ref_id,
            "date": self.date.strftime("%Y-%m-%d"),
            "date_created": arrow_ts(self.date_created),
            "user": self.user.to_json(public=public),
        }
        return output

    def __str__(self):
        """ A string representation of this log entry. """
        verb = ""
        desc = "%(user)s %(verb)s %(project)s#%(obj_id)s"
        arg = {
            "user": self.user.user if self.user else self.user_email,
            "obj_id": self.ref_id,
            "project": self.project.fullname,
        }

        issue_verb = {
            "created": "created issue",
            "commented": "commented on issue",
            "close": "closed issue",
            "open": "opened issue",
        }

        pr_verb = {
            "created": "created PR",
            "commented": "commented on PR",
            "closed": "closed PR",
            "merged": "merged PR",
        }

        if self.issue and self.log_type in issue_verb:
            verb = issue_verb[self.log_type]
        elif self.pull_request and self.log_type in pr_verb:
            verb = pr_verb[self.log_type]
        elif (
            not self.pull_request
            and not self.issue
            and self.log_type == "created"
        ):
            verb = "created Project"
            desc = "%(user)s %(verb)s %(project)s"
        elif self.log_type == "committed":
            verb = "committed on"

        arg["verb"] = verb

        return desc % arg

    def date_tz(self, tz="UTC"):
        """Returns the date (as a datetime.date()) of this log entry
        in a specified timezone (Olson name as a string). Assumes that
        date_created is aware, or UTC. If tz isn't a valid timezone
        identifier for arrow, just returns the date component of
        date_created.
        """
        try:
            return arrow.get(self.date_created).to(tz).date()
        except arrow.parser.ParserError:
            return self.date_created.date()


class IssueWatcher(BASE):
    """ Stores the users watching issues.

    Table -- issue_watchers
    """

    __tablename__ = "issue_watchers"
    __table_args__ = (sa.UniqueConstraint("issue_uid", "user_id"),)

    id = sa.Column(sa.Integer, primary_key=True)
    issue_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey("issues.uid", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    watch = sa.Column(sa.Boolean, nullable=False)

    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref("issue_watched", cascade="delete, delete-orphan"),
    )

    issue = relation(
        "Issue",
        foreign_keys=[issue_uid],
        remote_side=[Issue.uid],
        backref=backref("watchers", cascade="delete, delete-orphan"),
    )


class PullRequestWatcher(BASE):
    """ Stores the users watching issues.

    Table -- pull_request_watchers
    """

    __tablename__ = "pull_request_watchers"
    __table_args__ = (sa.UniqueConstraint("pull_request_uid", "user_id"),)

    id = sa.Column(sa.Integer, primary_key=True)
    pull_request_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            "pull_requests.uid", onupdate="CASCADE", ondelete="CASCADE"
        ),
        nullable=False,
    )
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    watch = sa.Column(sa.Boolean, nullable=False)

    user = relation(
        "User",
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref("pr_watched", cascade="delete, delete-orphan"),
    )

    pull_request = relation(
        "PullRequest",
        foreign_keys=[pull_request_uid],
        remote_side=[PullRequest.uid],
        backref=backref("watchers", cascade="delete, delete-orphan"),
    )


#
# Class and tables specific for the API/token access
#


class ACL(BASE):
    """
    Table listing all the rights a token can be given
    """

    __tablename__ = "acls"

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(32), unique=True, nullable=False)
    description = sa.Column(sa.Text(), nullable=False)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    def __repr__(self):
        """ Return a string representation of this object. """

        return "ACL: %s - name %s" % (self.id, self.name)


class Token(BASE):
    """
    Table listing all the tokens per user and per project
    """

    __tablename__ = "tokens"

    id = sa.Column(sa.String(64), primary_key=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("users.id", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey("projects.id", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )
    description = sa.Column(sa.Text(), nullable=True)
    expiration = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )

    acls = relation(
        "ACL",
        secondary="tokens_acls",
        primaryjoin="tokens.c.id==tokens_acls.c.token_id",
        secondaryjoin="acls.c.id==tokens_acls.c.acl_id",
    )

    user = relation(
        "User",
        backref=backref(
            "tokens",
            cascade="delete, delete-orphan",
            order_by=str("Token.created"),
        ),
        foreign_keys=[user_id],
        remote_side=[User.id],
    )

    project = relation(
        "Project",
        backref=backref("tokens", cascade="delete, delete-orphan"),
        foreign_keys=[project_id],
        remote_side=[Project.id],
    )

    def __repr__(self):
        """ Return a string representation of this object. """

        return "Token: %s - name %s - expiration: %s" % (
            self.id,
            self.description,
            self.expiration,
        )

    @property
    def expired(self):
        """ Returns whether a token has expired or not. """
        if datetime.datetime.utcnow().date() >= self.expiration.date():
            return True
        else:
            return False

    @property
    def acls_list(self):
        """ Return a list containing the name of each ACLs this token has.
        """
        return sorted(["%s" % acl.name for acl in self.acls])

    @property
    def acls_list_pretty(self):
        """
        Return a list containing the description of each ACLs this token has.
        """
        return [
            acl.description
            for acl in sorted(self.acls, key=operator.attrgetter("name"))
        ]


class TokenAcl(BASE):
    """
    Association table linking the tokens table to the acls table.
    This allow linking token to acl.
    """

    __tablename__ = "tokens_acls"

    token_id = sa.Column(
        sa.String(64), sa.ForeignKey("tokens.id"), primary_key=True
    )
    acl_id = sa.Column(sa.Integer, sa.ForeignKey("acls.id"), primary_key=True)

    # Constraints
    __table_args__ = (sa.UniqueConstraint("token_id", "acl_id"),)


# ##########################################################
# These classes are only used if you're using the `local`
#                  authentication method
# ##########################################################


class PagureUserVisit(BASE):
    """
    Table storing the visits of the user.
    """

    __tablename__ = "pagure_user_visit"

    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(sa.Integer, sa.ForeignKey("users.id"), nullable=False)
    visit_key = sa.Column(
        sa.String(40), nullable=False, unique=True, index=True
    )
    user_ip = sa.Column(sa.String(50), nullable=False)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow
    )
    expiry = sa.Column(sa.DateTime)


class PagureUserGroup(BASE):
    """
    Association table linking the mm_user table to the mm_group table.
    This allow linking users to groups.
    """

    __tablename__ = "pagure_user_group"

    user_id = sa.Column(
        sa.Integer, sa.ForeignKey("users.id"), primary_key=True
    )
    group_id = sa.Column(
        sa.Integer, sa.ForeignKey("pagure_group.id"), primary_key=True
    )

    # Constraints
    __table_args__ = (sa.UniqueConstraint("user_id", "group_id"),)


# Make sure to load the Plugin tables, so they have a chance to register
get_plugin_tables()
