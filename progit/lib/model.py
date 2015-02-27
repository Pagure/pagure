#-*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.8', 'jinja2 >= 2.4']
import pkg_resources

import datetime
import logging
import json

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import relation

BASE = declarative_base()

ERROR_LOG = logging.getLogger('progit.model')


def create_tables(db_url, alembic_ini=None, debug=False):
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
    engine = create_engine(db_url, echo=debug)
    from progit.ui.plugins import get_plugin_tables
    get_plugin_tables()
    BASE.metadata.create_all(engine)
    #engine.execute(collection_package_create_view(driver=engine.driver))
    if db_url.startswith('sqlite:'):
        ## Ignore the warning about con_record
        # pylint: disable=W0613
        def _fk_pragma_on_connect(dbapi_con, con_record):
            ''' Tries to enforce referential constraints on sqlite. '''
            dbapi_con.execute('pragma foreign_keys=ON')
        sa.event.listen(engine, 'connect', _fk_pragma_on_connect)

    if alembic_ini is not None:  # pragma: no cover
        # then, load the Alembic configuration and generate the
        # version table, "stamping" it with the most recent rev:

        ## Ignore the warning missing alembic
        # pylint: disable=F0401
        from alembic.config import Config
        from alembic import command
        alembic_cfg = Config(alembic_ini)
        command.stamp(alembic_cfg, "head")

    scopedsession = scoped_session(sessionmaker(bind=engine))
    # Insert the default data into the db
    try:
        create_default_status(scopedsession)
    except SQLAlchemyError:
        pass
    return scopedsession


def create_default_status(session):
    """ Insert the defaults status in the status tables.
    """

    for status in ['Open', 'Invalid', 'Insufficient data', 'Fixed']:
        ticket_stat = StatusIssue(status=status)
        session.add(ticket_stat)
        try:
            session.flush()
        except SQLAlchemyError, err:
            ERROR_LOG.debug('Status %s could not be added', ticket_stat)

    session.commit()


class StatusIssue(BASE):
    """ Stores the status a ticket can have.

    Table -- status_issue
    """
    __tablename__ = 'status_issue'

    id = sa.Column(sa.Integer, primary_key=True)
    status = sa.Column(sa.Text, nullable=False, unique=True)


class User(BASE):
    """ Stores information about users.

    Table -- users
    """

    __tablename__ = 'users'
    id = sa.Column(sa.Integer, primary_key=True)
    user = sa.Column(sa.String(32), nullable=False, unique=True, index=True)
    fullname = sa.Column(sa.Text, nullable=False, index=True)
    public_ssh_key = sa.Column(sa.Text, nullable=True)

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
        "ProgitGroup",
        secondary="progit_user_group",
        primaryjoin="users.c.id==progit_user_group.c.user_id",
        secondaryjoin="progit_group.c.id==progit_user_group.c.group_id",
        backref="users",
    )
    session = relation("ProgitUserVisit", backref="user")

    @property
    def username(self):
        ''' Return the username. '''
        return self.user

    @property
    def groups(self):
        ''' Return the list of Group.group_name in which the user is. '''
        return [group.group_name for group in self.group_objs]

    def __repr__(self):
        ''' Return a string representation of this object. '''

        return 'User: %s - name %s' % (self.id, self.user)


class UserEmail(BASE):
    """ Stores email information about the users.

    Table -- user_emails
    """

    __tablename__ = 'user_emails'
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('users.id', onupdate='CASCADE'),
        nullable=False,
        index=True)
    email = sa.Column(sa.Text, nullable=False, unique=True)

    user = relation('User', foreign_keys=[user_id],
                    remote_side=[User.id], backref='emails')


class Project(BASE):
    """ Stores the projects.

    Table -- projects
    """

    __tablename__ = 'projects'

    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('users.id', onupdate='CASCADE'),
        nullable=False,
        index=True)
    name = sa.Column(sa.String(32), nullable=False, index=True)
    description = sa.Column(sa.Text, nullable=True)
    parent_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=True)
    issue_tracker = sa.Column(sa.Boolean, nullable=False, default=True)
    project_docs = sa.Column(sa.Boolean, nullable=False, default=True)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    parent = relation('Project', remote_side=[id], backref='forks')
    user = relation('User', foreign_keys=[user_id],
                    remote_side=[User.id], backref='projects')

    users = relation('User',
        secondary="user_projects",
        primaryjoin="projects.c.id==user_projects.c.project_id",
        secondaryjoin="users.c.id==user_projects.c.user_id",
        backref='co_projects')

    @property
    def path(self):
        ''' Return the name of the git repo on the filesystem. '''
        if self.parent_id:
            path = '%s/%s.git' % (self.user.user, self.name)
        else:
            path = '%s.git' % (self.name)
        return path

    @property
    def is_fork(self):
        ''' Return a boolean specifying if the project is a fork or not '''
        return self.parent_id is not None

    @property
    def fullname(self):
        ''' Return the name of the git repo as user/project if it is a
        project forked, otherwise it returns the project name.
        '''
        str_name = self.name
        if self.parent_id:
            str_name = "%s/%s" % (self.user.user, str_name)
        return str_name


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
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=False)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('users.id', onupdate='CASCADE'),
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
            'projects.id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True)
    title = sa.Column(
        sa.Text,
        nullable=False)
    content = sa.Column(
        sa.Text(),
        nullable=False)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('users.id', onupdate='CASCADE'),
        nullable=False,
        index=True)
    assignee_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('users.id', onupdate='CASCADE'),
        nullable=True,
        index=True)
    status = sa.Column(
        sa.Text,
        sa.ForeignKey(
            'status_issue.status', ondelete='CASCADE', onupdate='CASCADE'),
        default='Open',
        nullable=False)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    project = relation(
        'Project', foreign_keys=[project_id], remote_side=[Project.id],
        backref='issues', cascade="delete, delete-orphan",
        single_parent=True)
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
    def mail_id(self):
        ''' Return a unique reprensetation of the issue as string that
        can be used when sending emails.
        '''
        return '%s-ticket-%s@progit' % (self.project.name, self.id)

    def to_json(self):
        ''' Returns a JSON representation of the issue using the JSON module

        '''
        output = {
            'title': self.title,
            'content': self.content,
            'status': self.status,
            'date_created': self.date_created.strftime('%s'),
            'user': {
                'name': self.user.user,
                'emails': [email.email for email in self.user.emails],
            }
        }

        comments = []
        for comment in self.comments:
            cmt = {
                'id': comment.id,
                'comment': comment.comment,
                'parent': comment.parent_id,
                'date_created': comment.date_created.strftime('%s'),
                'user': {
                    'name': comment.user.user,
                    'emails': [email.email for email in comment.user.emails],
                }
            }
            comments.append(cmt)

        output['comments'] = comments

        return json.dumps(output)


class IssueToIssue(BASE):
    """ Stores the parent/child relationship between two issues.

    Table -- issue_to_issue
    """

    __tablename__ = 'issue_to_issue'

    parent_issue_id = sa.Column(
        sa.Text,
        sa.ForeignKey(
            'issues.uid', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True)
    child_issue_id = sa.Column(
        sa.Text,
        sa.ForeignKey(
            'issues.uid', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True)


class IssueComment(BASE):
    """ Stores the comments made on a commit/file.

    Table -- issue_comments
    """

    __tablename__ = 'issue_comments'

    id = sa.Column(sa.Integer, primary_key=True)
    issue_uid = sa.Column(
        sa.Text,
        sa.ForeignKey(
            'issues.uid', ondelete='CASCADE', onupdate='CASCADE'),
        index=True)
    comment = sa.Column(
        sa.Text(),
        nullable=False)
    parent_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('issue_comments.id', onupdate='CASCADE'),
        nullable=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('users.id', onupdate='CASCADE'),
        nullable=False,
        index=True)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    issue = relation(
        'Issue', foreign_keys=[issue_uid], remote_side=[Issue.uid],
        backref=backref('comments', order_by="IssueComment.date_created")
    )
    user = relation('User', foreign_keys=[user_id],
                    remote_side=[User.id], backref='comment_issues')


class Tag(BASE):
    """ Stores the tags.

    Table -- tags
    """

    __tablename__ = 'tags'

    tag = sa.Column(sa.Text(), primary_key=True)
    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)


class TagIssue(BASE):
    """ Stores the tag associated with an issue.

    Table -- tags_issues
    """

    __tablename__ = 'tags_issues'

    tag = sa.Column(
        sa.Text(),
        sa.ForeignKey(
            'tags.tag', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True)
    issue_uid = sa.Column(
        sa.Text,
        sa.ForeignKey(
            'issues.uid', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True)
    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    issue = relation(
        'Issue', foreign_keys=[issue_uid], remote_side=[Issue.uid],
        backref=backref(
            'tags', cascade="delete, delete-orphan", single_parent=True)
        )


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
            'projects.id', ondelete='CASCADE', onupdate='CASCADE'),
        primary_key=True)
    branch = sa.Column(
        sa.Text(),
        nullable=False)
    project_id_from = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False)
    branch_from = sa.Column(
        sa.Text(),
        nullable=False)
    commit_start = sa.Column(
        sa.Text(),
        nullable=True)
    commit_stop = sa.Column(
        sa.Text(),
        nullable=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('users.id', onupdate='CASCADE'),
        nullable=False,
        index=True)
    status = sa.Column(sa.Boolean, nullable=False, default=True)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    repo = relation(
        'Project', foreign_keys=[project_id], remote_side=[Project.id],
        backref='requests', cascade="delete, delete-orphan",
        single_parent=True)
    repo_from = relation(
        'Project', foreign_keys=[project_id_from], remote_side=[Project.id])
    user = relation('User', foreign_keys=[user_id],
                    remote_side=[User.id], backref='pull_requests')

    def __repr__(self):
        return 'PullRequest(%s, project:%s, user:%s, title:%s)' % (
            self.id, self.repo.name, self.user.user, self.title
        )

    @property
    def mail_id(self):
        ''' Return a unique reprensetation of the issue as string that
        can be used when sending emails.
        '''
        return '%s-pull-request-%s@progit' % (self.repo.name, self.id)


class PullRequestComment(BASE):
    """ Stores the comments made on a pull-request.

    Table -- pull_request_comments
    """

    __tablename__ = 'pull_request_comments'

    id = sa.Column(sa.Integer, primary_key=True)
    pull_request_uid = sa.Column(
        sa.Text,
        sa.ForeignKey(
            'pull_requests.uid', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False)
    commit_id = sa.Column(
        sa.String(40),
        nullable=False,
        index=True)
    user_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('users.id', onupdate='CASCADE'),
        nullable=False,
        index=True)
    filename = sa.Column(
        sa.Text,
        nullable=True)
    line = sa.Column(
        sa.Integer,
        nullable=True)
    comment = sa.Column(
        sa.Text(),
        nullable=False)
    parent_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('pull_request_comments.id', onupdate='CASCADE'),
        nullable=True)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    user = relation('User', foreign_keys=[user_id],
                    remote_side=[User.id],
                    backref=backref(
                        'pull_request_comments',
                        order_by="PullRequestComment.date_created")
                    )
    pull_request = relation(
        'PullRequest', backref='comments',
        foreign_keys=[pull_request_uid],
        remote_side=[PullRequest.uid])


# ##########################################################
# These classes are only used if you're using the `local`
#                  authentication method
# ##########################################################


class ProgitUserVisit(BASE):

    __tablename__ = 'progit_user_visit'

    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.Integer, sa.ForeignKey('users.id'), nullable=False)
    visit_key = sa.Column(
        sa.String(40), nullable=False, unique=True, index=True)
    user_ip = sa.Column(sa.String(50), nullable=False)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow)
    expiry = sa.Column(sa.DateTime)


class ProgitGroup(BASE):
    """
    An ultra-simple group definition.
    """

    # names like "Group", "Order" and "User" are reserved words in SQL
    # so we set the name to something safe for SQL
    __tablename__ = 'progit_group'

    id = sa.Column(sa.Integer, primary_key=True)
    group_name = sa.Column(sa.String(16), nullable=False, unique=True)
    created = sa.Column(
        sa.DateTime, nullable=False, default=datetime.datetime.utcnow)

    def __repr__(self):
        ''' Return a string representation of this object. '''

        return 'Group: %s - name %s' % (self.id, self.group_name)


class ProgitUserGroup(BASE):
    """
    Association table linking the mm_user table to the mm_group table.
    This allow linking users to groups.
    """

    __tablename__ = 'progit_user_group'

    user_id = sa.Column(
        sa.Integer, sa.ForeignKey('users.id'), primary_key=True)
    group_id = sa.Column(
        sa.Integer, sa.ForeignKey('progit_group.id'), primary_key=True)

    # Constraints
    __table_args__ = (
        sa.UniqueConstraint(
            'user_id', 'group_id'),
    )
