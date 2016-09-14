# -*- coding: utf-8 -*-

"""
 (c) 2014-2016 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

# pylint: disable=too-many-branches
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# pylint: disable=too-many-lines


try:
    import simplejson as json
except ImportError:
    import json

import datetime
import markdown
import os
import shutil
import tempfile
import urlparse
import uuid

import bleach
import redis
import six
import sqlalchemy
import sqlalchemy.schema
from datetime import timedelta
from sqlalchemy import func
from sqlalchemy import asc
from sqlalchemy.orm import aliased
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import SQLAlchemyError

import pygit2

import pagure.exceptions
import pagure.lib.git
import pagure.lib.login
import pagure.lib.notify
import pagure.pfmarkdown
from pagure.lib import model


REDIS = None
PAGURE_CI = None


def set_redis(host, port, dbname):
    """ Set the redis connection with the specified information. """
    global REDIS
    pool = redis.ConnectionPool(host=host, port=port, db=dbname)
    REDIS = redis.StrictRedis(connection_pool=pool)


def set_pagure_ci(services):
    """ Set the list of CI services supported by this pagure instance. """
    global PAGURE_CI
    PAGURE_CI = services


def get_user(session, key):
    """ Searches for a user in the database for a given username or email.
    """
    user_obj = search_user(session, username=key)
    if not user_obj:
        user_obj = search_user(session, email=key)

    if not user_obj:
        raise pagure.exceptions.PagureException(
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
    if db_url.startswith('sqlite'):
        engine = sqlalchemy.create_engine(
            db_url, echo=debug, pool_recycle=pool_recycle)
    else:
        engine = sqlalchemy.create_engine(
            db_url, echo=debug, pool_recycle=pool_recycle,
            client_encoding='utf8')
    scopedsession = scoped_session(sessionmaker(bind=engine))
    model.BASE.metadata.bind = scopedsession
    return scopedsession


def get_next_id(session, projectid):
    """ Returns the next identifier of a project ticket or pull-request
    based on the identifier already in the database.
    """
    query1 = session.query(
        func.max(model.Issue.id)
    ).filter(
        model.Issue.project_id == projectid
    )

    query2 = session.query(
        func.max(model.PullRequest.id)
    ).filter(
        model.PullRequest.project_id == projectid
    )

    nid = max([el[0] for el in query1.union(query2).all()]) or 0

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
    ).order_by(
        model.User.user
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


def create_user_ssh_keys_on_disk(user, gitolite_keydir):
    ''' Create the ssh keys for the user on the specific folder.

    This is the method allowing to have multiple ssh keys per user.
    '''
    if gitolite_keydir:
        # First remove any old keyfiles for the user
        # Assumption: we populated the keydir. This means that files
        #  will be in 0/<username>.pub, ..., and not in any deeper
        #  directory structures. Also, this means that if a user
        #  had 5 lines, they will be up to at most keys_4/<username>.pub,
        #  meaning that if a user is not in keys_<i>/<username>.pub, with
        #  i being any integer, the user is most certainly not in
        #  keys_<i+1>/<username>.pub.
        i = 0
        keyline_file = os.path.join(gitolite_keydir,
                                    'keys_%i' % i,
                                    '%s.pub' % user.user)
        while os.path.exists(keyline_file):
            os.unlink(keyline_file)
            i += 1
            keyline_file = os.path.join(gitolite_keydir,
                                        'keys_%i' % i,
                                        '%s.pub' % user.user)

        # Now let's create new keyfiles for the user
        keys = user.public_ssh_key.split('\n')
        for i in range(len(keys)):
            if not keys[i]:
                continue
            keyline_dir = os.path.join(gitolite_keydir, 'keys_%i' % i)
            if not os.path.exists(keyline_dir):
                os.mkdir(keyline_dir)
            keyfile = os.path.join(keyline_dir, '%s.pub' % user.user)
            with open(keyfile, 'w') as stream:
                stream.write(keys[i].strip().encode('UTF-8'))


def add_issue_comment(session, issue, comment, user, ticketfolder,
                      notify=True, date_created=None, notification=False):
    ''' Add a comment to an issue. '''
    user_obj = get_user(session, user)

    issue_comment = model.IssueComment(
        issue_uid=issue.uid,
        comment=comment,
        user_id=user_obj.id,
        date_created=date_created,
        notification=notification,
    )
    session.add(issue_comment)
    # Make sure we won't have SQLAlchemy error before we continue
    session.commit()

    pagure.lib.git.update_git(
        issue, repo=issue.project, repofolder=ticketfolder)

    if notify:
        pagure.lib.notify.notify_new_comment(issue_comment, user=user_obj)

    if not issue.private:
        pagure.lib.notify.log(
            issue.project,
            topic='issue.comment.added',
            msg=dict(
                issue=issue.to_json(public=True),
                project=issue.project.to_json(public=True),
                agent=user_obj.username,
            ),
            redis=REDIS,
        )

    if REDIS:
        if issue.private:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps({
                'issue': 'private',
                'comment_id': issue_comment.id,
            }))
        else:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps({
                'comment_id': issue_comment.id,
                'issue_id': issue.id,
                'project': issue.project.fullname,
                'comment_added': text2markdown(issue_comment.comment),
                'comment_user': issue_comment.user.user,
                'avatar_url': avatar_url_from_openid(
                    issue_comment.user.default_email, size=16),
                'comment_date': issue_comment.date_created.strftime(
                    '%Y-%m-%d %H:%M:%S'),
                'notification': notification,
            }))

    return 'Comment added'


def add_tag_obj(session, obj, tags, user, ticketfolder):
    ''' Add a tag to an object (either an issue or a project). '''
    user_obj = get_user(session, user)

    if isinstance(tags, basestring):
        tags = [tags]

    added_tags = []
    for objtag in tags:
        objtag = objtag.strip()
        known = False
        for tagobj in obj.tags:
            if tagobj.tag == objtag:
                known = True

        if known:
            continue

        tagobj = get_tag(session, objtag)
        if not tagobj:
            tagobj = model.Tag(tag=objtag)
            session.add(tagobj)
            session.flush()

        if isinstance(obj, model.Issue):
            dbobjtag = model.TagIssue(
                issue_uid=obj.uid,
                tag=tagobj.tag,
            )
        if isinstance(obj, model.Project):
            dbobjtag = model.TagProject(
                project_id=obj.id,
                tag=tagobj.tag,
            )

        session.add(dbobjtag)
        # Make sure we won't have SQLAlchemy error before we continue
        session.flush()
        added_tags.append(tagobj.tag)

    if isinstance(obj, model.Issue):
        pagure.lib.git.update_git(
            obj, repo=obj.project, repofolder=ticketfolder)

        if not obj.private:
            pagure.lib.notify.log(
                obj.project,
                topic='issue.tag.added',
                msg=dict(
                    issue=obj.to_json(public=True),
                    project=obj.project.to_json(public=True),
                    tags=added_tags,
                    agent=user_obj.username,
                ),
                redis=REDIS,
            )

        # Send notification for the event-source server
        if REDIS:
            REDIS.publish('pagure.%s' % obj.uid, json.dumps(
                {'added_tags': added_tags}))

    if added_tags:
        return 'Tag added: %s' % ', '.join(added_tags)
    else:
        return 'Nothing to add'


def add_issue_assignee(session, issue, assignee, user, ticketfolder,
                       notify=True):
    ''' Add an assignee to an issue, in other words, assigned an issue. '''
    user_obj = get_user(session, user)

    if assignee is None and issue.assignee is not None:
        issue.assignee_id = None
        session.add(issue)
        session.commit()
        pagure.lib.git.update_git(
            issue, repo=issue.project, repofolder=ticketfolder)

        if notify:
            pagure.lib.notify.notify_assigned_issue(issue, None, user_obj)

        if not issue.private:
            pagure.lib.notify.log(
                issue.project,
                topic='issue.assigned.reset',
                msg=dict(
                    issue=issue.to_json(public=True),
                    project=issue.project.to_json(public=True),
                    agent=user_obj.username,
                ),
                redis=REDIS,
            )

        # Send notification for the event-source server
        if REDIS:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps(
                {'unassigned': '-'}))

        return 'Assignee reset'
    elif assignee is None and issue.assignee is None:
        return

    # Validate the assignee
    assignee_obj = get_user(session, assignee)

    if issue.assignee_id != assignee_obj.id:
        issue.assignee_id = assignee_obj.id
        session.add(issue)
        session.flush()
        pagure.lib.git.update_git(
            issue, repo=issue.project, repofolder=ticketfolder)
        if notify:
            pagure.lib.notify.notify_assigned_issue(
                issue, assignee_obj, user_obj)

        if not issue.private:
            pagure.lib.notify.log(
                issue.project,
                topic='issue.assigned.added',
                msg=dict(
                    issue=issue.to_json(public=True),
                    project=issue.project.to_json(public=True),
                    agent=user_obj.username,
                ),
                redis=REDIS,
            )

        # Send notification for the event-source server
        if REDIS:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps(
                {'assigned': assignee_obj.to_json(public=True)}))

        return 'Issue assigned'


def add_pull_request_assignee(
        session, request, assignee, user, requestfolder):
    ''' Add an assignee to a request, in other words, assigned an issue. '''
    get_user(session, assignee)
    user_obj = get_user(session, user)

    if assignee is None and request.assignee is not None:
        request.assignee_id = None
        session.add(request)
        session.commit()
        pagure.lib.git.update_git(
            request, repo=request.project, repofolder=requestfolder)

        pagure.lib.notify.notify_assigned_request(request, None, user_obj)
        pagure.lib.notify.log(
            request.project,
            topic='request.assigned.reset',
            msg=dict(
                request=request.to_json(public=True),
                project=request.project.to_json(public=True),
                agent=user_obj.username,
            ),
            redis=REDIS,
        )

        return 'Request reset'
    elif assignee is None and request.assignee is None:
        return

    # Validate the assignee
    assignee_obj = get_user(session, assignee)

    if request.assignee_id != assignee_obj.id:
        request.assignee_id = assignee_obj.id
        session.add(request)
        session.flush()
        pagure.lib.git.update_git(
            request, repo=request.project, repofolder=requestfolder)

        pagure.lib.notify.notify_assigned_request(
            request, assignee_obj, user_obj)

        pagure.lib.notify.log(
            request.project,
            topic='request.assigned.added',
            msg=dict(
                request=request.to_json(public=True),
                project=request.project.to_json(public=True),
                agent=user_obj.username,
            ),
            redis=REDIS,
        )

        return 'Request assigned'


def add_issue_dependency(
        session, issue, issue_blocked, user, ticketfolder):
    ''' Add a dependency between two issues. '''
    user_obj = get_user(session, user)

    if issue.uid == issue_blocked.uid:
        raise pagure.exceptions.PagureException(
            'An issue cannot depend on itself'
        )

    if issue_blocked not in issue.children:
        i2i = model.IssueToIssue(
            parent_issue_id=issue_blocked.uid,
            child_issue_id=issue.uid
        )
        session.add(i2i)
        # Make sure we won't have SQLAlchemy error before we continue
        session.flush()
        pagure.lib.git.update_git(
            issue,
            repo=issue.project,
            repofolder=ticketfolder)
        pagure.lib.git.update_git(
            issue_blocked,
            repo=issue_blocked.project,
            repofolder=ticketfolder)

        #pagure.lib.notify.notify_assigned_issue(issue, user_obj)
        #pagure.lib.notify.notify_assigned_issue(issue_blocked, user_obj)

        if not issue.private:
            pagure.lib.notify.log(
                issue.project,
                topic='issue.dependency.added',
                msg=dict(
                    issue=issue.to_json(public=True),
                    project=issue.project.to_json(public=True),
                    added_dependency=issue_blocked.id,
                    agent=user_obj.username,
                ),
                redis=REDIS,
            )

        # Send notification for the event-source server
        if REDIS:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps({
                'added_dependency': issue_blocked.id,
                'issue_uid': issue.uid,
                'type': 'children',
            }))
            REDIS.publish('pagure.%s' % issue_blocked.uid, json.dumps({
                'added_dependency': issue.id,
                'issue_uid': issue_blocked.uid,
                'type': 'parent',
            }))

        return 'Dependency added'


def remove_issue_dependency(
        session, issue, issue_blocked, user, ticketfolder):
    ''' Remove a dependency between two issues. '''
    user_obj = get_user(session, user)

    if issue.uid == issue_blocked.uid:
        raise pagure.exceptions.PagureException(
            'An issue cannot depend on itself'
        )

    if issue_blocked in issue.children:
        child_del = []
        for child in issue.children:
            if child.uid == issue_blocked.uid:
                child_del.append(child.id)
                issue.children.remove(child)

        # Make sure we won't have SQLAlchemy error before we continue
        session.flush()
        pagure.lib.git.update_git(
            issue,
            repo=issue.project,
            repofolder=ticketfolder)
        pagure.lib.git.update_git(
            issue_blocked,
            repo=issue_blocked.project,
            repofolder=ticketfolder)

        #pagure.lib.notify.notify_assigned_issue(issue, user_obj)
        #pagure.lib.notify.notify_assigned_issue(issue_blocked, user_obj)

        if not issue.private:
            pagure.lib.notify.log(
                issue.project,
                topic='issue.dependency.removed',
                msg=dict(
                    issue=issue.to_json(public=True),
                    project=issue.project.to_json(public=True),
                    removed_dependency=child_del,
                    agent=user_obj.username,
                ),
                redis=REDIS,
            )

        # Send notification for the event-source server
        if REDIS:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps({
                'removed_dependency': child_del,
                'issue_uid': issue.uid,
                'type': 'children',
            }))
            REDIS.publish('pagure.%s' % issue_blocked.uid, json.dumps({
                'removed_dependency': issue.id,
                'issue_uid': issue_blocked.uid,
                'type': 'parent',
            }))

        return 'Dependency removed'


def remove_tags(session, project, tags, ticketfolder, user):
    ''' Removes the specified tag of a project. '''
    user_obj = get_user(session, user)

    if not isinstance(tags, list):
        tags = [tags]

    issues = search_issues(session, project, closed=False, tags=tags)
    issues.extend(search_issues(session, project, closed=True, tags=tags))

    msgs = []
    removed_tags = []
    if not issues:
        raise pagure.exceptions.PagureException(
            'No issue found with the tags: %s' % ', '.join(tags))
    else:
        for issue in issues:
            for issue_tag in issue.tags:
                if issue_tag.tag in tags:
                    tag = issue_tag.tag
                    removed_tags.append(tag)
                    session.delete(issue_tag)
                    msgs.append('Removed tag: %s' % tag)
            pagure.lib.git.update_git(
                issue, repo=issue.project, repofolder=ticketfolder)

    pagure.lib.notify.log(
        project,
        topic='project.tag.removed',
        msg=dict(
            project=project.to_json(public=True),
            tags=removed_tags,
            agent=user_obj.username,
        ),
        redis=REDIS,
    )

    return msgs


def remove_tags_obj(
        session, obj, tags, ticketfolder, user):
    ''' Removes the specified tag(s) of a given object. '''
    user_obj = get_user(session, user)

    if isinstance(tags, basestring):
        tags = [tags]

    removed_tags = []
    for objtag in obj.tags:
        if objtag.tag in tags:
            tag = objtag.tag
            removed_tags.append(tag)
            session.delete(objtag)

    if isinstance(obj, model.Issue):
        pagure.lib.git.update_git(
            obj, repo=obj.project, repofolder=ticketfolder)

        pagure.lib.notify.log(
            obj.project,
            topic='issue.tag.removed',
            msg=dict(
                issue=obj.to_json(public=True),
                project=obj.project.to_json(public=True),
                tags=removed_tags,
                agent=user_obj.username,
            ),
            redis=REDIS,
        )

        # Send notification for the event-source server
        if REDIS:
            REDIS.publish('pagure.%s' % obj.uid, json.dumps(
                {'removed_tags': removed_tags}))

    return 'Removed tag: %s' % ', '.join(removed_tags)


def edit_issue_tags(session, project, old_tag, new_tag, ticketfolder, user):
    ''' Removes the specified tag of a project. '''
    user_obj = get_user(session, user)

    if old_tag == new_tag:
        raise pagure.exceptions.PagureException(
            'Old tag: "%s" is the same as new tag "%s", nothing to change'
            % (old_tag, new_tag))

    issues = search_issues(session, project, closed=False, tags=old_tag)
    issues.extend(search_issues(session, project, closed=True, tags=old_tag))

    msgs = []
    if not issues:
        raise pagure.exceptions.PagureException(
            'No issue found with the tags: %s' % old_tag)
    else:
        tagobj = get_tag(session, new_tag)
        if not tagobj:
            tagobj = model.Tag(tag=new_tag)
            session.add(tagobj)
            session.flush()

        for issue in set(issues):
            add = True
            # Drop the old tag
            cnt = 0
            while cnt < len(issue.tags):
                issue_tag = issue.tags[cnt]
                if issue_tag.tag == old_tag:
                    issue.tags.remove(issue_tag)
                    cnt -= 1
                if issue_tag.tag == new_tag:
                    add = False
                cnt += 1
            session.flush()

            # Add the new one
            if add:
                issue_tag = model.TagIssue(
                    issue_uid=issue.uid,
                    tag=tagobj.tag
                )
                session.add(issue_tag)
                session.flush()

            # Update the git version
            pagure.lib.git.update_git(
                issue, repo=issue.project, repofolder=ticketfolder)

        msgs.append('Edited tag: %s to %s' % (old_tag, new_tag))
        pagure.lib.notify.log(
            project,
            topic='project.tag.edited',
            msg=dict(
                project=project.to_json(public=True),
                old_tag=old_tag,
                new_tag=new_tag,
                agent=user_obj.username,
            ),
            redis=REDIS,
        )

    return msgs


def add_user_to_project(session, project, new_user, user):
    ''' Add a specified user to a specified project. '''
    new_user_obj = get_user(session, new_user)
    user_obj = get_user(session, user)

    users = set([user.user for user in project.users])
    users.add(project.user.user)
    if new_user in users:
        raise pagure.exceptions.PagureException(
            'This user is already listed on this project.'
        )

    project_user = model.ProjectUser(
        project_id=project.id,
        user_id=new_user_obj.id,
    )
    session.add(project_user)
    # Make sure we won't have SQLAlchemy error before we continue
    session.flush()

    pagure.lib.notify.log(
        project,
        topic='project.user.added',
        msg=dict(
            project=project.to_json(public=True),
            new_user=new_user_obj.username,
            agent=user_obj.username,
        ),
        redis=REDIS,
    )

    return 'User added'


def add_group_to_project(
        session, project, new_group, user, create=False, is_admin=False):
    ''' Add a specified group to a specified project. '''
    user_obj = search_user(session, username=user)
    if not user_obj:
        raise pagure.exceptions.PagureException(
            'No user %s found.' % user
        )

    group_obj = search_groups(session, group_name=new_group)

    if not group_obj:
        if create:
            group_obj = pagure.lib.model.PagureGroup(
                group_name=new_group,
                group_type='user',
                user_id=user_obj.id,
            )
            session.add(group_obj)
            session.flush()
        else:
            raise pagure.exceptions.PagureException(
                'No group %s found.' % new_group
            )

    if user_obj not in project.users \
            and user_obj != project.user \
            and not is_admin:
        raise pagure.exceptions.PagureException(
            'You are not allowed to add a group of users to this project'
        )

    groups = set([group.group_name for group in project.groups])
    if new_group in groups:
        raise pagure.exceptions.PagureException(
            'This group is already associated to this project.'
        )

    project_group = model.ProjectGroup(
        project_id=project.id,
        group_id=group_obj.id,
    )
    session.add(project_group)
    # Make sure we won't have SQLAlchemy error before we continue
    session.flush()

    pagure.lib.notify.log(
        project,
        topic='project.group.added',
        msg=dict(
            project=project.to_json(public=True),
            new_group=group_obj.group_name,
            agent=user,
        ),
        redis=REDIS,
    )

    return 'Group added'


def add_pull_request_comment(session, request, commit, tree_id, filename,
                             row, comment, user, requestfolder,
                             notify=True, notification=False):
    ''' Add a comment to a pull-request. '''
    user_obj = get_user(session, user)

    pr_comment = model.PullRequestComment(
        pull_request_uid=request.uid,
        commit_id=commit,
        tree_id=tree_id,
        filename=filename,
        line=row,
        comment=comment,
        user_id=user_obj.id,
        notification=notification,
    )
    session.add(pr_comment)
    # Make sure we won't have SQLAlchemy error before we continue
    session.flush()

    pagure.lib.git.update_git(
        request, repo=request.project, repofolder=requestfolder)

    if notify:
        pagure.lib.notify.notify_pull_request_comment(pr_comment, user_obj)

    # Send notification for the event-source server
    if REDIS:
        comment_text = pr_comment.comment
        if not notification:
            comment_text = text2markdown(pr_comment.comment)

        REDIS.publish('pagure.%s' % request.uid, json.dumps({
            'request_id': request.id,
            'comment_added': comment_text,
            'comment_user': pr_comment.user.user,
            'comment_id': pr_comment.id,
            'avatar_url': avatar_url_from_openid(
                pr_comment.user.default_email, size=16),
            'comment_date': pr_comment.date_created.strftime(
                '%Y-%m-%d %H:%M:%S'),
            'commit_id': commit,
            'filename': filename,
            'line': row,
            'notification': notification,
        }))

        # Send notification to the CI server, if the comment added was a
        # notification and the PR is still open
        if notification and request.status == 'Open' \
                and request.project.ci_hook and PAGURE_CI:
            REDIS.publish('pagure.ci', json.dumps({
                'ci_type': request.project.ci_hook.ci_type,
                'pr': request.to_json(public=True, with_comments=False)
            }))

    pagure.lib.notify.log(
        request.project,
        topic='pull-request.comment.added',
        msg=dict(
            pullrequest=request.to_json(public=True),
            agent=user_obj.username,
        ),
        redis=REDIS,
    )

    return 'Comment added'


def edit_comment(session, parent, comment, user,
                 updated_comment, folder):
    ''' Edit a comment. '''
    user_obj = get_user(session, user)
    comment.comment = updated_comment
    comment.edited_on = datetime.datetime.utcnow()
    comment.editor = user_obj

    session.add(comment)
    # Make sure we won't have SQLAlchemy error before we continue
    session.flush()

    pagure.lib.git.update_git(
        parent, repo=parent.project, repofolder=folder)

    topic = 'unknown'
    key = 'unknown'
    id_ = 'unknown'
    if parent.isa == 'pull-request':
        topic = 'pull-request.comment.edited'
        key = 'pullrequest'
        id_ = 'request_id'
    elif parent.isa == 'issue':
        topic = 'issue.comment.edited'
        key = 'issue'
        id_ = 'issue_id'

    pagure.lib.notify.log(
        parent.project,
        topic=topic,
        msg={
            key: parent.to_json(public=True, with_comments=False),
            'project': parent.project.to_json(public=True),
            'comment': comment.to_json(public=True),
            'agent': user_obj.username,
        },
        redis=REDIS,
    )

    if REDIS:
        if parent.isa == 'issue' and comment.parent.private:
            REDIS.publish('pagure.%s' % comment.parent.uid, json.dumps({
                'comment_updated': 'private',
                'comment_id': comment.id,
            }))
        else:
            REDIS.publish('pagure.%s' % parent.uid, json.dumps({
                id_: len(parent.comments),
                'comment_updated': text2markdown(comment.comment),
                'comment_id': comment.id,
                'parent_id': comment.parent.id,
                'comment_editor': user_obj.user,
                'avatar_url': avatar_url_from_openid(
                    comment.user.default_email, size=16),
                'comment_date': comment.edited_on.strftime(
                    '%Y-%m-%d %H:%M:%S'),
            }))

    return "Comment updated"


def add_pull_request_flag(session, request, username, percent, comment, url,
                          uid, user, requestfolder):
    ''' Add a flag to a pull-request. '''
    user_obj = get_user(session, user)

    action = 'added'
    pr_flag = get_pull_request_flag_by_uid(session, uid)
    if pr_flag:
        action = 'updated'
        pr_flag.comment = comment
        pr_flag.percent = percent
        pr_flag.url = url
    else:
        pr_flag = model.PullRequestFlag(
            pull_request_uid=request.uid,
            uid=uid or uuid.uuid4().hex,
            username=username,
            percent=percent,
            comment=comment,
            url=url,
            user_id=user_obj.id,
        )
    session.add(pr_flag)
    # Make sure we won't have SQLAlchemy error before we continue
    session.flush()

    pagure.lib.git.update_git(
        request, repo=request.project, repofolder=requestfolder)

    pagure.lib.notify.log(
        request.project,
        topic='pull-request.flag.%s' % action,
        msg=dict(
            pullrequest=request.to_json(public=True),
            flag=pr_flag.to_json(public=True),
            agent=user_obj.username,
        ),
        redis=REDIS,
    )

    return 'Flag %s' % action


def new_project(session, user, name, blacklist, allowed_prefix,
                gitfolder, docfolder, ticketfolder, requestfolder,
                description=None, url=None, avatar_email=None,
                parent_id=None, add_readme=False, userobj=None,
                prevent_40_chars=False, namespace=None):
    ''' Create a new project based on the information provided.
    '''
    if name in blacklist or (
            namespace and '%s/%s' % (namespace, name) in blacklist):
        raise pagure.exceptions.RepoExistsException(
            'No project "%s" are allowed to be created due to potential '
            'conflicts in URLs with pagure itself' % name
        )

    user_obj = get_user(session, user)
    allowed_prefix = allowed_prefix + [grp for grp in user_obj.groups]

    if namespace and namespace not in allowed_prefix:
        raise pagure.exceptions.PagureException(
            'The namespace of your project must be in the list of allowed '
            'namespaces set by the admins of this pagure instance, or the '
            'name of a group of which you are a member.'
        )

    if len(name) == 40 and prevent_40_chars:
        # We must block project with a name <foo>/<bar> where the length
        # of <bar> is exactly 40 characters long as this would otherwise
        # conflict with the old URL schema used for commit that was
        # <foo>/<commit hash>. To keep backward compatibility, we have an
        # endpoint redirecting <foo>/<commit hash> to <foo>/c/<commit hash>
        # available as an option.
        raise pagure.exceptions.PagureException(
            'Your project name cannot have exactly 40 characters after '
            'the `/`'
        )

    path = name
    if namespace:
        path = '%s/%s' % (namespace, name)

    gitrepo = os.path.join(gitfolder, '%s.git' % path)
    if os.path.exists(gitrepo):
        raise pagure.exceptions.RepoExistsException(
            'The project repo "%s" already exists' % path
        )

    project = model.Project(
        name=name,
        namespace=namespace,
        description=description if description else None,
        url=url if url else None,
        avatar_email=avatar_email if avatar_email else None,
        user_id=user_obj.id,
        parent_id=parent_id,
        hook_token=pagure.lib.login.id_generator(40)
    )
    session.add(project)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    if not add_readme:
        pygit2.init_repository(gitrepo, bare=True)
    else:
        temp_gitrepo_path = tempfile.mkdtemp(prefix='pagure-')
        temp_gitrepo = pygit2.init_repository(temp_gitrepo_path, bare=False)
        author = userobj.fullname or userobj.user
        author_email = userobj.default_email
        if six.PY2:
            author = author.encode('utf-8')
            author_email = author_email.encode('utf-8')
        author = pygit2.Signature(author, author_email)
        content = u"# %s\n\n%s" % (name, description)
        readme_file = os.path.join(temp_gitrepo.workdir, "README.md")
        with open(readme_file, 'wb') as stream:
            stream.write(content.encode('utf-8'))
        temp_gitrepo.index.add_all()
        temp_gitrepo.index.write()
        tree = temp_gitrepo.index.write_tree()
        temp_gitrepo.create_commit(
            'HEAD', author, author, 'Added the README', tree, [])
        pygit2.clone_repository(temp_gitrepo_path, gitrepo, bare=True)
        shutil.rmtree(temp_gitrepo_path)

    http_clone_file = os.path.join(gitrepo, 'git-daemon-export-ok')
    if not os.path.exists(http_clone_file):
        with open(http_clone_file, 'w') as stream:
            pass

    docrepo = os.path.join(docfolder, project.path)
    if os.path.exists(docrepo):
        shutil.rmtree(gitrepo)
        raise pagure.exceptions.RepoExistsException(
            'The docs repo "%s" already exists' % project.path
        )
    pygit2.init_repository(docrepo, bare=True)

    ticketrepo = os.path.join(ticketfolder, project.path)
    if os.path.exists(ticketrepo):
        shutil.rmtree(gitrepo)
        shutil.rmtree(docrepo)
        raise pagure.exceptions.RepoExistsException(
            'The tickets repo "%s" already exists' % project.path
        )
    pygit2.init_repository(
        ticketrepo, bare=True,
        mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP)

    requestrepo = os.path.join(requestfolder, project.path)
    if os.path.exists(requestrepo):
        shutil.rmtree(gitrepo)
        shutil.rmtree(docrepo)
        shutil.rmtree(ticketrepo)
        raise pagure.exceptions.RepoExistsException(
            'The requests repo "%s" already exists' % project.path
        )
    pygit2.init_repository(
        requestrepo, bare=True,
        mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP)

    # create the project in the db
    session.commit()

    pagure.lib.notify.log(
        project,
        topic='project.new',
        msg=dict(
            project=project.to_json(public=True),
            agent=user_obj.username,
        ),
    )

    return 'Project "%s" created' % name


def new_issue(session, repo, title, content, user, ticketfolder,
              issue_id=None, issue_uid=None, private=False, status=None,
              notify=True, date_created=None):
    ''' Create a new issue for the specified repo. '''
    user_obj = get_user(session, user)

    issue = model.Issue(
        id=issue_id or get_next_id(session, repo.id),
        project_id=repo.id,
        title=title,
        content=content,
        user_id=user_obj.id,
        uid=issue_uid or uuid.uuid4().hex,
        private=private,
        date_created=date_created,
    )

    if status is not None:
        issue.status = status

    session.add(issue)
    # Make sure we won't have SQLAlchemy error before we create the issue
    session.flush()

    pagure.lib.git.update_git(
        issue, repo=repo, repofolder=ticketfolder)

    if notify:
        pagure.lib.notify.notify_new_issue(issue, user=user_obj)

    if not private:
        pagure.lib.notify.log(
            issue.project,
            topic='issue.new',
            msg=dict(
                issue=issue.to_json(public=True),
                project=issue.project.to_json(public=True),
                agent=user_obj.username,
            ),
            redis=REDIS,
        )

    return issue


def drop_issue(session, issue, user, ticketfolder):
    ''' Delete a specified issue. '''
    user_obj = get_user(session, user)

    private = issue.private
    session.delete(issue)

    # Make sure we won't have SQLAlchemy error before we create the issue
    session.flush()

    pagure.lib.git.clean_git(
        issue, repo=issue.project, repofolder=ticketfolder)

    if not private:
        pagure.lib.notify.log(
            issue.project,
            topic='issue.drop',
            msg=dict(
                issue=issue.to_json(public=True),
                project=issue.project.to_json(public=True),
                agent=user_obj.username,
            ),
            redis=REDIS,
        )

    return issue


def new_pull_request(session, branch_from,
                     repo_to, branch_to, title, user,
                     requestfolder, initial_comment=None,
                     repo_from=None, remote_git=None,
                     requestuid=None, requestid=None,
                     status='Open', notify=True):
    ''' Create a new pull request on the specified repo. '''
    if not repo_from and not remote_git:
        raise pagure.exceptions.PagureException(
            'Invalid input, you must specify either a local repo or a '
            'remote one')

    user_obj = get_user(session, user)

    request = model.PullRequest(
        id=requestid or get_next_id(session, repo_to.id),
        uid=requestuid or uuid.uuid4().hex,
        project_id=repo_to.id,
        project_id_from=repo_from.id if repo_from else None,
        remote_git=remote_git if remote_git else None,
        branch=branch_to,
        branch_from=branch_from,
        title=title,
        initial_comment=initial_comment or None,
        user_id=user_obj.id,
        status=status,
    )
    session.add(request)
    # Make sure we won't have SQLAlchemy error before we create the request
    session.flush()

    pagure.lib.git.update_git(
        request, repo=request.project, repofolder=requestfolder)

    if notify:
        pagure.lib.notify.notify_new_pull_request(request)

    pagure.lib.notify.log(
        request.project,
        topic='pull-request.new',
        msg=dict(
            pullrequest=request.to_json(public=True),
            agent=user_obj.username,
        ),
        redis=REDIS,
    )

    # Send notification to the CI server
    if REDIS and request.project.ci_hook and PAGURE_CI:
        REDIS.publish('pagure.ci', json.dumps({
            'ci_type': request.project.ci_hook.ci_type,
            'pr': request.to_json(public=True, with_comments=False)
        }))

    return request


def edit_issue(session, issue, ticketfolder, user,
               title=None, content=None, status=None,
               priority=None, milestone=None, private=False):
    ''' Edit the specified issue.
    '''
    user_obj = get_user(session, user)

    if status == 'Fixed' and issue.parents:
        for parent in issue.parents:
            if parent.status == 'Open':
                raise pagure.exceptions.PagureException(
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
        if status.lower() != 'open':
            issue.closed_at = datetime.datetime.utcnow()
        edit.append('status')
    if priority:
        try:
            priority = int(priority)
        except:
            priority = None
        if priority != issue.priority:
            issue.priority = priority
            edit.append('priority')
    if private in [True, False] and private != issue.private:
        issue.private = private
        edit.append('private')
    if milestone != issue.milestone:
        issue.milestone = milestone
        edit.append('milestone')

    pagure.lib.git.update_git(
        issue, repo=issue.project, repofolder=ticketfolder)

    if 'status' in edit:
        add_issue_comment(
            session,
            issue,
            comment='@%s changed the status to ``%s``' % (
                user_obj.username, status),
            user=user,
            ticketfolder=ticketfolder,
            notify=False,
            notification=True,
        )

    if not issue.private and edit:
        pagure.lib.notify.log(
            issue.project,
            topic='issue.edit',
            msg=dict(
                issue=issue.to_json(public=True),
                project=issue.project.to_json(public=True),
                fields=edit,
                agent=user_obj.username,
            ),
            redis=REDIS,
        )

    if REDIS and edit:
        if issue.private:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps({
                'issue': 'private',
                'fields': edit,
            }))
        else:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps({
                'fields': edit,
                'issue': issue.to_json(public=True, with_comments=False),
            }))

    if edit:
        session.add(issue)
        session.flush()
        return 'Successfully edited issue #%s' % issue.id


def update_project_settings(session, repo, settings, user):
    ''' Update the settings of a project. '''
    user_obj = get_user(session, user)

    update = []
    new_settings = repo.settings
    for key in new_settings:
        if key in settings:
            if new_settings[key] != settings[key]:
                update.append(key)
                if key == 'Minimum_score_to_merge_pull-request':
                    try:
                        settings[key] = int(settings[key]) \
                            if settings[key] else -1
                    except ValueError:
                        raise pagure.exceptions.PagureException(
                            "Please enter a numeric value for the 'minimum "
                            "score to merge pull request' field.")
                elif key == 'Web-hooks':
                    settings[key] = settings[key] or None
                new_settings[key] = settings[key]
        else:
            update.append(key)
            val = False
            if key == 'Web-hooks':
                val = None
            new_settings[key] = val

    if not update:
        return 'No settings to change'
    else:
        repo.settings = new_settings
        session.add(repo)
        session.flush()
        pagure.lib.notify.log(
            repo,
            topic='project.edit',
            msg=dict(
                project=repo.to_json(public=True),
                fields=update,
                agent=user_obj.username,
            ),
            redis=REDIS,
        )

        return 'Edited successfully settings of repo: %s' % repo.fullname


def fork_project(session, user, repo, gitfolder,
                 docfolder, ticketfolder, requestfolder):
    ''' Fork a given project into the user's forks. '''
    reponame = os.path.join(gitfolder, repo.path)
    forkreponame = '%s.git' % os.path.join(
        gitfolder, 'forks', user, repo.name)

    if os.path.exists(forkreponame):
        raise pagure.exceptions.RepoExistsException(
            'Repo "forks/%s/%s" already exists' % (user, repo.name))

    user_obj = get_user(session, user)

    project = model.Project(
        name=repo.name,
        description=repo.description,
        user_id=user_obj.id,
        parent_id=repo.id,
        is_fork=True,
        hook_token=pagure.lib.login.id_generator(40)
    )

    # disable issues, PRs in the fork by default
    default_repo_settings = project.settings
    default_repo_settings['issue_tracker'] = False
    default_repo_settings['pull_requests'] = False
    project.settings = default_repo_settings

    session.add(project)
    # Make sure we won't have SQLAlchemy error before we create the repo
    session.flush()

    frepo = pygit2.clone_repository(reponame, forkreponame, bare=True)
    # Clone all the branches as well
    for branch in frepo.listall_branches(pygit2.GIT_BRANCH_REMOTE):
        branch_obj = frepo.lookup_branch(branch, pygit2.GIT_BRANCH_REMOTE)
        name = branch_obj.branch_name.replace(
            branch_obj.remote_name, '')[1:]
        if name in frepo.listall_branches(pygit2.GIT_BRANCH_LOCAL):
            continue
        frepo.create_branch(name, frepo.get(branch_obj.target.hex))

    # Create the git-daemin-export-ok file on the clone
    http_clone_file = os.path.join(forkreponame, 'git-daemon-export-ok')
    if not os.path.exists(http_clone_file):
        with open(http_clone_file, 'w'):
            pass

    docrepo = os.path.join(docfolder, project.path)
    if os.path.exists(docrepo):
        shutil.rmtree(forkreponame)
        raise pagure.exceptions.RepoExistsException(
            'The docs "%s" already exists' % project.path
        )
    pygit2.init_repository(docrepo, bare=True)

    ticketrepo = os.path.join(ticketfolder, project.path)
    if os.path.exists(ticketrepo):
        shutil.rmtree(forkreponame)
        shutil.rmtree(docrepo)
        raise pagure.exceptions.RepoExistsException(
            'The tickets repo "%s" already exists' % project.path
        )
    pygit2.init_repository(
        ticketrepo, bare=True,
        mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP)

    requestrepo = os.path.join(requestfolder, project.path)
    if os.path.exists(requestrepo):
        shutil.rmtree(forkreponame)
        shutil.rmtree(docrepo)
        shutil.rmtree(ticketrepo)
        raise pagure.exceptions.RepoExistsException(
            'The requests repo "%s" already exists' % project.path
        )
    pygit2.init_repository(
        requestrepo, bare=True,
        mode=pygit2.C.GIT_REPOSITORY_INIT_SHARED_GROUP)

    pagure.lib.notify.log(
        project,
        topic='project.forked',
        msg=dict(
            project=project.to_json(public=True),
            agent=user_obj.username,
        ),
    )

    return 'Repo "%s" cloned to "%s/%s"' % (repo.name, user, repo.name)


def search_projects(
        session, username=None,
        fork=None, tags=None, namespace=None, pattern=None,
        start=None, limit=None, count=False, sort=None):
    '''List existing projects
    '''
    projects = session.query(
        sqlalchemy.distinct(model.Project.id)
    )

    if username is not None:
        projects = projects.filter(
            # User created the project
            sqlalchemy.and_(
                model.User.user == username,
                model.User.id == model.Project.user_id,
            )
        )
        sub_q2 = session.query(
            model.Project.id
        ).filter(
            # User got commit right
            sqlalchemy.and_(
                model.User.user == username,
                model.User.id == model.ProjectUser.user_id,
                model.ProjectUser.project_id == model.Project.id
            )
        )
        sub_q3 = session.query(
            model.Project.id
        ).filter(
            # User created a group that has commit right
            sqlalchemy.and_(
                model.User.user == username,
                model.PagureGroup.user_id == model.User.id,
                model.PagureGroup.group_type == 'user',
                model.PagureGroup.id == model.ProjectGroup.group_id,
                model.Project.id == model.ProjectGroup.project_id,
            )
        )
        sub_q4 = session.query(
            model.Project.id
        ).filter(
            # User is part of a group that has commit right
            sqlalchemy.and_(
                model.User.user == username,
                model.PagureUserGroup.user_id == model.User.id,
                model.PagureUserGroup.group_id == model.PagureGroup.id,
                model.PagureGroup.group_type == 'user',
                model.PagureGroup.id == model.ProjectGroup.group_id,
                model.Project.id == model.ProjectGroup.project_id,
            )
        )

        projects = projects.union(sub_q2).union(sub_q3).union(sub_q4)

    if fork is not None:
        if fork is True:
            projects = projects.filter(
                model.Project.is_fork == True
            )
        elif fork is False:
            projects = projects.filter(
                model.Project.is_fork == False
            )

    if tags:
        if not isinstance(tags, (list, tuple)):
            tags = [tags]

        projects = projects.filter(
            model.Project.id == model.TagProject.project_id
        ).filter(
            model.TagProject.tag.in_(tags)
        )

    if pattern:
        pattern = pattern.replace('*', '%')
        if '%' in pattern:
            projects = projects.filter(
                model.Project.name.like(pattern)
            )
        else:
            projects = projects.filter(
                model.Project.name == pattern
            )

    if namespace:
        projects = projects.filter(
            model.Project.namespace == namespace
        )

    query = session.query(
        model.Project
    ).filter(
        model.Project.id.in_(projects.subquery())
    )

    if sort == 'latest':
        query = query.order_by(
            model.Project.date_created.desc()
        )
    elif sort == 'oldest':
        query = query.order_by(
            model.Project.date_created.asc()
        )
    else:
        query = query.order_by(
            asc(func.lower(model.Project.name))
        )

    if start is not None:
        query = query.offset(start)

    if limit is not None:
        query = query.limit(limit)

    if count:
        return query.count()
    else:
        return query.all()


def get_project(session, name, user=None, namespace=None):
    '''Get a project from the database
    '''
    query = session.query(
        model.Project
    ).filter(
        model.Project.name == name
    ).filter(
        model.Project.namespace == namespace
    )

    if user is not None:
        query = query.filter(
            model.User.user == user
        ).filter(
            model.User.id == model.Project.user_id
        ).filter(
            model.Project.is_fork == True
        )
    else:
        query = query.filter(
            model.Project.is_fork == False
        )

    return query.first()


def search_issues(
        session, repo, issueid=None, issueuid=None, status=None,
        closed=False, tags=None, assignee=None, author=None, private=None,
        priority=None, milestones=None,
        count=False, offset=None, limit=None):
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
    :type repo: pagure.lib.model.Project
    :kwarg issueid: the identifier of the issue to look for
    :type issueid: int or None
    :kwarg issueuid: the unique identifier of the issue to look for
    :type issueuid: str or None
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
    :kwarg priority: the priority of the issues to search
    :type priority: int or None
    :kwarg milestones: a milestone the issue(s) returned should be
        associated with.
    :type milestones: str or list(str) or None
    :kwarg count: a boolean to specify if the method should return the list
        of Issues or just do a COUNT query.
    :type count: boolean

    :return: A single Issue object if issueid is specified, a list of Project
        objects otherwise.
    :rtype: Project or [Project]

    '''
    query = session.query(
        sqlalchemy.distinct(model.Issue.uid)
    ).filter(
        model.Issue.project_id == repo.id
    )

    if issueid is not None:
        query = query.filter(
            model.Issue.id == issueid
        )

    if issueuid is not None:
        query = query.filter(
            model.Issue.uid == issueuid
        )

    if status is not None and not closed:
        query = query.filter(
            model.Issue.status == status
        )
    if closed:
        query = query.filter(
            model.Issue.status != 'Open'
        )
    if priority:
        query = query.filter(
            model.Issue.priority == priority
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
            sub_q2 = session.query(
                sqlalchemy.distinct(model.Issue.uid)
            ).filter(
                model.Issue.project_id == repo.id
            ).filter(
                model.Issue.uid == model.TagIssue.issue_uid
            ).filter(
                model.TagIssue.tag.in_(ytags)
            )
        if notags:
            sub_q3 = session.query(
                sqlalchemy.distinct(model.Issue.uid)
            ).filter(
                model.Issue.project_id == repo.id
            ).filter(
                model.Issue.uid == model.TagIssue.issue_uid
            ).filter(
                model.TagIssue.tag.in_(notags)
            )
        # Adjust the main query based on the parameters specified
        if ytags and not notags:
            query = query.filter(model.Issue.uid.in_(sub_q2))
        elif not ytags and notags:
            query = query.filter(~model.Issue.uid.in_(sub_q3))
        elif ytags and notags:
            final_set = set(sub_q2.all()) - set(sub_q3.all())
            if final_set:
                query = query.filter(model.Issue.uid.in_(list(final_set)))

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

    if milestones is not None and milestones != []:
        if isinstance(milestones, basestring):
            milestones = [milestones]

        query = query.filter(
            model.Issue.milestone.in_(milestones)
        )

    query = session.query(
        model.Issue
    ).filter(
        model.Issue.uid.in_(query.subquery())
    ).filter(
        model.Issue.project_id == repo.id
    )

    query = query.order_by(
        model.Issue.date_created.desc()
    )

    if issueid is not None or issueuid is not None:
        output = query.first()
    elif count:
        output = query.count()
    else:
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
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
        status=None, author=None, assignee=None, count=False,
        offset=None, limit=None):
    ''' Retrieve the specified issue
    '''

    query = session.query(
        model.PullRequest
    ).order_by(
        model.PullRequest.id.desc()
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
        if isinstance(status, bool):
            if status:
                query = query.filter(
                    model.PullRequest.status == 'Open'
                )
            else:
                query = query.filter(
                    model.PullRequest.status != 'Open'
                )
        else:
            query = query.filter(
                model.PullRequest.status == status
            )

    if assignee is not None:
        if str(assignee).lower() not in ['false', '0', 'true', '1']:
            user2 = aliased(model.User)
            if assignee.startswith('!'):
                sub = session.query(
                    model.PullRequest.uid
                ).filter(
                    model.PullRequest.assignee_id == user2.id
                ).filter(
                    user2.user == assignee[1:]
                )

                query = query.filter(
                    ~model.PullRequest.uid.in_(sub)
                )
            else:
                query = query.filter(
                    model.PullRequest.assignee_id == user2.id
                ).filter(
                    user2.user == assignee
                )
        elif str(assignee).lower() in ['true', '1']:
            query = query.filter(
                model.PullRequest.assignee_id != None
            )
        else:
            query = query.filter(
                model.PullRequest.assignee_id == None
            )

    if author is not None:
        query = query.filter(
            model.PullRequest.user_id == model.User.id
        ).filter(
            model.User.user == author
        )

    if requestid:
        output = query.first()
    elif count:
        output = query.count()
    else:
        if offset:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        output = query.all()

    return output


def close_pull_request(session, request, user, requestfolder, merged=True):
    ''' Close the provided pull-request.
    '''
    user_obj = get_user(session, user)

    if merged is True:
        request.status = 'Merged'
    else:
        request.status = 'Closed'
    request.closed_by_id = user_obj.id
    request.closed_at = datetime.datetime.utcnow()
    session.add(request)
    session.flush()

    if merged is True:
        pagure.lib.notify.notify_merge_pull_request(request, user_obj)
    else:
        pagure.lib.notify.notify_cancelled_pull_request(request, user_obj)

    pagure.lib.git.update_git(
        request, repo=request.project, repofolder=requestfolder)

    pagure.lib.add_pull_request_comment(
        session, request,
        commit=None, tree_id=None, filename=None, row=None,
        comment='Pull-Request has been %s by %s' % (
            request.status.lower(), user),
        user=user,
        requestfolder=requestfolder,
        notify=False, notification=True
    )

    pagure.lib.notify.log(
        request.project,
        topic='pull-request.closed',
        msg=dict(
            pullrequest=request.to_json(public=True),
            merged=merged,
            agent=user_obj.username,
        ),
        redis=REDIS,
    )


def reset_status_pull_request(session, project):
    ''' Reset the status of all opened Pull-Requests of a project.
    '''
    requests = search_pull_requests(
        session, project_id=project.id, status='Open')

    for request in requests:
        request.merge_status = None
        session.add(request)

    session.commit()


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
    ''' Return a specific comment of a specified request.
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
        unique accross all projects on this pagure instance and should be
        unique accross multiple pagure instances as well
    :type issue_uid: str or None

    :return: A single Issue object.
    :rtype: pagure.lib.model.Issue

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
        unique accross all projects on this pagure instance and should be
        unique accross multiple pagure instances as well
    :type request_uid: str or None

    :return: A single Issue object.
    :rtype: pagure.lib.model.PullRequest

    '''
    query = session.query(
        model.PullRequest
    ).filter(
        model.PullRequest.uid == request_uid
    )
    return query.first()


def get_pull_request_flag_by_uid(session, flag_uid):
    ''' Return the flag corresponding to the specified unique identifier.

    :arg session: the session to use to connect to the database.
    :arg flag_uid: the unique identifier of a request. This identifier is
        unique accross all flags on this pagure instance and should be
        unique accross multiple pagure instances as well
    :type request_uid: str or None

    :return: A single Issue object.
    :rtype: pagure.lib.model.PullRequestFlag

    '''
    query = session.query(
        model.PullRequestFlag
    ).filter(
        model.PullRequestFlag.uid == flag_uid.strip() if flag_uid else None
    )
    return query.first()


def set_up_user(session, username, fullname, default_email,
                emails=None, ssh_key=None, keydir=None):
    ''' Set up a new user into the database or update its information. '''
    user = search_user(session, username=username)
    if not user:
        user = model.User(
            user=username,
            fullname=fullname,
            default_email=default_email
        )
        session.add(user)
        session.flush()

    if user.fullname != fullname:
        user.fullname = fullname
        session.add(user)
        session.flush()

    if emails:
        emails = set(emails)
    else:
        emails = set()
    emails.add(default_email)
    for email in emails:
        add_email_to_user(session, user, email)

    if ssh_key and not user.public_ssh_key:
        update_user_ssh(session, user, ssh_key, keydir)

    return user


def add_email_to_user(session, user, user_email):
    ''' Add the provided email to the specified user. '''
    emails = [email.email for email in user.emails]
    if user_email not in emails:
        useremail = model.UserEmail(
            user_id=user.id,
            email=user_email)
        session.add(useremail)
        session.flush()


def update_user_ssh(session, user, ssh_key, keydir):
    ''' Set up a new user into the database or update its information. '''
    if isinstance(user, basestring):
        user = get_user(session, user)

    user.public_ssh_key = ssh_key
    if keydir and user.public_ssh_key:
        create_user_ssh_keys_on_disk(user, keydir)
        pagure.lib.git.generate_gitolite_acls()
    session.add(user)
    session.flush()


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
        hashhex = hashlib.sha256(openid).hexdigest()
        return "https://seccdn.libravatar.org/avatar/%s?%s" % (
            hashhex, query)


def update_tags(session, obj, tags, username, ticketfolder):
    """ Update the tags of a specified object (adding or removing them).
    This object can be either an issue or a project.

    """
    if isinstance(tags, basestring):
        tags = [tags]

    toadd = set(tags) - set(obj.tags_text)
    torm = set(obj.tags_text) - set(tags)
    messages = []
    if toadd:
        messages.append(
            add_tag_obj(
                session,
                obj=obj,
                tags=toadd,
                user=username,
                ticketfolder=ticketfolder,
            )
        )

    if torm:
        messages.append(
            remove_tags_obj(
                session,
                obj=obj,
                tags=torm,
                user=username,
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


def add_user_pending_email(session, userobj, email):
    ''' Add the provided user to the specified user.
    '''
    other_user = search_user(session, email=email)
    if other_user and other_user != userobj:
        raise pagure.exceptions.PagureException(
            'Someone else has already registered this email'
        )

    pending_email = search_pending_email(session, email=email)
    if pending_email:
        raise pagure.exceptions.PagureException(
            'This email is already pending confirmation'
        )

    tmpemail = pagure.lib.model.UserEmailPending(
        user_id=userobj.id,
        token=pagure.lib.login.id_generator(40),
        email=email
    )
    session.add(tmpemail)
    session.flush()

    pagure.lib.notify.notify_new_email(tmpemail, user=userobj)


def resend_pending_email(session, userobj, email):
    ''' Resend to the user the confirmation email for the provided email
    address.
    '''
    other_user = search_user(session, email=email)
    if other_user and other_user != userobj:
        raise pagure.exceptions.PagureException(
            'Someone else has already registered this email address'
        )

    pending_email = search_pending_email(session, email=email)
    if not pending_email:
        raise pagure.exceptions.PagureException(
            'This email address has already been confirmed'
        )

    pending_email.token = pagure.lib.login.id_generator(40)
    session.add(pending_email)
    session.flush()

    pagure.lib.notify.notify_new_email(pending_email, user=userobj)


def search_pending_email(session, email=None, token=None):
    ''' Searches the database for the pending email matching the given
    criterias.

    :arg session: the session to use to connect to the database.
    :kwarg email: the email to look for
    :type email: string or None
    :kwarg token: the token of the pending email to look for
    :type token: string or None
    :return: A single UserEmailPending object
    :rtype: UserEmailPending

    '''
    query = session.query(
        model.UserEmailPending
    )

    if email is not None:
        query = query.filter(
            model.UserEmailPending.email == email
        )

    if token is not None:
        query = query.filter(
            model.UserEmailPending.token == token
        )

    output = query.first()

    return output


def generate_hook_token(session):
    ''' For each project in the database, re-generate a unique hook_token.

    '''

    for project in search_projects(session):
        project.hook_token = pagure.lib.login.id_generator(40)
        session.add(project)
    session.commit()


def get_group_types(session, group_type=None):
    ''' Return the list of type a group can have.

    '''
    query = session.query(
        model.PagureGroupType
    ).order_by(
        model.PagureGroupType.group_type
    )

    if group_type:
        query = query.filter(
            model.PagureGroupType.group_type == group_type
        )

    return query.all()


def search_groups(session, pattern=None, group_name=None, group_type=None):
    ''' Return the groups based on the criteria specified.

    '''
    query = session.query(
        model.PagureGroup
    ).order_by(
        model.PagureGroup.group_type
    )

    if pattern:
        pattern = pattern.replace('*', '%')
        query = query.filter(
            model.PagureGroup.group_name.like(pattern)
        )

    if group_name:
        query = query.filter(
            model.PagureGroup.group_name == group_name
        )

    if group_type:
        query = query.filter(
            model.PagureGroup.group_type == group_type
        )

    if group_name:
        return query.first()
    else:
        return query.all()


def add_user_to_group(session, username, group, user, is_admin):
    ''' Add the specified user to the given group.
    '''
    new_user = search_user(session, username=username)
    if not new_user:
        raise pagure.exceptions.PagureException(
            'No user `%s` found' % username)

    action_user = user
    user = search_user(session, username=user)
    if not user:
        raise pagure.exceptions.PagureException(
            'No user `%s` found' % action_user)

    if group.group_name not in user.groups and not is_admin\
            and user.username != group.creator.username:
        raise pagure.exceptions.PagureException(
            'You are not allowed to add user to this group')

    for guser in group.users:
        if guser.username == new_user.username:
            return 'User `%s` already in the group, nothing to change.' % (
                new_user.username)

    grp = model.PagureUserGroup(
        group_id=group.id,
        user_id=new_user.id
    )
    session.add(grp)
    session.flush()
    return 'User `%s` added to the group `%s`.' % (
        new_user.username, group.group_name)


def edit_group_info(
        session, group, display_name, description, user, is_admin):
    ''' Edit the information regarding a given group.
    '''
    action_user = user
    user = search_user(session, username=user)
    if not user:
        raise pagure.exceptions.PagureException(
            'No user `%s` found' % action_user)

    if group.group_name not in user.groups \
            and not is_admin \
            and user.username != group.creator.username:
        raise pagure.exceptions.PagureException(
            'You are not allowed to edit this group')

    edits = []
    if display_name and display_name != group.display_name:
        group.display_name = display_name
        edits.append('display_name')
    if description and description != group.description:
        group.description = description
        edits.append('description')

    session.add(group)
    session.flush()

    msg = 'Nothing changed'
    if edits:
        pagure.lib.notify.log(
            None,
            topic='group.edit',
            msg=dict(
                group=group.to_json(public=True),
                fields=edits,
                agent=user.username,
            ),
            redis=REDIS,
        )
        msg = 'Group "%s" (%s) edited' % (
            group.display_name, group.group_name)

    return msg


def delete_user_of_group(session, username, groupname, user, is_admin,
                         force=False):
    ''' Removes the specified user from the given group.
    '''
    group_obj = search_groups(session, group_name=groupname)

    if not group_obj:
        raise pagure.exceptions.PagureException(
            'No group `%s` found' % groupname)

    drop_user = search_user(session, username=username)
    if not drop_user:
        raise pagure.exceptions.PagureException(
            'No user `%s` found' % username)

    action_user = user
    user = search_user(session, username=user)
    if not user:
        raise pagure.exceptions.PagureException(
            'Could not find user %s' % action_user)

    if group_obj.group_name not in user.groups and not is_admin:
        raise pagure.exceptions.PagureException(
            'You are not allowed to remove user from this group')

    if drop_user.username == group_obj.creator.username and not force:
        raise pagure.exceptions.PagureException(
            'The creator of a group cannot be removed')

    user_grp = get_user_group(session, drop_user.id, group_obj.id)
    if not user_grp:
        raise pagure.exceptions.PagureException(
            'User `%s` could not be found in the group `%s`' % (
                username, groupname))

    session.delete(user_grp)
    session.flush()


def add_group(
        session, group_name, display_name, description,
        group_type, user, is_admin, blacklist):
    ''' Creates a new group with the given information.
    '''
    if ' ' in group_name:
        raise pagure.exceptions.PagureException(
            'Spaces are not allowed in group names: %s' % group_name)

    if group_name in blacklist:
        raise pagure.exceptions.PagureException(
            'This group name has been blacklisted, '
            'please choose another one')

    group_types = ['user']
    if is_admin:
        group_types = [
            grp.group_type
            for grp in get_group_types(session)
        ]

    if not is_admin:
        group_type = 'user'

    if group_type not in group_types:
        raise pagure.exceptions.PagureException(
            'Invalide type for this group')

    username = user
    user = search_user(session, username=user)
    if not user:
        raise pagure.exceptions.PagureException(
            'Could not find user %s' % username)

    group = search_groups(session, group_name=group_name)
    if group:
        raise pagure.exceptions.PagureException(
            'There is already a group named %s' % group_name)

    grp = pagure.lib.model.PagureGroup(
        group_name=group_name,
        display_name=display_name,
        description=description,
        group_type=group_type,
        user_id=user.id,
    )
    session.add(grp)
    session.flush()

    return add_user_to_group(
        session, user.username, grp, user.username, is_admin)


def get_user_group(session, userid, groupid):
    ''' Return a specific user_group for the specified group and user
    identifiers.

    :arg session: the session with which to connect to the database.

    '''
    query = session.query(
        model.PagureUserGroup
    ).filter(
        model.PagureUserGroup.user_id == userid
    ).filter(
        model.PagureUserGroup.group_id == groupid
    )

    return query.first()


def is_group_member(session, user, groupname):
    """ Return whether the user is a member of the specified group. """
    if not user:
        return False

    user = search_user(session, username=user)
    if not user:
        return False

    return groupname in user.groups


def get_api_token(session, token_str):
    """ Return the Token object corresponding to the provided token string
    if there is any, returns None otherwise.
    """
    query = session.query(
        model.Token
    ).filter(
        model.Token.id == token_str
    )

    return query.first()


def get_acls(session):
    """ Returns all the possible ACLs a token can have according to the
    database.
    """
    query = session.query(
        model.ACL
    ).order_by(
        model.ACL.name
    )

    return query.all()


def add_token_to_user(session, project, acls, username):
    """ Create a new token for the specified user on the specified project
    with the given ACLs.
    """
    acls_obj = session.query(
        model.ACL
    ).filter(
        model.ACL.name.in_(acls)
    ).all()

    user = search_user(session, username=username)

    token = pagure.lib.model.Token(
        id=pagure.lib.login.id_generator(64),
        user_id=user.id,
        project_id=project.id,
        expiration=datetime.datetime.utcnow() + datetime.timedelta(days=60)
    )
    session.add(token)
    session.flush()

    for acl in acls_obj:
        item = pagure.lib.model.TokenAcl(
            token_id=token.id,
            acl_id=acl.id,
        )
        session.add(item)

    session.commit()

    return 'Token created'


def text2markdown(text, extended=True):
    """ Simple text to html converter using the markdown library.
    """
    md_processor = markdown.Markdown(safe_mode="escape")
    if extended:
        # Install our markdown modifications
        md_processor = markdown.Markdown(extensions=['pagure.pfmarkdown'])

    if text:
        # Hack to allow blockquotes to be marked by ~~~
        ntext = []
        indent = False
        for line in text.split('\n'):
            if line.startswith('~~~'):
                indent = not indent
                continue
            if indent:
                line = '    %s' % line
            ntext.append(line)
        return clean_input(md_processor.convert('\n'.join(ntext)))

    return ''


def filter_img_src(name, value):
    ''' Filter in img html tags images coming from a different domain. '''
    if name in ('alt', 'height', 'width', 'class'):
        return True
    if name == 'src':
        parsed = urlparse.urlparse(value)
        return (not parsed.netloc) or parsed.netloc == urlparse.urlparse(
            pagure.APP.config['APP_URL']).netloc
    return False


def clean_input(text, ignore=None):
    """ For a given html text, escape everything we do not want to support
    to avoid potential security breach.
    """
    if ignore and not isinstance(ignore, (tuple, set, list)):
        ignore = [ignore]

    attrs = bleach.ALLOWED_ATTRIBUTES
    if not ignore or not 'img' in ignore:
        attrs['img'] = filter_img_src

    tags = bleach.ALLOWED_TAGS + [
        'p', 'br', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'table', 'td', 'tr', 'th',
        'col', 'tbody', 'pre', 'img', 'hr', 'dl', 'dt', 'dd', 'span',
        'kbd', 'var', 'del',
    ]
    if ignore:
        for tag in ignore:
            if tag in tags:
                tags.remove(tag)

    return bleach.clean(text, tags=tags, attributes=attrs)


def could_be_text(text):
    """ Returns wether we think this chain of character could be text or not
    """
    try:
        text.decode('utf-8')
        return True
    except:
        return False


def get_pull_request_of_user(session, username):
    '''List the opened pull-requests of an user.
    These pull-requests have either been opened by that user or against
    projects that user has commit on.
    '''
    projects = session.query(
        sqlalchemy.distinct(model.Project.id)
    )

    projects = projects.filter(
        # User created the project
        sqlalchemy.and_(
            model.User.user == username,
            model.User.id == model.Project.user_id,
        )
    )
    sub_q2 = session.query(
        model.Project.id
    ).filter(
        # User got commit right
        sqlalchemy.and_(
            model.User.user == username,
            model.User.id == model.ProjectUser.user_id,
            model.ProjectUser.project_id == model.Project.id
        )
    )
    sub_q3 = session.query(
        model.Project.id
    ).filter(
        # User created a group that has commit right
        sqlalchemy.and_(
            model.User.user == username,
            model.PagureGroup.user_id == model.User.id,
            model.PagureGroup.group_type == 'user',
            model.PagureGroup.id == model.ProjectGroup.group_id,
            model.Project.id == model.ProjectGroup.project_id,
        )
    )
    sub_q4 = session.query(
        model.Project.id
    ).filter(
        # User is part of a group that has commit right
        sqlalchemy.and_(
            model.User.user == username,
            model.PagureUserGroup.user_id == model.User.id,
            model.PagureUserGroup.group_id == model.PagureGroup.id,
            model.PagureGroup.group_type == 'user',
            model.PagureGroup.id == model.ProjectGroup.group_id,
            model.Project.id == model.ProjectGroup.project_id,
        )
    )

    projects = projects.union(sub_q2).union(sub_q3).union(sub_q4)

    query = session.query(
        model.PullRequest
    ).filter(
        model.PullRequest.project_id.in_(projects.subquery())
    ).order_by(
        model.PullRequest.date_created.desc()
    )

    return query.all()


def update_watch_status(session, project, user, watch):
    ''' Update the user status for watching a project.
    '''
    user_obj = get_user(session, user)

    if not user_obj:
        raise pagure.exceptions.PagureException(
            'No user with username: %s' % user)

    watcher = session.query(
        model.Watcher
    ).filter(
        sqlalchemy.and_(
            model.Watcher.project_id == project.id,
            model.Watcher.user_id == user_obj.id,
        )
    ).first()

    if not watcher:
        watcher = model.Watcher(
            project_id=project.id,
            user_id=user_obj.id,
            watch=watch
        )
    else:
        watcher.watch = watch

    session.add(watcher)
    session.flush()

    msg_success = 'You are now watching this repo.'
    if not int(watch):
        msg_success = 'You are no longer watching this repo.'
    return msg_success


def is_watching(session, user, reponame, repouser=None, namespace=None):
    ''' Check user watching the project. '''

    if user is None:
        return False

    user_obj = search_user(session, username=user.username)
    if not user_obj:
        return False

    query = session.query(
        model.Watcher
    ).filter(
        model.Watcher.user_id == user_obj.id
    ).filter(
        model.Watcher.project_id == model.Project.id
    ).filter(
        model.Project.name == reponame
    )

    if repouser is not None:
        query = query.filter(
            model.User.user == repouser
        ).filter(
            model.User.id == model.Project.user_id
        ).filter(
            model.Project.is_fork == True
        )
    else:
        query = query.filter(
            model.Project.is_fork == False
        )

    if namespace is not None:
        query = query.filter(
            model.Project.namespace == namespace
        )

    watcher = query.first()

    if watcher:
        return watcher.watch

    project = pagure.lib.get_project(
        session, reponame, user=repouser, namespace=namespace)
    if not project:
        return False

    if user.username == project.user.username:
        return True

    for group in project.groups:
        for guser in group.users:
            if user.username == guser.username:
                return True

    return False


def user_watch_list(session, user):
    ''' Returns list of all the projects which the user is watching '''

    user_obj = search_user(session, username=user)
    if not user_obj:
        return []

    unwatched = session.query(
        model.Watcher
    ).filter(
        model.Watcher.user_id == user_obj.id
    ).filter(
        model.Watcher.watch == False
    )

    unwatched_list = []
    if unwatched:
        unwatched_list = [unwatch.project for unwatch in unwatched.all()]

    watched = session.query(
        model.Watcher
    ).filter(
        model.Watcher.user_id == user_obj.id
    ).filter(
        model.Watcher.watch == True
    )

    watched_list = []
    if watched:
        watched_list = [watch.project for watch in watched.all()]

    user_projects = search_projects(session, username=user_obj.user)
    watch = set(watched_list + user_projects)

    for project in user_projects:
        if project in unwatched_list:
            watch.remove(project)

    return sorted(list(watch), key=lambda proj: proj.name)


def save_report(session, repo, name, url, username):
    """ Save the report of issues based on the given URL of the project.
    """
    url_obj = urlparse.urlparse(url)
    url = url_obj.geturl().replace(url_obj.query, '')
    query = dict(urlparse.parse_qsl(url_obj.query))
    reports = repo.reports
    reports[name] = query
    repo.reports = reports
    session.add(repo)
