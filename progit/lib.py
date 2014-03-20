#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


import os

import sqlalchemy
from datetime import timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import SQLAlchemyError

import pygit2

import progit.exceptions
from progit import model


def create_session(db_url, debug=False, pool_recycle=3600):
    ''' Create the Session object to use to query the database.

    :arg db_url: URL used to connect to the database. The URL contains
    information with regards to the database engine, the host to connect
    to, the user and password and the database name.
      ie: <engine>://<user>:<password>@<host>/<dbname>
    :kwarg debug: a boolean specifying wether we should have the verbose
        output of sqlalchemy or not.
    :return a Session that can be used to query the database.

    '''
    engine = sqlalchemy.create_engine(
        db_url, echo=debug, pool_recycle=pool_recycle)
    scopedsession = scoped_session(sessionmaker(bind=engine))
    return scopedsession


def get_user_project(session, username):
    ''' Retrieve the list of projects managed by a user.

    '''

    query = session.query(
        model.Project
    ).filter(
        model.Project.user == username
    )

    return query.all()


def new_project(session, user, name, folder,
                description=None, parent_id=None):
    ''' Create a new project based on the information provided.
    '''
    gitrepo = os.path.join(folder, '%s.git' % name)
    if os.path.exists(gitrepo):
        raise progit.exceptions.RepoExistsException(
            'The project "%s" already exists' % name
        )

    project = model.Project(
        name=name,
        description=description,
        user=user,
        parent_id=parent_id
    )
    session.add(project)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    pygit2.init_repository(gitrepo, bare=True)

    return 'Project "%s" created' % name


def new_issue(session, repo, title, content, user):
    ''' Create a new issue for the specified repo. '''
    issue = model.Issue(
        project_id=repo.id,
        title=title,
        content=content,
        user=user,
    )
    session.add(issue)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    return 'Issue created'


def edit_issue(session, issue, title, content):
    ''' Edit the specified issue.
    '''
    edit = []
    if title != issue.title:
        issue.title = title
        edit.append('title')
    if content != issue.content:
        issue.content = content
        edit.append('content')

    if not edit:
        return 'No changes to edit'
    else:
        session.add(issue)
        session.flush()
        return 'Edited successfully issue #%s' % issue.id


def fork_project(session, user, repo, repo_folder, fork_folder):
    ''' Fork a given project into the user's forks. '''
    reponame = os.path.join(repo_folder, repo.path)
    forkreponame = os.path.join(fork_folder, user, repo.path)

    if os.path.exists(forkreponame):
        raise progit.exceptions.RepoExistsException(
            'Repo "%s/%s" already exists' % (user, repo.name))

    project = model.Project(
        name=repo.name,
        description=repo.description,
        user=user,
        parent_id=repo.id
    )
    session.add(project)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    pygit2.clone_repository(reponame, forkreponame, bare=True)

    return 'Repo "%s" cloned to "%s/%s"' % (repo.name, user, repo.name)


def list_projects(
        session, username=None, fork=None,
        start=None, limit=None, count=False):
    '''List existing projects
    '''
    projects = session.query(model.Project)

    if username is not None:
        projects = projects.filter_by(
            user=username
        )

    if fork is not None:
        if fork is True:
            projects = projects.filter(
                model.Project.parent_id != None
            )
        elif fork is False:
            projects = projects.filter(
                model.Project.parent_id == None
            )

    if start is not None:
        projects = projects.offset(start)

    if limit is not None:
        projects = projects.limit(limit)

    if count:
        return projects.count()
    else:
        return projects.all()


def get_project(session, name, user=None):
    '''Get a project from the database
    '''
    query = session.query(
        model.Project
    ).filter(
        model.Project.name == name
    )

    if user is not None:
        query = query.filter(
            model.Project.user == user
        ).filter(
            model.Project.parent_id != None
        )
    else:
        query = query.filter(
            model.Project.parent_id == None
        )

    return query.first()


def get_issues(session, repo):
    ''' Retrieve all the issues associated to a project
    '''
    query = session.query(
        model.Issue
    ).filter(
        model.Issue.project_id == repo.id
    )

    return query.all()


def get_issue(session, issueid):
    ''' Retrieve the specified issue
    '''
    query = session.query(
        model.Issue
    ).filter(
        model.Issue.id == issueid
    )

    return query.first()
