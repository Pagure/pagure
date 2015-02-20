#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


import datetime
import json
import os
import random
import shutil
import string
import tempfile
import uuid

import sqlalchemy
import sqlalchemy.schema
from datetime import timedelta
from sqlalchemy import func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import SQLAlchemyError

import pygit2

import progit.exceptions
import progit.notify
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


def id_generator(size=15, chars=string.ascii_uppercase + string.digits):
    """ Generates a random identifier for the given size and using the
    specified characters.
    If no size is specified, it uses 15 as default.
    If no characters are specified, it uses ascii char upper case and
    digits.
    :arg size: the size of the identifier to return.
    :arg chars: the list of characters that can be used in the
        idenfitier.
    """
    return ''.join(random.choice(chars) for x in range(size))


def get_next_id(session, projectid):
    """ Returns the next identifier of a project ticket or pull-request
    based on the identifier already in the database.
    """
    q1 = session.query(
        func.max(model.Issue.id)
    ).filter(
        model.Issue.project_id == projectid
    )

    q2 = session.query(
        func.max(model.PullRequest.id)
    ).filter(
        model.PullRequest.project_id == projectid
    )

    nid = max([el[0] for el in q1.union(q2).all()]) or 0

    return nid + 1


def commit_to_patch(repo_obj, commits):
    ''' For a given commit (PyGit2 commit object) of a specified git repo,
    returns a string representation of the changes the commit did in a
    format that allows it to be used as patch.
    '''
    if not isinstance(commits, list):
        commits = [commits]

    patch = ""
    for cnt, commit in enumerate(commits):
        if commit.parents:
            diff = commit.tree.diff_to_tree()

            parent = repo_obj.revparse_single('%s^' % commit.oid.hex)
            diff = repo_obj.diff(parent, commit)
        else:
            # First commit in the repo
            diff = commit.tree.diff_to_tree(swap=True)

        subject = message = ''
        if '\n' in commit.message:
            subject, message = commit.message.split('\n', 1)
        else:
            subject = commit.message

        if len(commits) > 1:
            subject = '[PATCH %s/%s] %s' % (cnt + 1, len(commits), subject)

        patch += """From %(commit)s Mon Sep 17 00:00:00 2001
From: %(author_name)s <%(author_email)s>
Date: %(date)s
Subject: %(subject)s

%(msg)s
---

%(patch)s
""" % (
            {
                'commit': commit.oid.hex,
                'author_name': commit.author.name,
                'author_email': commit.author.email,
                'date': datetime.datetime.utcfromtimestamp(
                    commit.commit_time).strftime('%b %d %Y %H:%M:%S +0000'),
                'subject': subject,
                'msg': message,
                'patch': diff.patch,
            }
        )
    return patch


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


def get_user_by_token(session, token):
    ''' Return a specified User via its token.

    :arg session: the session with which to connect to the database.

    '''
    user = session.query(
        model.User
    ).filter(
        model.User.token == token
    ).first()
    return user


def get_all_users(session, pattern=None):
    ''' Return the user corresponding to this username, or None. '''
    query = session.query(
        model.User
    ).order_by(
        model.User.user
    )

    if pattern:
        pattern = pattern.replace('*', '%')
        query = query.filter(
            model.User.user.like(pattern)
        )

    users = query.all()
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

    issue_comment = model.IssueComment(
        issue_id=issue.id,
        comment=comment,
        user_id=user_obj.id,
    )
    session.add(issue_comment)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    update_git_ticket(issue, repo=issue.project, ticketfolder=ticketfolder)

    progit.notify.notify_new_comment(issue_comment)

    return 'Comment added'


def add_issue_tag(session, issue, tag, user, ticketfolder):
    ''' Add a tag to an issue. '''
    user_obj = get_user(session, user)
    if not user_obj:
        user_obj = get_user_by_email(session, user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    for tag_issue in issue.tags:
        if tag_issue.tag == tag:
            return 'Tag already present: %s' % tag

    tagobj = get_tag(session, tag)
    if not tagobj:
        tagobj = model.Tag(tag=tag)
        session.add(tagobj)
        session.flush()

    issue_tag = model.TagIssue(
        issue_id=issue.id,
        tag=tagobj.tag,
    )
    session.add(issue_tag)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    update_git_ticket(issue, repo=issue.project, ticketfolder=ticketfolder)

    return 'Tag added'


def add_issue_assignee(session, issue, assignee, user, ticketfolder):
    ''' Add an assignee to an issue, in other words, assigned an issue. '''
    user_obj = get_user(session, user)
    if not user_obj:
        user_obj = get_user_by_email(session, user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    # Validate the assignee
    user_obj = get_user(session, assignee)
    if not user_obj:
        user_obj = get_user_by_email(session, assignee)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % assignee
        )

    if issue.assignee_id != user_obj.id:
        issue.assignee_id = user_obj.id
        session.add(issue)
        # Make sure we won't have SQLAlchemy error before we create the repo
        session.flush()
        update_git_ticket(
            issue, repo=issue.project, ticketfolder=ticketfolder)

        progit.notify.notify_assigned_issue(issue, user_obj)

        return 'Issue assigned'


def add_issue_dependancy(session, issue, issue_blocked, user, ticketfolder):
    ''' Add a depdency between two issues. '''
    user_obj = get_user(session, user)
    if not user_obj:
        user_obj = get_user_by_email(session, user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    if issue_blocked not in issue.children:
        i2i = model.IssueToIssue(
            parent_issue_id=issue_blocked.uid,
            child_issue_id=issue.uid
        )
        session.add(i2i)
        # Make sure we won't have SQLAlchemy error before we create the repo
        session.flush()
        update_git_ticket(
            issue, repo=issue.project, ticketfolder=ticketfolder)
        update_git_ticket(
            issue_blocked,
            repo=issue_blocked.project,
            ticketfolder=ticketfolder)

        #progit.notify.notify_assigned_issue(issue, user_obj)
        #progit.notify.notify_assigned_issue(issue_blocked, user_obj)

        return 'Issue assigned'


def remove_issue_tags(session, project, tags):
    ''' Removes the specified tag of a project. '''

    if not isinstance(tags, list):
        tags = [tags]

    issues = get_issues(session, project, closed=False, tags=tags)
    issues.extend(get_issues(session, project, closed=True, tags=tags))

    msgs = []
    if not issues:
        raise progit.exceptions.ProgitException(
            'No issue found with the tag: %s' % tag)
    else:
        for issue in issues:
            for issue_tag in issue[0].tags:
                if issue_tag.tag in tags:
                    tag = issue_tag.tag
                    session.delete(issue_tag)
                    msgs.append('Removed tag: %s' % tag)
    return msgs


def edit_issue_tags(session, project, old_tag, new_tag):
    ''' Removes the specified tag of a project. '''

    if not isinstance(old_tag, list):
        old_tags = [old_tag]

    issues = get_issues(session, project, closed=False, tags=old_tags)
    issues.extend(get_issues(session, project, closed=True, tags=old_tags))

    msgs = []
    if not issues:
        raise progit.exceptions.ProgitException(
            'No issue found with the tags: %s' % old_tag)
    else:
        tagobj = get_tag(session, new_tag)
        if not tagobj:
            tagobj = model.Tag(tag=new_tag)
            session.add(tagobj)

        for issue in issues:
            add = True
            # Drop the old tag
            for issue_tag in issue[0].tags:
                if issue_tag.tag in old_tags:
                    tag = issue_tag.tag
                    session.delete(issue_tag)
                if issue_tag.tag == new_tag:
                    add = False

            if add:
                # Add the new one
                issue_tag = model.TagIssue(
                    issue_id=issue[0].id,
                    tag=new_tag
                )
                session.add(issue_tag)
                msgs.append('Edited tag: %s to %s' % (old_tag, new_tag))

    return msgs

def add_user_to_project(session, project, user):
    ''' Add a specified user to a specified project. '''
    user_obj = get_user(session, user)
    if not user_obj:
        user_obj = get_user_by_email(session, user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    project_user = model.ProjectUser(
        project_id=project.id,
        user_id=user_obj.id,
    )
    session.add(project_user)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    return 'User added'


def add_pull_request_comment(session, request, commit, filename, row,
                             comment, user):
    ''' Add a comment to a pull-request. '''
    user_obj = get_user(session, user)
    if not user_obj:
        user_obj = get_user_by_email(session, user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    pr_comment = model.PullRequestComment(
        pull_request_id=request.id,
        commit_id=commit,
        filename=filename,
        line=row,
        comment=comment,
        user_id=user_obj.id,
    )
    session.add(pr_comment)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

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
        id=get_next_id(session, repo.id),
        project_id=repo.id,
        title=title,
        content=content,
        user_id=user_obj.id,
        uid=uuid.uuid4().hex,
    )
    session.add(issue)
    # Make sure we won't have SQLAlchemy error before we create the issue
    session.flush()

    update_git_ticket(issue, repo=repo, ticketfolder=ticketfolder)

    progit.notify.notify_new_issue(issue)

    return 'Issue created'


def new_pull_request(session, repo_from, branch_from,
                     repo_to, branch_to, title, user):
    ''' Create a new pull request on the specified repo. '''
    user_obj = get_user(session, user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    request = model.PullRequest(
        id=get_next_id(session, repo_to.id),
        uid=uuid.uuid4().hex,
        project_id=repo_to.id,
        project_id_from=repo_from.id,
        branch=branch_to,
        branch_from=branch_from,
        title=title,
        user_id=user_obj.id,
    )
    session.add(request)
    # Make sure we won't have SQLAlchemy error before we create the request
    session.flush()

    progit.notify.notify_new_pull_request(request)

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


def get_issues(
        session, repo, status=None, closed=False, tags=None,
        assignee=None, author=None):
    ''' Retrieve all the issues associated to a project

    Watch out that the closed argument is incompatible with the status
    argument. The closed argument will return all the issues whose status
    is not 'Open', otherwise it will return the issues having the specified
    status.
    The `tags` argument can be used to filter the issues returned based on
    a certain tag.

    '''
    query = session.query(
        model.Issue
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
    if tags is not None and tags != []:
        query = query.filter(
            model.Issue.id == model.TagIssue.issue_id
        ).filter(
            model.TagIssue.tag.in_(tags)
        )
    if assignee is not None:
        if assignee not in [0, '0']:
            query = query.filter(
                model.Issue.assignee_id == model.User.id
            ).filter(
                model.User.user == assignee
            )
        else:
            query = query.filter(
                model.Issue.assignee_id == None
            )
    if author is not None:
        query = query.filter(
                model.Issue.user_id == model.User.id
            ).filter(
                model.User.user == author
            )

    return query.all()


def get_issue(session, projectid, issueid):
    ''' Retrieve the specified issue
    '''
    query = session.query(
        model.Issue
    ).filter(
        model.Issue.project_id == projectid
    ).filter(
        model.Issue.id == issueid
    ).order_by(
        model.Issue.id
    )

    return query.first()

def get_tags_of_project(session, project):
    ''' Returns the list of tags associated with the issues of a project.
    '''
    query = session.query(
        model.Tag
    ).filter(
        model.Tag.tag == model.TagIssue.tag
    ).filter(
        model.TagIssue.issue_uid == model.Issue.uid
    ).filter(
        model.Issue.project_id == project.id
    ).order_by(
        model.Tag.tag
    )

    return query.all()


def get_tag(session, tag):
    ''' Returns a Tag object for the given tag text.
    '''
    query = session.query(
        model.Tag
    ).filter(
        model.Tag.tag == tag
    )

    return query.first()


def get_pull_requests(
        session, project_id=None, project_id_from=None, status=None):
    ''' Retrieve the specified issue
    '''

    query = session.query(
        model.PullRequest
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

    query = session.query(
        model.PullRequest
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


def close_pull_request(session, request, user, merged=True):
    ''' Close the provided pull-request.
    '''
    request.status = False
    session.add(request)
    session.flush()

    if merged == True:
        progit.notify.notify_merge_pull_request(request, user)
    else:
        progit.notify.notify_cancelled_pull_request(request, user)


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


def avatar_url(username, size=64, default='retro'):
    openid = "http://%s.id.fedoraproject.org/" % username
    return avatar_url_from_openid(openid, size, default)


def avatar_url_from_openid(openid, size=64, default='retro', dns=False):
    """
    Our own implementation since fas doesn't support this nicely yet.
    """

    if dns:  # pragma: no cover
        # This makes an extra DNS SRV query, which can slow down our webapps.
        # It is necessary for libravatar federation, though.
        import libravatar
        return libravatar.libravatar_url(
            openid=openid,
            size=size,
            default=default,
        )
    else:
        import urllib, hashlib
        query = urllib.urlencode({'s': size, 'd': default})
        hash = hashlib.sha256(openid).hexdigest()
        return "https://seccdn.libravatar.org/avatar/%s?%s" % (hash, query)


def get_session_by_visitkey(session, sessionid):
    ''' Return a specified VisitUser via its session identifier (visit_key).

    :arg session: the session with which to connect to the database.

    '''
    query = session.query(
        model.ProgitUserVisit
    ).filter(
        model.ProgitUserVisit.visit_key == sessionid
    )

    return query.first()


def get_groups(session):
    ''' Return the list of groups present in the database.

    :arg session: the session with which to connect to the database.

    '''
    query = session.query(
        model.ProgitGroup
    ).order_by(
        model.ProgitGroup.group_name
    )

    return query.all()


def get_group(session, group):
    ''' Return a specific group for the specified group name.

    :arg session: the session with which to connect to the database.

    '''
    query = session.query(
        model.ProgitGroup
    ).filter(
        model.ProgitGroup.group_name == group
    ).order_by(
        model.ProgitGroup.group_name
    )

    return query.first()


def get_users_by_group(session, group):
    ''' Return the list of users for a specified group.

    :arg session: the session with which to connect to the database.

    '''
    query = session.query(
        model.User
    ).filter(
        model.User.id == model.ProgitUserGroup.user_id
    ).filter(
        model.ProgitUserGroup.group_id == model.ProgitGroup.id
    ).filter(
        model.ProgitGroup.group_name == group
    ).order_by(
        model.User.user
    )

    return query.all()


def get_user_group(session, userid, groupid):
    ''' Return a specific user_group for the specified group and user
    identifiers.

    :arg session: the session with which to connect to the database.

    '''
    query = session.query(
        model.ProgitUserGroup
    ).filter(
        model.ProgitUserGroup.user_id == userid
    ).filter(
        model.ProgitUserGroup.group_id == groupid
    )

    return query.first()
