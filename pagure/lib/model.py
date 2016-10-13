# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources

import datetime
import logging
import json
import operator

import sqlalchemy as sa

from sqlalchemy import create_engine, MetaData
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import relation


CONVENTION = {
    "ix": 'ix_%(table_name)s_%(column_0_label)s',
    # Checks are currently buggy and prevent us from naming them correctly
    #"ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "%(table_name)s_%(column_0_name)s_fkey",
    "pk": "%(table_name)s_pkey",
    "uq": "%(table_name)s_%(column_0_name)s_key",
}

BASE = declarative_base(metadata=MetaData(naming_convention=CONVENTION))

ERROR_LOG = logging.getLogger('pagure.model')

# hit w/ all the id field we use
# pylint: disable=invalid-name
# pylint: disable=too-few-public-methods
# pylint: disable=no-init
# pylint: disable=no-member
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
    :kwarg debug, a boolean specifying wether we should have the verbose
        output of sqlalchemy or not.
    :return a session that can be used to query the database.

    """
    if db_url.startswith('sqlite'):
        engine = create_engine(db_url, echo=debug)
    else:
        engine = create_engine(db_url, echo=debug, client_encoding='utf8')

    from pagure.lib.plugins import get_plugin_tables
    get_plugin_tables()
    BASE.metadata.create_all(engine)
    # engine.execute(collection_package_create_view(driver=engine.driver))
    if db_url.startswith('sqlite:'):
        # Ignore the warning about con_record
        # pylint: disable=unused-argument
        def _fk_pragma_on_connect(dbapi_con, _):  # pragma: no cover
            ''' Tries to enforce referential constraints on sqlite. '''
            dbapi_con.execute('pragma foreign_keys=ON')
        sa.event.listen(engine, 'connect', _fk_pragma_on_connect)

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

    statuses = ['Open', 'Closed']
    for status in statuses:
        ticket_stat = StatusIssue(status=status)
        session.add(ticket_stat)
        try:
            session.commit()
        except SQLAlchemyError:  # pragma: no cover
            session.rollback()
            ERROR_LOG.debug('Status %s could not be added', ticket_stat)

    for status in ['Open', 'Closed', 'Merged']:
        pr_stat = StatusPullRequest(status=status)
        session.add(pr_stat)
        try:
            session.commit()
        except SQLAlchemyError:  # pragma: no cover
            session.rollback()
            ERROR_LOG.debug('Status %s could not be added', pr_stat)

    for grptype in ['user', 'admin']:
        grp_type = PagureGroupType(group_type=grptype)
        session.add(grp_type)
        try:
            session.commit()
        except SQLAlchemyError:  # pragma: no cover
            session.rollback()
            ERROR_LOG.debug('Type %s could not be added', grptype)

    for acl in sorted(acls) or {}:
        item = ACL(
            name=acl,
            description=acls[acl]
        )
        session.add(item)
        try:
            session.commit()
        except SQLAlchemyError:  # pragma: no cover
            session.rollback()
            ERROR_LOG.debug('ACL %s could not be added', acl)


class StatusIssue(BASE):
    """ Stores the status a ticket can have.

    Table -- status_issue
    """
    __tablename__ = 'status_issue'

    id = sa.Column(sa.Integer, primary_key=True)
    status = sa.Column(sa.String(255), nullable=False, unique=True)


class StatusPullRequest(BASE):
    """ Stores the status a pull-request can have.

    Table -- status_issue
    """
    __tablename__ = 'status_pull_requests'

    id = sa.Column(sa.Integer, primary_key=True)
    status = sa.Column(sa.String(255), nullable=False, unique=True)


class User(BASE):
    """ Stores information about users.

    Table -- users
    """

    __tablename__ = 'users'
    id = sa.Column(sa.Integer, primary_key=True)
    user = sa.Column(sa.String(255), nullable=False, unique=True, index=True)
    fullname = sa.Column(sa.String(255), nullable=False, index=True)
    public_ssh_key = sa.Column(sa.Text, nullable=True)
    default_email = sa.Column(sa.Text, nullable=False)
    _settings = sa.Column(sa.Text, nullable=True)

    password = sa.Column(sa.Text, nullable=True)
    token = sa.Column(sa.String(50), nullable=True)
    created = sa.Column(
        sa.DateTime,
        nullable=False,
        default=sa.func.now())
    updated_on = sa.Column(
        sa.DateTime,
        nullable=False,
        default=sa.func.now(),
        onupdate=sa.func.now())

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
        ''' Return the username. '''
        return self.user

    @property
    def groups(self):
        ''' Return the list of Group.group_name in which the user is. '''
        return [group.group_name for group in self.group_objs]

    @property
    def settings(self):
        """ Return the dict stored as string in the database as an actual
        dict object.
        """
        default = {
            'cc_me_to_my_actions': False,
        }

        if self._settings:
            current = json.loads(self._settings)
            # Update the current dict with the new keys
            for key in default:
                if key not in current:
                    current[key] = default[key]
                elif str(current[key]).lower() in ['true', 'y']:
                    current[key] = True
            return current
        else:
            return default

    @settings.setter
    def settings(self, settings):
        ''' Ensures the settings are properly saved. '''
        self._settings = json.dumps(settings)

    def __repr__(self):
        ''' Return a string representation of this object. '''

        return 'User: %s - name %s' % (self.id, self.user)

    def to_json(self, public=False):
        ''' Return a representation of the User in a dictionnary. '''
        output = {
            'name': self.user,
            'fullname': self.fullname,
        }
        if not public:
            output['default_email'] = self.default_email
            output['emails'] = sorted([email.email for email in self.emails])

        return output


class UserEmail(BASE):
    """ Stores email information about the users.

    Table -- user_emails
    """

    __tablename__ = 'user_emails'
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=False,
        index=True)
    email = sa.Column(sa.String(255), nullable=False, unique=True)

    user = relation(
        'User', foreign_keys=[user_id], remote_side=[User.id],
        backref=backref(
            'emails', cascade="delete, delete-orphan", single_parent=True
        )
    )


class UserEmailPending(BASE):
    """ Stores email information about the users.

    Table -- user_emails_pending
    """

    __tablename__ = 'user_emails_pending'
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=False,
        index=True)
    email = sa.Column(sa.String(255), nullable=False, unique=True)
    token = sa.Column(sa.String(50), nullable=True)
    created = sa.Column(
        sa.DateTime,
        nullable=False,
        default=sa.func.now())

    user = relation(
        'User', foreign_keys=[user_id], remote_side=[User.id],
        backref=backref(
            'emails_pending',
            cascade="delete, delete-orphan",
            single_parent=True
        )
    )


class Project(BASE):
    """ Stores the projects.

    Table -- projects
    """

    __tablename__ = 'projects'

    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=False,
        index=True)
    namespace = sa.Column(sa.String(255), nullable=True, index=True)
    name = sa.Column(sa.String(255), nullable=False, index=True)
    description = sa.Column(sa.Text, nullable=True)
    url = sa.Column(sa.Text, nullable=True)
    _settings = sa.Column(sa.Text, nullable=True)
    # The hook_token is used to sign the notification sent via web-hook
    hook_token = sa.Column(sa.String(40), nullable=False, unique=True)
    avatar_email = sa.Column(sa.Text, nullable=True)
    is_fork = sa.Column(sa.Boolean, default=False, nullable=False)
    parent_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE',
        ),
        nullable=True)
    _priorities = sa.Column(sa.Text, nullable=True)
    _milestones = sa.Column(sa.Text, nullable=True)
    _reports = sa.Column(sa.Text, nullable=True)
    _notifications = sa.Column(sa.Text, nullable=True)
    _close_status = sa.Column(sa.Text, nullable=True)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    parent = relation('Project', remote_side=[id], backref='forks')
    user = relation('User', foreign_keys=[user_id],
                    remote_side=[User.id], backref='projects')

    users = relation(
        'User',
        secondary="user_projects",
        primaryjoin="projects.c.id==user_projects.c.project_id",
        secondaryjoin="users.c.id==user_projects.c.user_id",
        backref='co_projects'
    )

    groups = relation(
        "PagureGroup",
        secondary="projects_groups",
        primaryjoin="projects.c.id==projects_groups.c.project_id",
        secondaryjoin="pagure_group.c.id==projects_groups.c.group_id",
        backref="projects",
    )

    unwatchers = relation(
        "Watcher",
        primaryjoin="and_(Project.id==Watcher.project_id, "
        "Watcher.watch=='0')"
    )

    @property
    def path(self):
        ''' Return the name of the git repo on the filesystem. '''
        return '%s.git' % self.fullname

    @property
    def fullname(self):
        ''' Return the name of the git repo as user/project if it is a
        project forked, otherwise it returns the project name.
        '''
        str_name = self.name
        if self.namespace:
            str_name = '%s/%s' % (self.namespace, str_name)
        if self.is_fork:
            str_name = "forks/%s/%s" % (self.user.user, str_name)
        return str_name

    @property
    def tags_text(self):
        ''' Return the list of tags in a simple text form. '''
        return [tag.tag for tag in self.tags]

    @property
    def settings(self):
        """ Return the dict stored as string in the database as an actual
        dict object.
        """
        default = {
            'issue_tracker': True,
            'project_documentation': False,
            'pull_requests': True,
            'Only_assignee_can_merge_pull-request': False,
            'Minimum_score_to_merge_pull-request': -1,
            'Web-hooks': None,
            'Enforce_signed-off_commits_in_pull-request': False,
            'always_merge': False,
            'issues_default_to_private': False,
            'fedmsg_notifications': True,
        }

        if self._settings:
            current = json.loads(self._settings)
            # Update the current dict with the new keys
            for key in default:
                if key not in current:
                    current[key] = default[key]
                elif key == 'Minimum_score_to_merge_pull-request':
                    current[key] = int(current[key])
                elif str(current[key]).lower() in ['true', 'y']:
                    current[key] = True
            return current
        else:
            return default

    @settings.setter
    def settings(self, settings):
        ''' Ensures the settings are properly saved. '''
        self._settings = json.dumps(settings)

    @property
    def milestones(self):
        """ Return the dict stored as string in the database as an actual
        dict object.
        """
        milestones = {}

        if self._milestones:
            milestones = json.loads(self._milestones)

        return milestones

    @milestones.setter
    def milestones(self, milestones):
        ''' Ensures the milestones are properly saved. '''
        self._milestones = json.dumps(milestones)

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
        ''' Ensures the priorities are properly saved. '''
        self._priorities = json.dumps(priorities)

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
        ''' Ensures the notifications are properly saved. '''
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
        ''' Ensures the reports are properly saved. '''
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
        ''' Ensures the different close status are properly saved. '''
        self._close_status = json.dumps(close_status)

    @property
    def open_requests(self):
        ''' Returns the number of open pull-requests for this project. '''
        return BASE.metadata.bind.query(
            PullRequest
        ).filter(
            self.id == PullRequest.project_id
        ).filter(
            PullRequest.status == 'Open'
        ).count()

    @property
    def open_tickets(self):
        ''' Returns the number of open tickets for this project. '''
        return BASE.metadata.bind.query(
            Issue
        ).filter(
            self.id == Issue.project_id
        ).filter(
            Issue.status == 'Open'
        ).count()

    @property
    def open_tickets_public(self):
        ''' Returns the number of open tickets for this project. '''
        return BASE.metadata.bind.query(
            Issue
        ).filter(
            self.id == Issue.project_id
        ).filter(
            Issue.status == 'Open'
        ).filter(
            Issue.private == False
        ).count()

    def to_json(self, public=False, api=False):
        ''' Return a representation of the project as JSON.
        '''

        output = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'namespace': self.namespace,
            'parent': self.parent.to_json(
                public=public, api=api) if self.parent else None,
            'date_created': self.date_created.strftime('%s'),
            'user': self.user.to_json(public=public),
            'tags': self.tags_text,
            'priorities': self.priorities,
        }
        if not api:
            output['settings'] = self.settings

        return output


class ProjectUser(BASE):
    """ Stores the user of a projects.

    Table -- user_projects
    """

    __tablename__ = 'user_projects'
    __table_args__ = (
        sa.UniqueConstraint('project_id', 'user_id'),
    )

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE',
        ),
        nullable=False)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=False,
        index=True)


class Issue(BASE):
    """ Stores the issues reported on a project.

    Table -- issues
    """

    __tablename__ = 'issues'

    id = sa.Column(sa.Integer, primary_key=True)
    uid = sa.Column(sa.String(32), unique=True, nullable=False)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE',
        ),
        primary_key=True)
    title = sa.Column(
        sa.Text,
        nullable=False)
    content = sa.Column(
        sa.Text(),
        nullable=False)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=False,
        index=True)
    assignee_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=True,
        index=True)
    status = sa.Column(
        sa.String(255),
        sa.ForeignKey(
            'status_issue.status', onupdate='CASCADE',
        ),
        default='Open',
        nullable=False)
    private = sa.Column(sa.Boolean, nullable=False, default=False)
    priority = sa.Column(sa.Integer, nullable=True, default=None)
    milestone = sa.Column(sa.String(255), nullable=True, default=None)
    close_status = sa.Column(sa.Text, nullable=True)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    closed_at = sa.Column(sa.DateTime, nullable=True)

    project = relation(
        'Project', foreign_keys=[project_id], remote_side=[Project.id],
        backref=backref(
            'issues', cascade="delete, delete-orphan", single_parent=True)
        )

    user = relation('User', foreign_keys=[user_id],
                    remote_side=[User.id], backref='issues')
    assignee = relation('User', foreign_keys=[assignee_id],
                        remote_side=[User.id], backref='assigned_issues')

    parents = relation(
        "Issue",
        secondary="issue_to_issue",
        primaryjoin="issues.c.uid==issue_to_issue.c.child_issue_id",
        secondaryjoin="issue_to_issue.c.parent_issue_id==issues.c.uid",
        backref="children",
    )

    def __repr__(self):
        return 'Issue(%s, project:%s, user:%s, title:%s)' % (
            self.id, self.project.name, self.user.user, self.title
        )

    @property
    def isa(self):
        ''' A string to allow finding out that this is an issue. '''
        return 'issue'

    @property
    def mail_id(self):
        ''' Return a unique reprensetation of the issue as string that
        can be used when sending emails.
        '''
        return '%s-ticket-%s@pagure' % (self.project.name, self.uid)

    @property
    def tags_text(self):
        ''' Return the list of tags in a simple text form. '''
        return [tag.tag for tag in self.tags]

    @property
    def depends_text(self):
        ''' Return the list of issue this issue depends on in simple text. '''
        return [issue.id for issue in self.children]

    @property
    def blocks_text(self):
        ''' Return the list of issue this issue blocks on in simple text. '''
        return [issue.id for issue in self.parents]

    @property
    def user_comments(self):
        ''' Return user comments only, filter it from notifications
        '''
        return [
            comment
            for comment in self.comments
            if not comment.notification]

    def to_json(self, public=False, with_comments=True):
        ''' Returns a dictionary representation of the issue.

        '''
        output = {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'status': self.status,
            'date_created': self.date_created.strftime('%s'),
            'closed_at': self.closed_at.strftime(
                '%s') if self.closed_at else None,
            'user': self.user.to_json(public=public),
            'private': self.private,
            'tags': self.tags_text,
            'depends': [str(item) for item in self.depends_text],
            'blocks': [str(item) for item in self.blocks_text],
            'assignee': self.assignee.to_json(
                public=public) if self.assignee else None,
            'priority': self.priority,
            'milestone': self.milestone,
        }

        comments = []
        if with_comments:
            for comment in self.comments:
                comments.append(comment.to_json(public=public))

        output['comments'] = comments

        return output


class IssueToIssue(BASE):
    """ Stores the parent/child relationship between two issues.

    Table -- issue_to_issue
    """

    __tablename__ = 'issue_to_issue'

    parent_issue_id = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            'issues.uid', ondelete='CASCADE', onupdate='CASCADE',
        ),
        primary_key=True)
    child_issue_id = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            'issues.uid', ondelete='CASCADE', onupdate='CASCADE',
        ),
        primary_key=True)


class IssueComment(BASE):
    """ Stores the comments made on a commit/file.

    Table -- issue_comments
    """

    __tablename__ = 'issue_comments'

    id = sa.Column(sa.Integer, primary_key=True)
    issue_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            'issues.uid', ondelete='CASCADE', onupdate='CASCADE',
        ),
        index=True)
    comment = sa.Column(
        sa.Text(),
        nullable=False)
    parent_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'issue_comments.id', onupdate='CASCADE',
        ),
        nullable=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=False,
        index=True)

    notification = sa.Column(sa.Boolean, default=False, nullable=False)
    edited_on = sa.Column(sa.DateTime, nullable=True)
    editor_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=True)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    issue = relation(
        'Issue', foreign_keys=[issue_uid], remote_side=[Issue.uid],
        backref=backref(
            'comments', cascade="delete, delete-orphan",
            order_by="IssueComment.date_created"
        ),
    )
    user = relation(
        'User',
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref='comment_issues')
    editor = relation(
        'User',
        foreign_keys=[editor_id],
        remote_side=[User.id])

    @property
    def mail_id(self):
        ''' Return a unique reprensetation of the issue as string that
        can be used when sending emails.
        '''
        return '%s-ticket-%s-%s@pagure' % (
            self.issue.project.name, self.issue.uid, self.id)

    @property
    def parent(self):
        ''' Return the parent, in this case the issue object. '''
        return self.issue

    def to_json(self, public=False):
        ''' Returns a dictionary representation of the issue.

        '''
        output = {
            'id': self.id,
            'comment': self.comment,
            'parent': self.parent_id,
            'date_created': self.date_created.strftime('%s'),
            'user': self.user.to_json(public=public),
            'edited_on': self.edited_on.strftime('%s')
            if self.edited_on else None,
            'editor': self.editor.to_json(public=public)
            if self.editor_id else None,
            'notification': self.notification,
        }
        return output


class IssueKeys(BASE):
    """ Stores the custom keys a project can use on issues.

    Table -- issue_keys
    """

    __tablename__ = 'issue_keys'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE', ondelete='CASCADE',
        ),
        nullable=False)
    name = sa.Column(sa.Text(), nullable=False)
    key_type = sa.Column(sa.String(255), nullable=False)

    __table_args__ = (sa.UniqueConstraint('project_id', 'name'),)

    project = relation(
        'Project', foreign_keys=[project_id], remote_side=[Project.id],
        backref=backref(
            'issue_keys', cascade="delete, delete-orphan", single_parent=True)
        )


class IssueValues(BASE):
    """ Stores the values of the custom keys set by project on issues.

    Table -- issue_values
    """

    __tablename__ = 'issue_values'

    key_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'issue_keys.id', ondelete='CASCADE', onupdate='CASCADE',
        ),
        primary_key=True)
    issue_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            'issues.uid', ondelete='CASCADE', onupdate='CASCADE',
        ),
        primary_key=True)
    value = sa.Column(sa.Text(), nullable=False)

    issue = relation(
        'Issue', foreign_keys=[issue_uid], remote_side=[Issue.uid],
        backref=backref(
            'other_fields', cascade="delete, delete-orphan", single_parent=True)
        )

    key = relation(
        'IssueKeys', foreign_keys=[key_id], remote_side=[IssueKeys.id],
        backref=backref('values', cascade="delete, delete-orphan")
        )


class Tag(BASE):
    """ Stores the tags.

    Table -- tags
    """

    __tablename__ = 'tags'

    tag = sa.Column(sa.String(255), primary_key=True)
    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)


class TagIssue(BASE):
    """ Stores the tag associated with an issue.

    Table -- tags_issues
    """

    __tablename__ = 'tags_issues'

    tag = sa.Column(
        sa.String(255),
        sa.ForeignKey(
            'tags.tag', ondelete='CASCADE', onupdate='CASCADE',
        ),
        primary_key=True)
    issue_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            'issues.uid', ondelete='CASCADE', onupdate='CASCADE',
        ),
        primary_key=True)
    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    issue = relation(
        'Issue', foreign_keys=[issue_uid], remote_side=[Issue.uid],
        backref=backref(
            'tags', cascade="delete, delete-orphan", single_parent=True)
        )

    def __repr__(self):
        return 'TagIssue(issue:%s, tag:%s)' % (self.issue.id, self.tag)


class TagProject(BASE):
    """ Stores the tag associated with a project.

    Table -- tags_projects
    """

    __tablename__ = 'tags_projects'

    tag = sa.Column(
        sa.String(255),
        sa.ForeignKey(
            'tags.tag', ondelete='CASCADE', onupdate='CASCADE',
        ),
        primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', ondelete='CASCADE', onupdate='CASCADE',
        ),
        primary_key=True)
    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    project = relation(
        'Project', foreign_keys=[project_id], remote_side=[Project.id],
        backref=backref(
            'tags', cascade="delete, delete-orphan", single_parent=True)
        )

    def __repr__(self):
        return 'TagProject(project:%s, tag:%s)' % (
            self.project.fullname, self.tag)


class PullRequest(BASE):
    """ Stores the pull requests created on a project.

    Table -- pull_requests
    """

    __tablename__ = 'pull_requests'

    id = sa.Column(sa.Integer, primary_key=True)
    uid = sa.Column(sa.String(32), unique=True, nullable=False)
    title = sa.Column(
        sa.Text,
        nullable=False)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', ondelete='CASCADE', onupdate='CASCADE',
        ),
        primary_key=True)
    branch = sa.Column(
        sa.Text(),
        nullable=False)
    project_id_from = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', ondelete='CASCADE', onupdate='CASCADE',
        ),
        nullable=True)
    remote_git = sa.Column(
        sa.Text(),
        nullable=True)
    branch_from = sa.Column(
        sa.Text(),
        nullable=False)
    commit_start = sa.Column(
        sa.Text(),
        nullable=True)
    commit_stop = sa.Column(
        sa.Text(),
        nullable=True)
    initial_comment = sa.Column(
        sa.Text(),
        nullable=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=False,
        index=True)
    assignee_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=True,
        index=True)
    merge_status = sa.Column(
        sa.Enum(
            'NO_CHANGE', 'FFORWARD', 'CONFLICTS', 'MERGE',
            name='merge_status_enum',
        ),
        nullable=True)

    status = sa.Column(
        sa.String(255),
        sa.ForeignKey(
            'status_pull_requests.status', onupdate='CASCADE',
        ),
        default='Open',
        nullable=False)
    closed_by_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=True)
    closed_at = sa.Column(
        sa.DateTime,
        nullable=True)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)
    updated_on = sa.Column(
        sa.DateTime,
        nullable=False,
        default=sa.func.now(),
        onupdate=sa.func.now())

    __table_args__ = (
        sa.CheckConstraint(
            'NOT(project_id_from IS NULL AND remote_git IS NULL)',
        ),
    )

    project = relation(
        'Project', foreign_keys=[project_id], remote_side=[Project.id],
        backref=backref(
            'requests', cascade="delete, delete-orphan",
        ),
        single_parent=True)
    project_from = relation(
        'Project', foreign_keys=[project_id_from], remote_side=[Project.id])

    user = relation('User', foreign_keys=[user_id],
                    remote_side=[User.id], backref='pull_requests')
    assignee = relation('User', foreign_keys=[assignee_id],
                        remote_side=[User.id], backref='assigned_requests')
    closed_by = relation('User', foreign_keys=[closed_by_id],
                         remote_side=[User.id], backref='closed_requests')

    def __repr__(self):
        return 'PullRequest(%s, project:%s, user:%s, title:%s)' % (
            self.id, self.project.name, self.user.user, self.title
        )

    @property
    def isa(self):
        ''' A string to allow finding out that this is an pull-request. '''
        return 'pull-request'

    @property
    def mail_id(self):
        ''' Return a unique reprensetation of the issue as string that
        can be used when sending emails.
        '''
        return '%s-pull-request-%s@pagure' % (self.project.name, self.uid)

    @property
    def discussion(self):
        ''' Return the list of comments related to the pull-request itself,
        ie: not related to a specific commit.
        '''
        return [
            comment
            for comment in self.comments
            if not comment.commit_id
        ]

    @property
    def score(self):
        ''' Return the review score of the pull-request by checking the
        number of +1, -1, :thumbup: and :thumbdown: in the comment of the
        pull-request.
        This includes only the main comments not the inline ones.

        An user can only give one +1 and one -1.
        '''
        positive = set()
        negative = set()
        for comment in self.discussion:
            for word in ['+1', ':thumbsup:']:
                if word in comment.comment:
                    positive.add(comment.user_id)
                    break
            for word in ['-1', ':thumbsdown:']:
                if word in comment.comment:
                    negative.add(comment.user_id)
                    break

        return len(positive) - len(negative)

    @property
    def remote(self):
        ''' Return whether the current PullRequest is a remote pull-request
        or not.
        '''
        return self.remote_git is not None

    @property
    def user_comments(self):
        ''' Return user comments only, filter it from notifications
        '''
        return [
            comment
            for comment in self.comments
            if not comment.notification]

    def to_json(self, public=False, api=False, with_comments=True):
        ''' Returns a dictionnary representation of the pull-request.

        '''
        output = {
            'id': self.id,
            'uid': self.uid,
            'title': self.title,
            'branch': self.branch,
            'project': self.project.to_json(public=public, api=api),
            'branch_from': self.branch_from,
            'repo_from': self.project_from.to_json(
                public=public, api=api) if self.project_from else None,
            'remote_git': self.remote_git,
            'date_created': self.date_created.strftime('%s'),
            'updated_on': self.updated_on.strftime('%s'),
            'closed_at': self.closed_at.strftime(
                '%s') if self.closed_at else None,
            'user': self.user.to_json(public=public),
            'assignee': self.assignee.to_json(
                public=public) if self.assignee else None,
            'status': self.status,
            'commit_start': self.commit_start,
            'commit_stop': self.commit_stop,
            'closed_by': self.closed_by.to_json(
                public=public) if self.closed_by else None,
            'initial_comment': self.initial_comment,
        }

        comments = []
        if with_comments:
            for comment in self.comments:
                comments.append(comment.to_json(public=public))

        output['comments'] = comments

        return output


class PullRequestComment(BASE):
    """ Stores the comments made on a pull-request.

    Table -- pull_request_comments
    """

    __tablename__ = 'pull_request_comments'

    id = sa.Column(sa.Integer, primary_key=True)
    pull_request_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            'pull_requests.uid', ondelete='CASCADE', onupdate='CASCADE',
        ),
        nullable=False)
    commit_id = sa.Column(
        sa.String(40),
        nullable=True,
        index=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=False,
        index=True)
    filename = sa.Column(
        sa.Text,
        nullable=True)
    line = sa.Column(
        sa.Integer,
        nullable=True)
    tree_id = sa.Column(
        sa.String(40),
        nullable=True)
    comment = sa.Column(
        sa.Text(),
        nullable=False)
    parent_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'pull_request_comments.id', onupdate='CASCADE',
        ),
        nullable=True)
    notification = sa.Column(sa.Boolean, default=False, nullable=False)
    edited_on = sa.Column(sa.DateTime, nullable=True)
    editor_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('users.id', onupdate='CASCADE'),
        nullable=True)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    user = relation('User', foreign_keys=[user_id],
                    remote_side=[User.id],
                    backref=backref(
                        'pull_request_comments',
                        order_by="PullRequestComment.date_created"))
    pull_request = relation(
        'PullRequest',
        backref=backref(
            'comments',
            cascade="delete, delete-orphan",
            order_by="PullRequestComment.date_created"
        ),
        foreign_keys=[pull_request_uid],
        remote_side=[PullRequest.uid])
    editor = relation(
        'User',
        foreign_keys=[editor_id],
        remote_side=[User.id])

    @property
    def mail_id(self):
        ''' Return a unique reprensetation of the issue as string that
        can be used when sending emails.
        '''
        return '%s-pull-request-%s-%s@pagure' % (
            self.pull_request.project.name, self.pull_request.uid, self.id)

    @property
    def parent(self):
        ''' Return the parent, in this case the pull_request object. '''
        return self.pull_request

    def to_json(self, public=False):
        ''' Return a dict representation of the pull-request comment. '''

        return {
            'id': self.id,
            'commit': self.commit_id,
            'tree': self.tree_id,
            'filename': self.filename,
            'line': self.line,
            'comment': self.comment,
            'parent': self.parent_id,
            'date_created': self.date_created.strftime('%s'),
            'user': self.user.to_json(public=public),
            'edited_on': self.edited_on.strftime('%s')
            if self.edited_on else None,
            'editor': self.editor.to_json(public=public)
            if self.editor_id else None,
            'notification': self.notification,
        }


class PullRequestFlag(BASE):
    """ Stores the flags attached to a pull-request.

    Table -- pull_request_flags
    """

    __tablename__ = 'pull_request_flags'

    id = sa.Column(sa.Integer, primary_key=True)
    uid = sa.Column(sa.String(32), unique=True, nullable=False)
    pull_request_uid = sa.Column(
        sa.String(32),
        sa.ForeignKey(
            'pull_requests.uid', ondelete='CASCADE', onupdate='CASCADE',
        ),
        nullable=False)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=False,
        index=True)
    username = sa.Column(
        sa.Text(),
        nullable=False)
    percent = sa.Column(
        sa.Integer(),
        nullable=False)
    comment = sa.Column(
        sa.Text(),
        nullable=False)
    url = sa.Column(
        sa.Text(),
        nullable=False)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    user = relation('User', foreign_keys=[user_id],
                    remote_side=[User.id],
                    backref=backref(
                        'pull_request_flags',
                        order_by="PullRequestFlag.date_created"))

    pull_request = relation(
        'PullRequest',
        backref=backref(
            'flags', cascade="delete, delete-orphan",
        ),
        foreign_keys=[pull_request_uid],
        remote_side=[PullRequest.uid])

    def to_json(self, public=False):
        ''' Returns a dictionnary representation of the pull-request.

        '''
        output = {
            'uid': self.uid,
            'pull_request_uid': self.pull_request_uid,
            'username': self.username,
            'percent': self.percent,
            'comment': self.comment,
            'url': self.url,
            'date_created': self.date_created.strftime('%s'),
            'user': self.user.to_json(public=public),
        }

        return output


class PagureGroupType(BASE):
    """
    A list of the type a group can have definition.
    """

    # names like "Group", "Order" and "User" are reserved words in SQL
    # so we set the name to something safe for SQL
    __tablename__ = 'pagure_group_type'

    group_type = sa.Column(sa.String(16), primary_key=True)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def __repr__(self):
        ''' Return a string representation of this object. '''

        return 'GroupType: %s' % (self.group_type)


class PagureGroup(BASE):
    """
    An ultra-simple group definition.
    """

    # names like "Group", "Order" and "User" are reserved words in SQL
    # so we set the name to something safe for SQL
    __tablename__ = 'pagure_group'

    id = sa.Column(sa.Integer, primary_key=True)
    group_name = sa.Column(sa.String(16), nullable=False, unique=True)
    display_name = sa.Column(sa.String(255), nullable=False, unique=True)
    description = sa.Column(sa.String(255), nullable=True)
    group_type = sa.Column(
        sa.String(16),
        sa.ForeignKey(
            'pagure_group_type.group_type',
        ),
        default='user',
        nullable=False)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=False,
        index=True)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow)

    creator = relation(
        'User',
        foreign_keys=[user_id],
        remote_side=[User.id],
        backref=backref('groups_created')
    )

    def __repr__(self):
        ''' Return a string representation of this object. '''

        return 'Group: %s - name %s' % (self.id, self.group_name)

    def to_json(self, public=False):
        ''' Returns a dictionnary representation of the pull-request.

        '''
        output = {
            'name': self.group_name,
            'display_name': self.display_name,
            'description': self.description,
            'group_type': self.group_type,
            'creator': self.creator.to_json(public=public),
            'date_created': self.created.strftime('%s'),
        }

        return output


class ProjectGroup(BASE):
    """
    Association table linking the projects table to the pagure_group table.
    This allow linking projects to groups.
    """

    __tablename__ = 'projects_groups'

    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE', ondelete='CASCADE',
        ),
        primary_key=True)
    group_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'pagure_group.id',
        ),
        primary_key=True)

    # Constraints
    __table_args__ = (sa.UniqueConstraint('project_id', 'group_id'),)


class Watcher(BASE):
    """ Stores the user of a projects.

    Table -- watchers
    """

    __tablename__ = 'watchers'
    __table_args__ = (
        sa.UniqueConstraint('project_id', 'user_id'),
    )

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=False)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('users.id', onupdate='CASCADE'),
        nullable=False,
        index=True)
    watch = sa.Column(
        sa.Boolean,
        nullable=False)

    user = relation(
        'User', foreign_keys=[user_id], remote_side=[User.id],
        backref=backref(
            'watchers', cascade="delete, delete-orphan"
        ),
    )

    project = relation(
        'Project', foreign_keys=[project_id], remote_side=[Project.id],
        backref=backref(
            'watchers', cascade="delete, delete-orphan",
        ),
    )

#
# Class and tables specific for the API/token access
#


class ACL(BASE):
    """
    Table listing all the rights a token can be given
    """

    __tablename__ = 'acls'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(32), unique=True, nullable=False)
    description = sa.Column(sa.Text(), nullable=False)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def __repr__(self):
        ''' Return a string representation of this object. '''

        return 'ACL: %s - name %s' % (self.id, self.name)


class Token(BASE):
    """
    Table listing all the tokens per user and per project
    """

    __tablename__ = 'tokens'

    id = sa.Column(sa.String(64), primary_key=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'users.id', onupdate='CASCADE',
        ),
        nullable=False,
        index=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', onupdate='CASCADE',
        ),
        nullable=False,
        index=True)
    expiration = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow)

    acls = relation(
        "ACL",
        secondary="tokens_acls",
        primaryjoin="tokens.c.id==tokens_acls.c.token_id",
        secondaryjoin="acls.c.id==tokens_acls.c.acl_id",
    )

    user = relation(
        'User',
        backref=backref(
            'tokens', cascade="delete, delete-orphan",
            order_by="Token.created"
        ),
        foreign_keys=[user_id],
        remote_side=[User.id])

    project = relation(
        'Project',
        backref=backref(
            'tokens', cascade="delete, delete-orphan",
        ),
        foreign_keys=[project_id],
        remote_side=[Project.id])

    def __repr__(self):
        ''' Return a string representation of this object. '''

        return 'Token: %s - name %s' % (self.id, self.expiration)

    @property
    def expired(self):
        ''' Returns wether a token has expired or not. '''
        if datetime.datetime.utcnow().date() >= self.expiration.date():
            return True
        else:
            return False

    @property
    def acls_list(self):
        ''' Return a list containing the name of each ACLs this token has.
        '''
        return sorted([str(acl.name) for acl in self.acls])

    @property
    def acls_list_pretty(self):
        '''
        Return a list containing the description of each ACLs this token has.
        '''
        return [acl.description for acl in sorted(
            self.acls, key=operator.attrgetter('name'))]


class TokenAcl(BASE):
    """
    Association table linking the tokens table to the acls table.
    This allow linking token to acl.
    """

    __tablename__ = 'tokens_acls'

    token_id = sa.Column(
        sa.String(64), sa.ForeignKey(
            'tokens.id',
        ),
        primary_key=True)
    acl_id = sa.Column(
        sa.Integer, sa.ForeignKey(
            'acls.id',
        ),
        primary_key=True)

    # Constraints
    __table_args__ = (
        sa.UniqueConstraint(
            'token_id', 'acl_id'),
    )


# ##########################################################
# These classes are only used if you're using the `local`
#                  authentication method
# ##########################################################


class PagureUserVisit(BASE):
    """
    Table storing the visits of the user.
    """

    __tablename__ = 'pagure_user_visit'

    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.Integer, sa.ForeignKey(
            'users.id',
        ),
        nullable=False)
    visit_key = sa.Column(
        sa.String(40), nullable=False, unique=True, index=True)
    user_ip = sa.Column(sa.String(50), nullable=False)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow)
    expiry = sa.Column(sa.DateTime)


class PagureUserGroup(BASE):
    """
    Association table linking the mm_user table to the mm_group table.
    This allow linking users to groups.
    """

    __tablename__ = 'pagure_user_group'

    user_id = sa.Column(
        sa.Integer, sa.ForeignKey(
            'users.id',
        ),
        primary_key=True)
    group_id = sa.Column(
        sa.Integer, sa.ForeignKey(
            'pagure_group.id',
        ),
        primary_key=True)

    # Constraints
    __table_args__ = (
        sa.UniqueConstraint(
            'user_id', 'group_id'),
    )
