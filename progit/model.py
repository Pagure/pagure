#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

__requires__ = ['SQLAlchemy >= 0.7', 'jinja2 >= 2.4']
import pkg_resources

import datetime
import logging

import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.declarative import declarative_base
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
    create_default_status(scopedsession)
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
            ERROR_LOG.exception(err)

    session.commit()


class StatusIssue(BASE):
    """ Stores the status a ticket can have.

    Table -- status_issue
    """
    __tablename__ = 'status_issue'

    id = sa.Column(sa.Integer, primary_key=True)
    status = sa.Column(sa.Text, nullable=False, unique=True)


class Project(BASE):
    """ Stores the projects.

    Table -- projects
    """

    __tablename__ = 'projects'

    id = sa.Column(sa.Integer, primary_key=True)
    user = sa.Column(sa.String(32), nullable=False)
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

    @property
    def path(self):
        ''' Return the name of the git repo on the filesystem. '''
        if self.parent_id:
            path = '%s/%s.git' % (self.user, self.name)
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
            str_name = "%s/%s" % (self.user, str_name)
        return str_name


class ProjectUser(BASE):
    """ Stores the user of a projects.

    Table -- user_projects
    """

    __tablename__ = 'user_projects'
    __table_args__ = (
        sa.UniqueConstraint('project_id', 'user'),
    )

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('projects.id', onupdate='CASCADE'),
        nullable=False)
    user = sa.Column(sa.String(32), nullable=False)

    project = relation(
        'Project', foreign_keys=[project_id], remote_side=[Project.id],
        backref='users')


class Comment(BASE):
    """ Stores the comments made on a commit/file.

    Table -- comments
    """

    __tablename__ = 'comments'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False)
    commit_id = sa.Column(
        sa.String(40),
        nullable=False,
        index=True)
    line = sa.Column(
        sa.Integer,
        nullable=True)
    comment = sa.Column(
        sa.Text(),
        nullable=False)
    parent_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('comments.id', onupdate='CASCADE'),
        nullable=True)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)


class Issue(BASE):
    """ Stores the issues reported on a project.

    Table -- issues
    """

    __tablename__ = 'issues'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False)
    title = sa.Column(
        sa.Text,
        nullable=False)
    content = sa.Column(
        sa.Text(),
        nullable=False)
    user = sa.Column(sa.String(32), nullable=False)
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
        backref='issues')


class IssueComment(BASE):
    """ Stores the comments made on a commit/file.

    Table -- issue_comments
    """

    __tablename__ = 'issue_comments'

    id = sa.Column(sa.Integer, primary_key=True)
    issue_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'issues.id', ondelete='CASCADE', onupdate='CASCADE'),
        index=True)
    comment = sa.Column(
        sa.Text(),
        nullable=False)
    parent_id = sa.Column(
        sa.Integer,
        sa.ForeignKey('comments.id', onupdate='CASCADE'),
        nullable=True)
    user = sa.Column(sa.String(32), nullable=False)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    issue = relation(
        'Issue', foreign_keys=[issue_id], remote_side=[Issue.id],
        backref='comments')


class PullRequest(BASE):
    """ Stores the pull requests created on a project.

    Table -- pull_requests
    """

    __tablename__ = 'pull_requests'

    id = sa.Column(sa.Integer, primary_key=True)
    project_id = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False)
    project_id_from = sa.Column(
        sa.Integer,
        sa.ForeignKey(
            'projects.id', ondelete='CASCADE', onupdate='CASCADE'),
        nullable=False)
    title = sa.Column(
        sa.Text,
        nullable=False)
    start_id = sa.Column(
        sa.String(40),
        nullable=True)
    stop_id = sa.Column(
        sa.String(40),
        nullable=False)
    user = sa.Column(sa.String(32), nullable=False)
    status = sa.Column(sa.Boolean, nullable=False, default=True)

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    repo = relation(
        'Project', foreign_keys=[project_id], remote_side=[Project.id],
        backref='requests')
    repo_from = relation(
        'Project', foreign_keys=[project_id_from], remote_side=[Project.id])
