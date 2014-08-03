#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


import json
import os
import shutil
import tempfile
import uuid

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


def get_user(session, username):
    ''' Return the user corresponding to this username, or None. '''
    user = session.query(
        model.User
    ).filter(
        model.User.user == username
    ).first()
    return user


def get_user_by_email(session, user_mail):
    ''' Return the user corresponding to this email, or None. '''
    mail = session.query(
        model.UserEmail
    ).filter(
        model.UserEmail.email == user_mail
    ).first()
    if mail:
        return mail.user


def get_all_users(session):
    ''' Return the user corresponding to this username, or None. '''
    users = session.query(
        model.User
    ).all()
    return users


def add_issue_comment(session, issue, comment, user, ticketfolder):
    ''' Add a comment to an issue. '''
    user_obj = get_user(session, user)
    if not user_obj:
        user_obj = get_user_by_email(session, user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    isse_comment = model.IssueComment(
        issue_id=issue.id,
        comment=comment,
        user_id=user_obj.id,
    )
    session.add(isse_comment)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    update_git_ticket(issue, repo=issue.project, ticketfolder=ticketfolder)

    return 'Comment added'


def get_user_project(session, username):
    ''' Retrieve the list of projects managed by a user.

    '''

    query = session.query(
        model.Project
    ).filter(
        model.Project.user == username
    )

    return query.all()


def new_project(session, user, name, gitfolder, docfolder, ticketfolder,
                description=None, parent_id=None):
    ''' Create a new project based on the information provided.
    '''
    gitrepo = os.path.join(gitfolder, '%s.git' % name)
    if os.path.exists(gitrepo):
        raise progit.exceptions.RepoExistsException(
            'The project repo "%s" already exists' % name
        )

    user_obj = get_user(session, user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    project = model.Project(
        name=name,
        description=description,
        user_id=user_obj.id,
        parent_id=parent_id
    )
    session.add(project)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    pygit2.init_repository(gitrepo, bare=True)

    gitrepo = os.path.join(docfolder, project.path)
    if os.path.exists(gitrepo):
        raise progit.exceptions.RepoExistsException(
            'The docs repo "%s" already exists' % project.path
        )
    pygit2.init_repository(gitrepo, bare=True)

    gitrepo = os.path.join(ticketfolder, project.path)
    if os.path.exists(gitrepo):
        raise progit.exceptions.RepoExistsException(
            'The tickets repo "%s" already exists' % project.path
        )
    pygit2.init_repository(gitrepo, bare=True)

    return 'Project "%s" created' % name


def new_issue(session, repo, title, content, user, ticketfolder):
    ''' Create a new issue for the specified repo. '''
    user_obj = get_user(session, user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    issue = model.Issue(
        project_id=repo.id,
        title=title,
        content=content,
        user_id=user_obj.id,
        uid=uuid.uuid4().hex,
    )
    session.add(issue)
    # Make sure we won't have SQLAlchemy error before we create the issue
    session.flush()

    global_id = model.GlobalId(
        project_id=repo.id,
        issue_id=issue.id,
    )

    session.add(global_id)
    session.flush()

    update_git_ticket(issue, repo=repo, ticketfolder=ticketfolder)

    return 'Issue created'


def new_pull_request(
        session, repo, repo_from, title, user, stop_id, start_id=None):
    ''' Create a new pull request on the specified repo. '''
    user_obj = get_user(session, user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    request = model.PullRequest(
        project_id=repo.id,
        project_id_from=repo_from.id,
        title=title,
        start_id=start_id,
        stop_id=stop_id,
        user_id=user_obj.id,
    )
    session.add(request)
    # Make sure we won't have SQLAlchemy error before we create the request
    session.flush()

    global_id = model.GlobalId(
        project_id=repo.id,
        request_id=request.id,
    )

    session.add(global_id)
    session.flush()

    return 'Request created'


def edit_issue(session, issue, ticketfolder,
               title=None, content=None, status=None):
    ''' Edit the specified issue.
    '''
    edit = []
    if title and title != issue.title:
        issue.title = title
        edit.append('title')
    if content and content != issue.content:
        issue.content = content
        edit.append('content')
    if status and status != issue.status:
        issue.status = status
        edit.append('status')

    update_git_ticket(issue, repo=issue.project, ticketfolder=ticketfolder)

    if not edit:
        return 'No changes to edit'
    else:
        session.add(issue)
        session.flush()
        return 'Edited successfully issue #%s' % issue.id


def update_project_settings(session, repo, issue_tracker, project_docs):
    ''' Update the settings of a project. '''
    update = []
    if issue_tracker != repo.issue_tracker:
        repo.issue_tracker = issue_tracker
        update.append('issue_tracker')
    if project_docs != repo.project_docs:
        repo.project_docs = project_docs
        update.append('project_docs')

    if not update:
        return 'No settings to change'
    else:
        session.add(repo)
        session.flush()
        return 'Edited successfully setting of repo: %s' % repo.fullname


def fork_project(session, user, repo, gitfolder,
                 forkfolder, docfolder,ticketfolder):
    ''' Fork a given project into the user's forks. '''
    if repo.is_fork:
        reponame = os.path.join(forkfolder, repo.path)
    else:
        reponame = os.path.join(gitfolder, repo.path)
    forkreponame = '%s.git' % os.path.join(forkfolder, user, repo.name)

    if repo.user.user == user:
        raise progit.exceptions.RepoExistsException(
            'You may not fork your own repo')

    if os.path.exists(forkreponame):
        raise progit.exceptions.RepoExistsException(
            'Repo "%s/%s" already exists' % (user, repo.name))

    user_obj = get_user(session, user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    project = model.Project(
        name=repo.name,
        description=repo.description,
        user_id=user_obj.id,
        parent_id=repo.id
    )
    session.add(project)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    pygit2.clone_repository(reponame, forkreponame, bare=True)

    gitrepo = os.path.join(docfolder, project.path)
    if os.path.exists(gitrepo):
        raise progit.exceptions.RepoExistsException(
            'The docs "%s" already exists' % project.path
        )
    pygit2.init_repository(gitrepo, bare=True)

    gitrepo = os.path.join(ticketfolder, project.path)
    if os.path.exists(gitrepo):
        raise progit.exceptions.RepoExistsException(
            'The tickets repo "%s" already exists' % project.path
        )
    pygit2.init_repository(gitrepo, bare=True)

    return 'Repo "%s" cloned to "%s/%s"' % (repo.name, user, repo.name)


def list_projects(
        session, username=None, fork=None,
        start=None, limit=None, count=False):
    '''List existing projects
    '''
    projects = session.query(
        model.Project
    ).order_by(
        model.Project.date_created
    )

    if username is not None:
        projects = projects.filter(
            model.User.user == username
        ).filter(
            model.User.id == model.Project.user_id
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
            model.User.user == user
        ).filter(
            model.User.id == model.Project.user_id
        ).filter(
            model.Project.parent_id != None
        )
    else:
        query = query.filter(
            model.Project.parent_id == None
        )

    return query.first()


def get_issues(session, repo, status=None, closed=False):
    ''' Retrieve all the issues associated to a project

    Watch out that the closed argument is incompatible with the status
    argument. The closed argument will return all the issues whose status
    is not 'Open', otherwise it will return the issues having the specified
    status.
    '''
    subquery = session.query(
        model.GlobalId,
        sqlalchemy.over(
            sqlalchemy.func.row_number(),
            partition_by=model.GlobalId.project_id,
            order_by=model.GlobalId.id
        ).label('global_id')
    ).subquery()

    query = session.query(
        model.Issue,
        subquery.c.global_id
    ).filter(
        subquery.c.issue_id == model.Issue.id
    ).filter(
        subquery.c.project_id == model.Issue.project_id
    ).filter(
        model.Issue.project_id == repo.id
    ).order_by(
        model.Issue.id
    )

    if status is not None and not closed:
        query = query.filter(
            model.Issue.status == status
        )
    if closed:
        query = query.filter(
            model.Issue.status != 'Open'
        )

    return query.all()


def get_issue(session, issueid):
    ''' Retrieve the specified issue
    '''
    subquery = session.query(
        model.GlobalId,
        sqlalchemy.over(
            sqlalchemy.func.row_number(),
            partition_by=model.GlobalId.project_id,
            order_by=model.GlobalId.id
        ).label('global_id')
    ).subquery()

    query = session.query(
        model.Issue
    ).filter(
        subquery.c.project_id == model.Issue.project_id
    ).filter(
        subquery.c.issue_id == model.Issue.id
    ).filter(
        subquery.c.global_id == issueid
    ).order_by(
        model.Issue.id
    )

    return query.first()


def get_pull_requests(
        session, project_id=None, project_id_from=None, status=None):
    ''' Retrieve the specified issue
    '''

    subquery = session.query(
        model.GlobalId,
        sqlalchemy.over(
            sqlalchemy.func.row_number(),
            partition_by=model.GlobalId.project_id,
            order_by=model.GlobalId.id
        ).label('global_id')
    ).subquery()

    query = session.query(
        model.PullRequest,
        subquery.c.global_id
    ).filter(
        subquery.c.request_id == model.PullRequest.id
    ).filter(
        subquery.c.project_id == model.PullRequest.project_id
    ).order_by(
        model.PullRequest.id
    )

    if project_id:
        query = query.filter(
            model.PullRequest.project_id == project_id
        )

    if project_id_from:
        query = query.filter(
            model.PullRequest.project_id_from == project_id_from
        )

    if status is not None:
        query = query.filter(
            model.PullRequest.status == status
        )

    return query.all()


def get_pull_request(
        session, requestid, project_id=None, project_id_from=None):
    ''' Retrieve the specified issue
    '''

    subquery = session.query(
        model.GlobalId,
        sqlalchemy.over(
            sqlalchemy.func.row_number(),
            partition_by=model.GlobalId.project_id,
            order_by=model.GlobalId.id
        ).label('global_id')
    ).subquery()

    query = session.query(
        model.PullRequest
    ).filter(
        subquery.c.project_id == model.PullRequest.project_id
    ).filter(
        subquery.c.request_id == model.PullRequest.id
    ).filter(
        subquery.c.global_id == requestid
    ).order_by(
        model.PullRequest.id
    )

    if project_id:
        query = query.filter(
            model.PullRequest.project_id == project_id
        )

    if project_id_from:
        query = query.filter(
            model.PullRequest.project_id_from == project_id_from
        )

    return query.first()


def close_pull_request(session, request):
    ''' Close the provided pull-request.
    '''
    request.status = False
    session.add(request)
    session.flush()


def get_issue_statuses(session):
    ''' Return the complete list of status an issue can have.
    '''
    output = []
    statuses = session.query(model.StatusIssue).all()
    for status in statuses:
        output.append(status.status)
    return output


def generate_gitolite_acls(session, configfile):
    ''' Generate the configuration file for gitolite for all projects
    on the forge.
    '''
    config = []
    for project in session.query(model.Project).all():
        if project.parent_id:
            config.append('repo forks/%s' % project.fullname)
        else:
            config.append('repo %s' % project.fullname)
        config.append('  RW+ = %s' % project.user.user)
        for user in project.users:
            if user != project.user:
                config.append('  RW+ = %s' % user.user.user)
        config.append('')

        config.append('repo docs/%s' % project.fullname)
        config.append('  RW+ = %s' % project.user.user)
        for user in project.users:
            if user != project.user:
                config.append('  RW+ = %s' % user.user.user)
        config.append('')

        config.append('repo tickets/%s' % project.fullname)
        config.append('  RW+ = %s' % project.user.user)
        for user in project.users:
            if user != project.user:
                config.append('  RW+ = %s' % user.user.user)
        config.append('')

    with open(configfile, 'w') as stream:
        for row in config:
            stream.write(row + '\n')


def set_up_user(session, username, fullname, user_email):
    ''' Set up a new user into the database or update its information. '''
    user = get_user(session, username)
    if not user:
        user = model.User(
            user=username,
            fullname=fullname)
        session.add(user)
        session.flush()

    if user.fullname != fullname:
        user.fullname = fullname
        session.add(user)
        session.flush()

    emails = [email.email for email in user.emails]
    if user_email not in emails:
        useremail = model.UserEmail(
            user_id=user.id,
            email=user_email)
        session.add(useremail)
        session.flush()


def update_user_ssh(session, user, ssh_key):
    ''' Set up a new user into the database or update its information. '''
    if isinstance(user, basestring):
        user = get_user(session, user)

    message = 'Nothing to update'

    if ssh_key != user.public_ssh_key:
        user.public_ssh_key = ssh_key
        session.add(user)
        session.flush()
        message = 'Public ssh key updated'

    return message


def issue_to_json(issue):
    """ Convert all the data related to an issue (a ticket) as json object.

    """
    output = {
        'title': issue.title,
        'content': issue.content,
        'status': issue.status,
        'date_created': issue.date_created.strftime('%s'),
        'user': {
            'name': issue.user.user,
            'emails': [email.email for email in issue.user.emails],
        }
    }

    comments = []
    for comment in issue.comments:
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


def update_git_ticket(issue, repo, ticketfolder):
    """ Update the given issue in its git.

    This method forks the provided repo, add/edit the issue whose file name
    is defined by the uid field of the issue and if there are additions/
    changes commit them and push them back to the original repo.

    """

    # Get the fork
    repopath = os.path.join(ticketfolder, repo.path)
    ticket_repo = pygit2.Repository(repopath)

    # Clone the repo into a temp folder
    newpath = tempfile.mkdtemp()
    new_repo = pygit2.clone_repository(repopath, newpath)

    file_path = os.path.join(newpath, issue.uid)

    # Get the current index
    index = new_repo.index

    # Are we adding files
    added = False
    if not os.path.exists(file_path):
        added = True

    # Write down what changed
    with open(file_path, 'w') as stream:
        stream.write(issue_to_json(issue))

    # Retrieve the list of files that changed
    diff = new_repo.diff()
    files = [patch.new_file_path for patch in diff]

    # Add the changes to the index
    if added:
        index.add(issue.uid)
    for filename in files:
        index.add(filename)

    # If not change, return
    if not files and not added:
        shutil.rmtree(newpath)
        return

    # See if there is a parent to this commit
    parent = None
    try:
        parent = new_repo.head.get_object().oid
    except pygit2.GitError:
        pass

    parents = []
    if parent:
        parents.append(parent)

    # Author/commiter will always be this one
    author = pygit2.Signature(name='progit', email='progit')

    # Actually commit
    sha = new_repo.create_commit(
        'refs/heads/master',
        author,
        author,
        'Updated ticket %s: %s' % (issue.uid, issue.title),
        new_repo.index.write_tree(),
        parents)
    index.write()

    # Push to origin
    ori_remote = new_repo.remotes[0]
    master_ref = new_repo.lookup_reference('HEAD').resolve()
    refname = '%s:%s' % (master_ref.name, master_ref.name)

    ori_remote.push(refname)

    # Remove the clone
    shutil.rmtree(newpath)
