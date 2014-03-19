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
    return scopedsession


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

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)

    parent = relation('Project')

    @property
    def path(self):
        ''' Return the name of the git repo on the filesystem. '''
        return "%s.git" % self.name

    @property
    def fork(self):
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

    date_created = sa.Column(sa.DateTime, nullable=False,
                             default=datetime.datetime.utcnow)
