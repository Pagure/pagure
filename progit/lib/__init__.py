# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


import datetime
import os
import shutil
import tempfile
import uuid

import sqlalchemy
import sqlalchemy.schema
from datetime import timedelta
from sqlalchemy import func
from sqlalchemy.orm import aliased
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import SQLAlchemyError

import pygit2

import progit.exceptions
import progit.lib.git
import progit.lib.notify
from progit.lib import model


def __get_user(session, key):
    """ Searches for a user in the database for a given username or email.
    """
    user_obj = search_user(session, username=key)
    if not user_obj:
        user_obj = search_user(session, email=key)

    if not user_obj:
        raise progit.exceptions.ProgitException(
            'No user "%s" found' % key
        )

    return user_obj


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


def add_issue_comment(session, issue, comment, user, ticketfolder,
                      notify=True):
    ''' Add a comment to an issue. '''
    user_obj = __get_user(session, user)

    issue_comment = model.IssueComment(
        issue_uid=issue.uid,
        comment=comment,
        user_id=user_obj.id,
    )
    session.add(issue_comment)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.commit()

    progit.lib.git.update_git(
        issue, repo=issue.project, repofolder=ticketfolder)

    if notify:
        progit.lib.notify.notify_new_comment(issue_comment, user=user_obj)

    return 'Comment added'


def add_issue_tag(session, issue, tag, user, ticketfolder):
    ''' Add a tag to an issue. '''
    user_obj = __get_user(session, user)

    for tag_issue in issue.tags:
        if tag_issue.tag == tag:
            raise progit.exceptions.ProgitException(
                'Tag already present: %s' % tag)

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

    progit.lib.git.update_git(
        issue, repo=issue.project, repofolder=ticketfolder)

    return 'Tag added'


def add_issue_assignee(session, issue, assignee, user, ticketfolder):
    ''' Add an assignee to an issue, in other words, assigned an issue. '''
    user_obj = __get_user(session, user)

    if assignee is None and issue.assignee != None:
        issue.assignee_id = None
        session.add(issue)
        session.commit()
        progit.lib.git.update_git(
            issue, repo=issue.project, repofolder=ticketfolder)

        progit.lib.notify.notify_assigned_issue(issue, None, user_obj)
        return 'Assignee reset'
    elif assignee is None and issue.assignee == None:
        return

    # Validate the assignee
    assignee_obj = __get_user(session, assignee)

    if issue.assignee_id != assignee_obj.id:
        issue.assignee_id = assignee_obj.id
        session.add(issue)
        session.flush()
        progit.lib.git.update_git(
            issue, repo=issue.project, repofolder=ticketfolder)

        print user_obj, assignee_obj
        progit.lib.notify.notify_assigned_issue(
            issue, assignee_obj, user_obj)

        return 'Issue assigned'


def add_issue_dependency(session, issue, issue_blocked, user, ticketfolder):
    ''' Add a dependency between two issues. '''
    user_obj = __get_user(session, user)

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
        progit.lib.git.update_git(
            issue,
            repo=issue.project,
            repofolder=ticketfolder)
        progit.lib.git.update_git(
            issue_blocked,
            repo=issue_blocked.project,
            repofolder=ticketfolder)

        #progit.lib.notify.notify_assigned_issue(issue, user_obj)
        #progit.lib.notify.notify_assigned_issue(issue_blocked, user_obj)

        return 'Dependency added'


def remove_issue_dependency(session, issue, issue_blocked, user, ticketfolder):
    ''' Remove a dependency between two issues. '''
    user_obj = __get_user(session, user)

    if issue.uid == issue_blocked.uid:
        raise progit.exceptions.ProgitException(
            'An issue cannot depend on itself'
        )

    if issue_blocked in issue.children:
        for child in issue.children:
            if child.uid == issue_blocked.uid:
                issue.children.remove(child)

        # Make sure we won't have SQLAlchemy error before we create the repo
        session.flush()
        progit.lib.git.update_git(
            issue,
            repo=issue.project,
            repofolder=ticketfolder)
        progit.lib.git.update_git(
            issue_blocked,
            repo=issue_blocked.project,
            repofolder=ticketfolder)

        #progit.lib.notify.notify_assigned_issue(issue, user_obj)
        #progit.lib.notify.notify_assigned_issue(issue_blocked, user_obj)

        return 'Dependency removed'


def remove_tags(session, project, tags, ticketfolder):
    ''' Removes the specified tag of a project. '''

    if not isinstance(tags, list):
        tags = [tags]

    issues = search_issues(session, project, closed=False, tags=tags)
    issues.extend(search_issues(session, project, closed=True, tags=tags))

    msgs = []
    if not issues:
        raise progit.exceptions.ProgitException(
            'No issue found with the tags: %s' % ', '.join(tags))
    else:
        for issue in issues:
            for issue_tag in issue.tags:
                if issue_tag.tag in tags:
                    tag = issue_tag.tag
                    session.delete(issue_tag)
                    msgs.append('Removed tag: %s' % tag)
            progit.lib.git.update_git(
                issue, repo=issue.project, repofolder=ticketfolder)

    return msgs


def remove_tags_issue(session, issue, tags, ticketfolder):
    ''' Removes the specified tag(s) of a issue. '''

    if isinstance(tags, basestring):
        tags = [tags]

    msgs = []
    for issue_tag in issue.tags:
        if issue_tag.tag in tags:
            tag = issue_tag.tag
            session.delete(issue_tag)
            msgs.append('Removed tag: %s' % tag)

    progit.lib.git.update_git(
        issue, repo=issue.project, repofolder=ticketfolder)

    return msgs


def edit_issue_tags(session, project, old_tag, new_tag, ticketfolder):
    ''' Removes the specified tag of a project. '''

    if old_tag == new_tag:
        raise progit.exceptions.ProgitException(
            'Old tag: "%s" is the same as new tag "%s", nothing to change'
            % (old_tag, new_tag))

    issues = search_issues(session, project, closed=False, tags=old_tag)
    issues.extend(search_issues(session, project, closed=True, tags=old_tag))

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
            for issue_tag in issue.tags:
                if issue_tag.tag == old_tag:
                    session.delete(issue_tag)

            if add:
                # Add the new one
                issue_tag = model.TagIssue(
                    issue_uid=issue.uid,
                    tag=new_tag
                )
                session.add(issue_tag)
                msgs.append('Edited tag: %s to %s' % (old_tag, new_tag))
            progit.lib.git.update_git(
                issue, repo=issue.project, repofolder=ticketfolder)

    return msgs


def add_user_to_project(session, project, user):
    ''' Add a specified user to a specified project. '''
    user_obj = __get_user(session, user)

    project_user = model.ProjectUser(
        project_id=project.id,
        user_id=user_obj.id,
    )
    session.add(project_user)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    return 'User added'


def add_pull_request_comment(session, request, commit, filename, row,
                             comment, user, requestfolder):
    ''' Add a comment to a pull-request. '''
    user_obj = __get_user(session, user)

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

    progit.lib.git.update_git(
        request, repo=request.repo, repofolder=requestfolder)

    return 'Comment added'


def new_project(session, user, name,
                gitfolder, docfolder, ticketfolder, requestfolder,
                description=None, parent_id=None):
    ''' Create a new project based on the information provided.
    '''
    gitrepo = os.path.join(gitfolder, '%s.git' % name)
    if os.path.exists(gitrepo):
        raise progit.exceptions.RepoExistsException(
            'The project repo "%s" already exists' % name
        )

    user_obj = __get_user(session, user)

    project = model.Project(
        name=name,
        description=description,
        user_id=user_obj.id,
        parent_id=parent_id
    )
    session.add(project)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.commit()

    pygit2.init_repository(gitrepo, bare=True)

    docrepo = os.path.join(docfolder, project.path)
    if os.path.exists(docrepo):
        shutil.rmtree(gitrepo)
        raise progit.exceptions.RepoExistsException(
            'The docs repo "%s" already exists' % project.path
        )
    pygit2.init_repository(docrepo, bare=True)

    ticketrepo = os.path.join(ticketfolder, project.path)
    if os.path.exists(ticketrepo):
        shutil.rmtree(gitrepo)
        shutil.rmtree(docrepo)
        raise progit.exceptions.RepoExistsException(
            'The tickets repo "%s" already exists' % project.path
        )
    pygit2.init_repository(ticketrepo, bare=True)

    requestrepo = os.path.join(requestfolder, project.path)
    if os.path.exists(requestrepo):
        shutil.rmtree(gitrepo)
        shutil.rmtree(docrepo)
        shutil.rmtree(ticketrepo)
        raise progit.exceptions.RepoExistsException(
            'The requests repo "%s" already exists' % project.path
        )
    pygit2.init_repository(requestrepo, bare=True)

    return 'Project "%s" created' % name


def new_issue(session, repo, title, content, user, ticketfolder,
              issue_id=None, issue_uid=None, private=False, status=None,
              notify=True):
    ''' Create a new issue for the specified repo. '''
    user_obj = __get_user(session, user)

    issue = model.Issue(
        id=issue_id or get_next_id(session, repo.id),
        project_id=repo.id,
        title=title,
        content=content,
        user_id=user_obj.id,
        uid=issue_uid or uuid.uuid4().hex,
        private=private,
    )

    if status is not None:
        issue.status = status

    session.add(issue)
    # Make sure we won't have SQLAlchemy error before we create the issue
    session.flush()

    progit.lib.git.update_git(
        issue, repo=repo, repofolder=ticketfolder)

    if notify:
        progit.lib.notify.notify_new_issue(issue, user=user_obj)

    return 'Issue created'


def new_pull_request(session, repo_from, branch_from,
                     repo_to, branch_to, title, user,
                     requestfolder, requestuid=None, requestid=None,
                     status=True, notify=True):
    ''' Create a new pull request on the specified repo. '''
    user_obj = __get_user(session, user)

    request = model.PullRequest(
        id=requestid or get_next_id(session, repo_to.id),
        uid=requestuid or uuid.uuid4().hex,
        project_id=repo_to.id,
        project_id_from=repo_from.id,
        branch=branch_to,
        branch_from=branch_from,
        title=title,
        user_id=user_obj.id,
        status=status,
    )
    session.add(request)
    # Make sure we won't have SQLAlchemy error before we create the request
    session.flush()

    progit.lib.git.update_git(
        request, repo=request.repo, repofolder=requestfolder)

    if notify:
        progit.lib.notify.notify_new_pull_request(request)

    return 'Request created'


def edit_issue(session, issue, ticketfolder,
               title=None, content=None, status=None, private=False):
    ''' Edit the specified issue.
    '''
    if status == 'Fixed' and issue.parents:
        for parent in issue.parents:
            if parent.status == 'Open':
                raise progit.exceptions.ProgitException(
                    'You cannot close a ticket that has ticket '
                    'depending that are still open.')

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
    if private in [True, False] and private != issue.private:
        issue.private = private
        edit.append('private')

    progit.lib.git.update_git(
        issue, repo=issue.project, repofolder=ticketfolder)

    if edit:
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
        return 'Edited successfully settings of repo: %s' % repo.fullname


def fork_project(session, user, repo, gitfolder,
                 forkfolder, docfolder, ticketfolder, requestfolder):
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

    user_obj = __get_user(session, user)

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

    docrepo = os.path.join(docfolder, project.path)
    if os.path.exists(docrepo):
        shutil.rmtree(forkreponame)
        raise progit.exceptions.RepoExistsException(
            'The docs "%s" already exists' % project.path
        )
    pygit2.init_repository(docrepo, bare=True)

    ticketrepo = os.path.join(ticketfolder, project.path)
    if os.path.exists(ticketrepo):
        shutil.rmtree(forkreponame)
        shutil.rmtree(docrepo)
        raise progit.exceptions.RepoExistsException(
            'The tickets repo "%s" already exists' % project.path
        )
    pygit2.init_repository(ticketrepo, bare=True)

    requestrepo = os.path.join(requestfolder, project.path)
    if os.path.exists(requestrepo):
        shutil.rmtree(forkreponame)
        shutil.rmtree(docrepo)
        shutil.rmtree(ticketrepo)
        raise progit.exceptions.RepoExistsException(
            'The requests repo "%s" already exists' % project.path
        )
    pygit2.init_repository(requestrepo, bare=True)

    return 'Repo "%s" cloned to "%s/%s"' % (repo.name, user, repo.name)


def search_projects(
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
        assignee=None, author=None, private=None, count=False):
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
    :kwarg assignee: the name of the user assigned to the issues to search
    :type assignee: str or None
    :kwarg author: the name of the user who created the issues to search
    :type author: str or None
    :kwarg private: boolean or string to use to include or exclude private
        tickets. Defaults to False.
        If False: private tickets are excluded
        If None: private tickets are included
        If user name is specified: private tickets reported by that user
        are included.
    :type private: False, None or str
    :kwarg count: a boolean to specify if the method should return the list
        of Issues or just do a COUNT query.
    :type count: boolean

    :return: A single Issue object if issueid is specified, a list of Project
        objects otherwise.
    :rtype: Project or [Project]

    '''
    query = session.query(
        sqlalchemy.distinct(model.Issue.id)
    ).filter(
        model.Issue.project_id == repo.id
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
        notags = []
        ytags = []
        for tag in tags:
            if tag.startswith('!'):
                notags.append(tag[1:])
            else:
                ytags.append(tag)

        if ytags:
            query = query.filter(
                model.Issue.uid == model.TagIssue.issue_uid
            ).filter(
                model.TagIssue.tag.in_(ytags)
            )
        if notags:
            sub = session.query(
                model.Issue.uid
            ).filter(
                    model.Issue.uid == model.TagIssue.issue_uid
            ).filter(
                    model.TagIssue.tag.in_(notags)
            )

            query = query.filter(
                ~model.Issue.uid.in_(sub)
            )
    if assignee is not None:
        if str(assignee).lower() not in ['false', '0', 'true', '1']:
            user2 = aliased(model.User)
            if assignee.startswith('!'):
                sub = session.query(
                    model.Issue.uid
                ).filter(
                    model.Issue.assignee_id == user2.id
                ).filter(
                    user2.user == assignee[1:]
                )

                query = query.filter(
                    ~model.Issue.uid.in_(sub)
                )
            else:
                query = query.filter(
                    model.Issue.assignee_id == user2.id
                ).filter(
                    user2.user == assignee
                )
        elif str(assignee).lower() in ['true', '1']:
            query = query.filter(
                model.Issue.assignee_id != None
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

    if private is False:
        query = query.filter(
            model.Issue.private == False
        )
    elif isinstance(private, basestring):
        user2 = aliased(model.User)
        query = query.filter(
            sqlalchemy.or_(
                model.Issue.private == False,
                sqlalchemy.and_(
                    model.Issue.private == True,
                    model.Issue.user_id == user2.id,
                    user2.user == private,
                )
            )
        )

    query = session.query(
        model.Issue
    ).filter(
        model.Issue.id.in_(query.subquery())
    ).order_by(
        model.Issue.id
    )

    if issueid is not None:
        output = query.first()
    elif count:
        output = query.count()
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


def close_pull_request(session, request, user, requestfolder, merged=True):
    ''' Close the provided pull-request.
    '''
    request.status = False
    session.add(request)
    session.flush()

    if merged == True:
        progit.lib.notify.notify_merge_pull_request(request, user)
    else:
        progit.lib.notify.notify_cancelled_pull_request(request, user)

    progit.lib.git.update_git(
        request, repo=request.repo, repofolder=requestfolder)


def get_issue_statuses(session):
    ''' Return the complete list of status an issue can have.
    '''
    output = []
    statuses = session.query(model.StatusIssue).all()
    for status in statuses:
        output.append(status.status)
    return output


def get_issue_comment(session, issue_uid, comment_id):
    ''' Return a specific comment of a specified issue.
    '''
    query = session.query(
        model.IssueComment
    ).filter(
        model.IssueComment.issue_uid == issue_uid
    ).filter(
        model.IssueComment.id == comment_id
    )

    return query.first()


def get_request_comment(session, request_uid, comment_id):
    ''' Return a specific comment of a specified issue.
    '''
    query = session.query(
        model.PullRequestComment
    ).filter(
        model.PullRequestComment.pull_request_uid == request_uid
    ).filter(
        model.PullRequestComment.id == comment_id
    )

    return query.first()


def get_issue_by_uid(session, issue_uid):
    ''' Return the issue corresponding to the specified unique identifier.

    :arg session: the session to use to connect to the database.
    :arg issue_uid: the unique identifier of an issue. This identifier is
        unique accross all projects on this progit instance and should be
        unique accross multiple progit instances as well
    :type issue_uid: str or None

    :return: A single Issue object.
    :rtype: progit.lib.model.Issue

    '''
    query = session.query(
        model.Issue
    ).filter(
        model.Issue.uid == issue_uid
    )
    return query.first()


def get_request_by_uid(session, request_uid):
    ''' Return the request corresponding to the specified unique identifier.

    :arg session: the session to use to connect to the database.
    :arg request_uid: the unique identifier of a request. This identifier is
        unique accross all projects on this progit instance and should be
        unique accross multiple progit instances as well
    :type request_uid: str or None

    :return: A single Issue object.
    :rtype: progit.lib.model.PullRequest

    '''
    query = session.query(
        model.PullRequest
    ).filter(
        model.PullRequest.uid == request_uid
    )
    return query.first()


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

    return user


def update_user_ssh(session, user, ssh_key):
    ''' Set up a new user into the database or update its information. '''
    if isinstance(user, basestring):
        user = __get_user(session, user)

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
        import urllib
        import hashlib
        query = urllib.urlencode({'s': size, 'd': default})
        hash = hashlib.sha256(openid).hexdigest()
        return "https://seccdn.libravatar.org/avatar/%s?%s" % (hash, query)


def update_tags_issue(session, issue, tags, username, ticketfolder):
    """ Update the tags of a specified issue (adding or removing them).

    """
    if isinstance(tags, basestring):
        tags = [tags]

    toadd = set(tags) - set(issue.tags_text)
    torm = set(issue.tags_text) - set(tags)
    messages = []
    for tag in toadd:
        messages.append(
            add_issue_tag(
                session,
                issue=issue,
                tag=tag,
                user=username,
                ticketfolder=ticketfolder,
            )
        )

    if torm:
        messages.extend(
            remove_tags_issue(
                session,
                issue=issue,
                tags=torm,
                ticketfolder=ticketfolder,
            )
        )
    session.commit()

    return messages


def update_dependency_issue(
        session, repo, issue, depends, username, ticketfolder):
    """ Update the dependency of a specified issue (adding or removing them)

    """
    if isinstance(depends, basestring):
        depends = [depends]

    toadd = set(depends) - set(issue.depends_text)
    torm = set(issue.depends_text) - set(depends)
    messages = []

    # Add issue depending
    for depend in toadd:
        issue_depend = search_issues(session, repo, issueid=depend)
        if issue_depend is None:
            continue
        if issue_depend.id in issue.depends_text:  # pragma: no cover
            # we should never be in this case but better safe than sorry...
            continue

        messages.append(
            add_issue_dependency(
                session,
                issue=issue_depend,
                issue_blocked=issue,
                user=username,
                ticketfolder=ticketfolder,
            )
        )

    # Remove issue depending
    for depend in torm:
        issue_depend = search_issues(session, repo, issueid=depend)
        if issue_depend is None:  # pragma: no cover
            # We cannot test this as it would mean we managed to put in an
            # invalid ticket as dependency earlier
            continue
        if issue_depend.id not in issue.depends_text:  # pragma: no cover
            # we should never be in this case but better safe than sorry...
            continue

        messages.append(
            remove_issue_dependency(
                session,
                issue=issue,
                issue_blocked=issue_depend,
                user=username,
                ticketfolder=ticketfolder,
            )
        )

    session.commit()
    return messages


def update_blocked_issue(
        session, repo, issue, blocks, username, ticketfolder):
    """ Update the upstream dependency of a specified issue (adding or
    removing them)

    """
    if isinstance(blocks, basestring):
        blocks = [blocks]

    toadd = set(blocks) - set(issue.blocks_text)
    torm = set(issue.blocks_text) - set(blocks)
    messages = []

    # Add issue blocked
    for block in toadd:
        issue_block = search_issues(session, repo, issueid=block)
        if issue_block is None:
            continue
        if issue_block.id in issue.blocks_text:  # pragma: no cover
            # we should never be in this case but better safe than sorry...
            continue

        messages.append(
            add_issue_dependency(
                session,
                issue=issue,
                issue_blocked=issue_block,
                user=username,
                ticketfolder=ticketfolder,
            )
        )
        session.commit()

    # Remove issue blocked
    for block in torm:
        issue_block = search_issues(session, repo, issueid=block)
        if issue_block is None:  # pragma: no cover
            # We cannot test this as it would mean we managed to put in an
            # invalid ticket as dependency earlier
            continue

        if issue_block.id not in issue.blocks_text:  # pragma: no cover
            # we should never be in this case but better safe than sorry...
            continue

        messages.append(
            remove_issue_dependency(
                session,
                issue=issue_block,
                issue_blocked=issue,
                user=username,
                ticketfolder=ticketfolder,
            )
        )

    session.commit()
    return messages
