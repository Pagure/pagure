#-*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


import datetime
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
import progit.lib.git
import progit.notify
from progit.lib import model


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


def search_user(session, username=None, email=None, token=None, pattern=None):
    ''' Searches the database for the user or users matching the given
    criterias.

    :arg session: the session to use to connect to the database.
    :kwarg username: the username of the user to look for.
    :type username: string or None
    :kwarg email: the email or one of the email of the user to look for
    :type email: string or None
    :kwarg token: the token of the user to look for
    :type token: string or None
    :kwarg pattern: a pattern to search the users with.
    :type pattern: string or None
    :return: A single User object if any of username, email or token is
        specified, a list of User objects otherwise.
    :rtype: User or [User]

    '''
    query = session.query(
        model.User
    )

    if username is not None:
        query = query.filter(
            model.User.user == username
        )

    if email is not None:
        query = query.filter(
            model.UserEmail.user_id == model.User.id
        ).filter(
            model.UserEmail.email == email
        )

    if token is not None:
        query = query.filter(
            model.User.token == token
        )

    if pattern:
        pattern = pattern.replace('*', '%')
        query = query.filter(
            model.User.user.like(pattern)
        )

    if any([username, email, token]):
        output = query.first()
    else:
        output = query.all()

    return output


def add_issue_comment(session, issue, comment, user, ticketfolder):
    ''' Add a comment to an issue. '''
    user_obj = search_user(session, username=user)
    if not user_obj:
        user_obj = search_user(session, email=user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    issue_comment = model.IssueComment(
        issue_uid=issue.uid,
        comment=comment,
        user_id=user_obj.id,
    )
    session.add(issue_comment)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    progit.lib.git.update_git_ticket(
        issue, repo=issue.project, ticketfolder=ticketfolder)

    progit.notify.notify_new_comment(issue_comment)

    return 'Comment added'


def add_issue_tag(session, issue, tag, user, ticketfolder):
    ''' Add a tag to an issue. '''
    user_obj = search_user(session, username=user)
    if not user_obj:
        user_obj = search_user(session, email=user)

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
        issue_uid=issue.uid,
        tag=tagobj.tag,
    )
    session.add(issue_tag)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    progit.lib.gitupdate_git_ticket(
        issue, repo=issue.project, ticketfolder=ticketfolder)

    return 'Tag added'


def add_issue_assignee(session, issue, assignee, user, ticketfolder):
    ''' Add an assignee to an issue, in other words, assigned an issue. '''
    if assignee is None:
        issue.assignee_id = None
        session.add(issue)
        session.commit()
        progit.lib.git.update_git_ticket(
            issue, repo=issue.project, ticketfolder=ticketfolder)

        progit.notify.notify_assigned_issue(issue, None, user)
        return 'Assignee reset'

    user_obj = search_user(session, username=user)
    if not user_obj:
        user_obj = search_user(session, email=user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    # Validate the assignee
    user_obj = search_user(session, user=assignee)
    if not user_obj:
        user_obj = search_user(session, email=assignee)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % assignee
        )

    if issue.assignee_id != user_obj.id:
        issue.assignee_id = user_obj.id
        session.add(issue)
        session.flush()
        progit.lib.git.update_git_ticket(
            issue, repo=issue.project, ticketfolder=ticketfolder)

        progit.notify.notify_assigned_issue(issue, user_obj, user)

        return 'Issue assigned'


def add_issue_dependency(session, issue, issue_blocked, user, ticketfolder):
    ''' Add a dependency between two issues. '''
    user_obj = search_user(session, username=user)
    if not user_obj:
        user_obj = search_user(session, email=user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    if issue.uid == issue_blocked.uid:
        raise progit.exceptions.ProgitException(
            'An issue cannot depend on itself'
        )

    if issue_blocked not in issue.children:
        i2i = model.IssueToIssue(
            parent_issue_id=issue_blocked.uid,
            child_issue_id=issue.uid
        )
        session.add(i2i)
        # Make sure we won't have SQLAlchemy error before we create the repo
        session.flush()
        progit.lib.git.update_git_ticket(
            issue, repo=issue.project, ticketfolder=ticketfolder)
        progit.lib.git.update_git_ticket(
            issue_blocked,
            repo=issue_blocked.project,
            ticketfolder=ticketfolder)

        #progit.notify.notify_assigned_issue(issue, user_obj)
        #progit.notify.notify_assigned_issue(issue_blocked, user_obj)

        return 'Dependency added'


def remove_issue_tags(session, project, tags):
    ''' Removes the specified tag of a project. '''

    if not isinstance(tags, list):
        tags = [tags]

    issues = search_issues(session, project, closed=False, tags=tags)
    issues.extend(search_issues(session, project, closed=True, tags=tags))

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

    issues = search_issues(session, project, closed=False, tags=old_tags)
    issues.extend(search_issues(session, project, closed=True, tags=old_tags))

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
                    issue_id=issue[0].uid,
                    tag=new_tag
                )
                session.add(issue_tag)
                msgs.append('Edited tag: %s to %s' % (old_tag, new_tag))

    return msgs


def add_user_to_project(session, project, user):
    ''' Add a specified user to a specified project. '''
    user_obj = search_user(session, username=user)
    if not user_obj:
        user_obj = search_user(session, email=user)

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
    user_obj = search_user(session, username=user)
    if not user_obj:
        user_obj = search_user(session, email=user)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % user
        )

    pr_comment = model.PullRequestComment(
        pull_request_uid=request.uid,
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


def new_project(session, user, name, gitfolder, docfolder, ticketfolder,
                description=None, parent_id=None):
    ''' Create a new project based on the information provided.
    '''
    gitrepo = os.path.join(gitfolder, '%s.git' % name)
    if os.path.exists(gitrepo):
        raise progit.exceptions.RepoExistsException(
            'The project repo "%s" already exists' % name
        )

    user_obj = search_user(session, username=user)

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
    user_obj = search_user(session, username=user)

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

    progit.lib.git.update_git_ticket(
        issue, repo=repo, ticketfolder=ticketfolder)

    progit.notify.notify_new_issue(issue)

    return 'Issue created'


def new_pull_request(session, repo_from, branch_from,
                     repo_to, branch_to, title, user):
    ''' Create a new pull request on the specified repo. '''
    user_obj = search_user(session, username=user)

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

    progit.lib.git.update_git_ticket(
        issue, repo=issue.project, ticketfolder=ticketfolder)

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

    user_obj = search_user(session, username=user)

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


def search_issues(
        session, repo, issueid=None, status=None, closed=False, tags=None,
        assignee=None, author=None):
    ''' Retrieve one or more issues associated to a project with the given
    criterias.

    Watch out that the closed argument is incompatible with the status
    argument. The closed argument will return all the issues whose status
    is not 'Open', otherwise it will return the issues having the specified
    status.
    The `tags` argument can be used to filter the issues returned based on
    a certain tag.
    If the `issueid` argument is specified a single Issue object (or None)
    will be returned instead of a list of Issue objects.

    :arg session: the session to use to connect to the database.
    :arg repo: a Project object to which the issues should be associated
    :type repo: progit.lib.model.Project
    :kwarg issueid: the identifier of the issue to look for
    :type issueid: int or None
    :kwarg status: the status of the issue to look for (incompatible with
        the `closed` argument).
    :type status: str or None
    :kwarg closed: a boolean indicating whether the issue to retrieve are
        closed or open (incompatible with the `status` argument).
    :type closed: bool or None
    :kwarg tags: a tag the issue(s) returned should be associated with
    :type tags: str or list(str) or None
    :return: A single Issue object if issueid is specified, a list of Project
        objects otherwise.
    :rtype: Project or [Project]

    '''
    query = session.query(
        model.Issue
    ).filter(
        model.Issue.project_id == repo.id
    ).order_by(
        model.Issue.id
    )

    if issueid is not None:
        query = query.filter(
            model.Issue.id == issueid
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
        if isinstance(tags, basestring):
            tags = [tags]

        query = query.filter(
            model.Issue.uid == model.TagIssue.issue_uid
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

    if issueid is not None:
        output = query.first()
    else:
        output = query.all()

    return output


def get_tags_of_project(session, project, pattern=None):
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

    if pattern:
        query = query.filter(
            model.Tag.tag.ilike(pattern.replace('*', '%'))
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


def search_pull_requests(
        session, requestid=None, project_id=None, project_id_from=None,
        status=None):
    ''' Retrieve the specified issue
    '''

    query = session.query(
        model.PullRequest
    ).order_by(
        model.PullRequest.id
    )

    if requestid:
        query = query.filter(
            model.PullRequest.id == requestid
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

    if requestid:
        output = query.first()
    else:
        output = query.all()

    return output


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


def set_up_user(session, username, fullname, user_email):
    ''' Set up a new user into the database or update its information. '''
    user = search_user(session, username=username)
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
        user = search_user(session, username=user)

    message = 'Nothing to update'

    if ssh_key != user.public_ssh_key:
        user.public_ssh_key = ssh_key
        session.add(user)
        session.flush()
        message = 'Public ssh key updated'

    return message


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
