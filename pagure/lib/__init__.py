# -*- coding: utf-8 -*-

"""
 (c) 2014-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>
   Farhaan Bukhsh <farhaan.bukhsh@gmail.com>

"""

# pylint: disable=too-many-branches
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
# pylint: disable=too-many-statements
# pylint: disable=too-many-lines


try:
    import simplejson as json
except ImportError:  # pragma: no cover
    import json

import datetime
import fnmatch
import hashlib
import logging
import os
import tempfile
import subprocess
import urlparse
import uuid
import markdown
import werkzeug
from math import ceil
import copy

import bleach
import redis
import six
import sqlalchemy
import sqlalchemy.schema
from sqlalchemy import func
from sqlalchemy import asc, desc
from sqlalchemy.orm import aliased
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from flask import url_for

import pagure
import pagure.exceptions
import pagure.lib.git
import pagure.lib.login
import pagure.lib.notify
import pagure.lib.plugins
import pagure.pfmarkdown
from pagure.lib import model
from pagure.lib import tasks


REDIS = None
PAGURE_CI = None
_log = logging.getLogger(__name__)


class Unspecified(object):
    """ Custom None object used to indicate that the caller has not made
    a choice for a particular argument.
    """
    pass


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


SESSIONMAKER = None


def create_session(db_url=None, debug=False, pool_recycle=3600):
    ''' Create the Session object to use to query the database.

    :arg db_url: URL used to connect to the database. The URL contains
    information with regards to the database engine, the host to connect
    to, the user and password and the database name.
      ie: <engine>://<user>:<password>@<host>/<dbname>
    :kwarg debug: a boolean specifying whether we should have the verbose
        output of sqlalchemy or not.
    :return a Session that can be used to query the database.

    '''
    global SESSIONMAKER

    if SESSIONMAKER is None:
        if db_url is None:
            raise ValueError("First call to create_session needs db_url")
        if db_url.startswith('postgres'):  # pragma: no cover
            engine = sqlalchemy.create_engine(
                db_url, echo=debug, pool_recycle=pool_recycle,
                client_encoding='utf8')
        else:  # pragma: no cover
            engine = sqlalchemy.create_engine(
                db_url, echo=debug, pool_recycle=pool_recycle)
        SESSIONMAKER = sessionmaker(bind=engine)

    scopedsession = scoped_session(SESSIONMAKER)
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


def is_valid_ssh_key(key):
    """ Validates the ssh key using ssh-keygen. """
    key = key.strip()
    if not key:
        return None
    with tempfile.TemporaryFile() as f:
        f.write(key.encode('utf-8'))
        f.seek(0)
        proc = subprocess.Popen(['/usr/bin/ssh-keygen', '-l', '-f',
                                 '/dev/stdin'],
                                stdin=f,
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    if proc.returncode != 0:
        return False
    return stdout


def are_valid_ssh_keys(keys):
    """ Checks if all the ssh keys are valid or not. """
    return all([is_valid_ssh_key(key) is not False
                for key in keys.split('\n')])


def create_deploykeys_ssh_keys_on_disk(project, gitolite_keydir):
    ''' Create the ssh keys for the projects' deploy keys on the key dir.

    This method does NOT support multiple ssh keys per deploy key.
    '''
    if not gitolite_keydir:
        # Nothing to do here, move right along
        return

    # First remove deploykeys that no longer exist
    keyfiles = ['deploykey_%s_%s.pub' %
                (werkzeug.secure_filename(project.fullname),
                 key.id)
                for key in project.deploykeys]

    project_key_dir = os.path.join(gitolite_keydir, 'deploykeys',
                                   project.fullname)
    if not os.path.exists(project_key_dir):
        os.makedirs(project_key_dir)

    for keyfile in os.listdir(project_key_dir):
        if keyfile not in keyfiles:
            # This key is no longer in the project. Remove it.
            os.remove(os.path.join(project_key_dir, keyfile))

    for deploykey in project.deploykeys:
        # See the comment in lib/git.py:write_gitolite_acls about why this
        # name for a file is sane and does not inject a new security risk.
        keyfile = 'deploykey_%s_%s.pub' % (
            werkzeug.secure_filename(project.fullname),
            deploykey.id)
        if not os.path.exists(os.path.join(project_key_dir, keyfile)):
            # We only take the very first key - deploykeys must be single keys
            key = deploykey.public_ssh_key.split('\n')[0]
            if not key:
                continue
            if not is_valid_ssh_key(key):
                continue
            with open(os.path.join(project_key_dir, keyfile), 'w') as f:
                f.write(deploykey.public_ssh_key)


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

        if not user.public_ssh_key:
            return

        # Now let's create new keyfiles for the user
        keys = user.public_ssh_key.split('\n')
        for i in range(len(keys)):
            if not keys[i]:
                continue
            if not is_valid_ssh_key(keys[i]):
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
    issue.last_updated = datetime.datetime.utcnow()
    session.add(issue)
    session.add(issue_comment)
    # Make sure we won't have SQLAlchemy error before we continue
    session.commit()

    pagure.lib.git.update_git(
        issue, repo=issue.project, repofolder=ticketfolder)

    if not notification:
        log_action(session, 'commented', issue, user_obj)

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

    # TODO: we should notify the SSE server even on update of the ticket
    # via git push to the ticket repo (the only case where notify=False
    # basically), but this causes problem with some of our markdown extension
    # so until we figure this out, we won't do live-refresh
    if REDIS and notify:
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
                'avatar_url': avatar_url_from_email(
                    issue_comment.user.default_email, size=16),
                'comment_date': issue_comment.date_created.strftime(
                    '%Y-%m-%d %H:%M:%S'),
                'notification': notification,
            }))

    return 'Comment added'


def add_tag_obj(session, obj, tags, user, gitfolder):
    ''' Add a tag to an object (either an issue or a project). '''
    user_obj = get_user(session, user)

    if isinstance(tags, basestring):
        tags = [tags]

    added_tags = []
    added_tags_color = []
    for objtag in tags:
        objtag = objtag.strip()
        known = False
        for tagobj in obj.tags:
            if tagobj.tag == objtag:
                known = True

        if known:
            continue

        if obj.isa == 'project':
            tagobj = get_tag(session, objtag)
            if not tagobj:
                tagobj = model.Tag(tag=objtag)

                session.add(tagobj)
                session.flush()

            dbobjtag = model.TagProject(
                project_id=obj.id,
                tag=tagobj.tag,
            )

        else:
            tagobj = get_colored_tag(session, objtag, obj.project.id)
            if not tagobj:
                tagobj = model.TagColored(
                    tag=objtag,
                    project_id=obj.project.id
                )
                session.add(tagobj)
                session.flush()

            if obj.isa == 'issue':
                dbobjtag = model.TagIssueColored(
                    issue_uid=obj.uid,
                    tag_id=tagobj.id
                )
            else:
                dbobjtag = model.TagPullRequest(
                    request_uid=obj.uid,
                    tag_id=tagobj.id
                )

            added_tags_color.append(tagobj.tag_color)

        session.add(dbobjtag)
        # Make sure we won't have SQLAlchemy error before we continue
        session.flush()
        added_tags.append(tagobj.tag)

    if isinstance(obj, model.Issue):
        pagure.lib.git.update_git(
            obj, repo=obj.project, repofolder=gitfolder)

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
        if REDIS and not obj.project.private:
            REDIS.publish('pagure.%s' % obj.uid, json.dumps(
                {
                    'added_tags': added_tags,
                    'added_tags_color': added_tags_color,
                }
            ))
    elif isinstance(obj, model.PullRequest):
        pagure.lib.git.update_git(
            obj, repo=obj.project, repofolder=gitfolder)

        if not obj.private:
            pagure.lib.notify.log(
                obj.project,
                topic='pull-request.tag.added',
                msg=dict(
                    pull_request=obj.to_json(public=True),
                    project=obj.project.to_json(public=True),
                    tags=added_tags,
                    agent=user_obj.username,
                ),
                redis=REDIS,
            )

        # Send notification for the event-source server
        if REDIS and not obj.project.private:
            REDIS.publish('pagure.%s' % obj.uid, json.dumps(
                {
                    'added_tags': added_tags,
                    'added_tags_color': added_tags_color,
                }
            ))

    if added_tags:
        return '%s tagged with: %s' % (
            obj.isa.capitalize(), ', '.join(added_tags))
    else:
        return 'Nothing to add'


def add_issue_assignee(session, issue, assignee, user, ticketfolder,
                       notify=True):
    ''' Add an assignee to an issue, in other words, assigned an issue. '''
    user_obj = get_user(session, user)

    old_assignee = issue.assignee

    if not assignee and issue.assignee is not None:
        issue.assignee_id = None
        issue.last_updated = datetime.datetime.utcnow()
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
        if REDIS and not issue.project.private:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps(
                {'unassigned': '-'}))

        return 'Assignee reset'
    elif not assignee and issue.assignee is None:
        return

    old_assignee = issue.assignee
    # Validate the assignee
    assignee_obj = get_user(session, assignee)

    if issue.assignee_id != assignee_obj.id:
        issue.assignee_id = assignee_obj.id
        session.add(issue)
        session.commit()
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
        issue.last_updated = datetime.datetime.utcnow()

        # Send notification for the event-source server
        if REDIS and not issue.project.private:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps(
                {'assigned': assignee_obj.to_json(public=True)}))

        output = 'Issue assigned to %s' % assignee
        if old_assignee:
            output += ' (was: %s)' % old_assignee.username
        return output


def add_pull_request_assignee(
        session, request, assignee, user, requestfolder):
    ''' Add an assignee to a request, in other words, assigned an issue. '''
    get_user(session, assignee)
    user_obj = get_user(session, user)

    if assignee is None and request.assignee is not None:
        request.assignee_id = None
        request.last_updated = datetime.datetime.utcnow()
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
        request.last_updated = datetime.datetime.utcnow()
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
            parent_issue_id=issue.uid,
            child_issue_id=issue_blocked.uid
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
        if REDIS and not issue.project.private:
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

        return 'Issue marked as depending on: #%s' % issue_blocked.id


def remove_issue_dependency(
        session, issue, issue_blocked, user, ticketfolder):
    ''' Remove a dependency between two issues. '''
    user_obj = get_user(session, user)

    if issue.uid == issue_blocked.uid:
        raise pagure.exceptions.PagureException(
            'An issue cannot depend on itself'
        )

    if issue_blocked in issue.parents:
        parent_del = []
        for parent in issue.parents:
            if parent.uid == issue_blocked.uid:
                parent_del.append(parent.id)
                issue.parents.remove(parent)

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

        if not issue.private:
            pagure.lib.notify.log(
                issue.project,
                topic='issue.dependency.removed',
                msg=dict(
                    issue=issue.to_json(public=True),
                    project=issue.project.to_json(public=True),
                    removed_dependency=parent_del,
                    agent=user_obj.username,
                ),
                redis=REDIS,
            )

        # Send notification for the event-source server
        if REDIS and not issue.project.private:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps({
                'removed_dependency': parent_del,
                'issue_uid': issue.uid,
                'type': 'children',
            }))
            REDIS.publish('pagure.%s' % issue_blocked.uid, json.dumps({
                'removed_dependency': issue.id,
                'issue_uid': issue_blocked.uid,
                'type': 'parent',
            }))

        return 'Issue **un**marked as depending on: #%s' % ' #'.join(
            [str(id) for id in parent_del])


def remove_tags(session, project, tags, gitfolder, user):
    ''' Removes the specified tag of a project. '''
    user_obj = get_user(session, user)

    if not isinstance(tags, list):
        tags = [tags]

    issues = search_issues(session, project, closed=False, tags=tags)
    issues.extend(search_issues(session, project, closed=True, tags=tags))

    msgs = []
    removed_tags = []
    tag_found = False
    for tag in tags:
        tagobj = get_colored_tag(session, tag, project.id)
        if tagobj:
            tag_found = True
            removed_tags.append(tag)
            msgs.append('Issue **un**tagged with: %s' % tag)
            session.delete(tagobj)

    if not tag_found:
        raise pagure.exceptions.PagureException(
            'Tags not found: %s' % ', '.join(tags))

    for issue in issues:
        for issue_tag in issue.tags:
            if issue_tag.tag in tags:
                tag = issue_tag.tag
                session.delete(issue_tag)
        pagure.lib.git.update_git(
            issue, repo=issue.project, repofolder=gitfolder)

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


def remove_tags_obj(session, obj, tags, gitfolder, user):
    ''' Removes the specified tag(s) of a given object. '''
    user_obj = get_user(session, user)

    if isinstance(tags, basestring):
        tags = [tags]

    removed_tags = []
    if obj.isa == 'project':
        for objtag in obj.tags:
            if objtag.tag in tags:
                tag = objtag.tag
                removed_tags.append(tag)
                session.delete(objtag)
    elif obj.isa == 'issue':
        for objtag in obj.tags_issues_colored:
            if objtag.tag.tag in tags:
                tag = objtag.tag.tag
                removed_tags.append(tag)
                session.delete(objtag)
    elif obj.isa == 'pull-request':
        for objtag in obj.tags_pr_colored:
            if objtag.tag.tag in tags:
                tag = objtag.tag.tag
                removed_tags.append(tag)
                session.delete(objtag)

    if isinstance(obj, model.Issue):
        pagure.lib.git.update_git(
            obj, repo=obj.project, repofolder=gitfolder)

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
        if REDIS and not obj.project.private:
            REDIS.publish('pagure.%s' % obj.uid, json.dumps(
                {'removed_tags': removed_tags}))
    elif isinstance(obj, model.PullRequest):
        pagure.lib.git.update_git(
            obj, repo=obj.project, repofolder=gitfolder)

        pagure.lib.notify.log(
            obj.project,
            topic='pull-request.tag.removed',
            msg=dict(
                pull_request=obj.to_json(public=True),
                project=obj.project.to_json(public=True),
                tags=removed_tags,
                agent=user_obj.username,
            ),
            redis=REDIS,
        )

        # Send notification for the event-source server
        if REDIS and not obj.project.private:
            REDIS.publish('pagure.%s' % obj.uid, json.dumps(
                {'removed_tags': removed_tags}))

    return '%s **un**tagged with: %s' % (
        obj.isa.capitalize(), ', '.join(removed_tags))


def edit_issue_tags(
        session, project, old_tag, new_tag, new_tag_description,
        new_tag_color, ticketfolder, user):
    ''' Removes the specified tag of a project. '''
    user_obj = get_user(session, user)
    old_tag_name = old_tag

    if not isinstance(old_tag, model.TagColored):
        old_tag = get_colored_tag(session, old_tag_name, project.id)

    if not old_tag:
        raise pagure.exceptions.PagureException(
            'No tag "%s" found related to this project' % (old_tag_name))

    old_tag_name = old_tag.tag
    old_tag_description = old_tag.tag_description
    old_tag_color = old_tag.tag_color

    # check for change
    no_change_in_tag = old_tag.tag == new_tag \
        and old_tag_description == new_tag_description \
        and old_tag_color == new_tag_color
    if no_change_in_tag:
        raise pagure.exceptions.PagureException(
            'No change.  Old tag "%s(%s)[%s]" is the same as '
            'new tag "%s(%s)[%s]"' % (
                old_tag, old_tag_description, old_tag_color, new_tag,
                new_tag_description, new_tag_color))
    elif old_tag.tag != new_tag:
        # Check if new tag already exists
        existing_tag = get_colored_tag(session, new_tag, project.id)
        if existing_tag:
            raise pagure.exceptions.PagureException(
                'Can not rename a tag to an existing tag name: %s' % new_tag)

    session.query(
        model.TagColored
    ).filter(
        model.TagColored.tag == old_tag.tag
    ).filter(
        model.TagColored.project_id == project.id
    ).update(
        {
            model.TagColored.tag: new_tag,
            model.TagColored.tag_description: new_tag_description,
            model.TagColored.tag_color: new_tag_color
        }
    )

    issues = session.query(
        model.Issue
    ).filter(
        model.TagIssueColored.tag_id == old_tag.id
    ).filter(
        model.TagIssueColored.issue_uid == model.Issue.uid
    ).all()
    for issue in issues:
        # Update the git version
        pagure.lib.git.update_git(
            issue, repo=issue.project, repofolder=ticketfolder)

    msgs = []
    msgs.append(
        'Edited tag: %s(%s)[%s] to %s(%s)[%s]' % (
            old_tag_name, old_tag_description, old_tag_color,
            new_tag, new_tag_description, new_tag_color
        )
    )

    pagure.lib.notify.log(
        project,
        topic='project.tag.edited',
        msg=dict(
            project=project.to_json(public=True),
            old_tag=old_tag.tag,
            old_tag_description=old_tag_description,
            old_tag_color=old_tag_color,
            new_tag=new_tag,
            new_tag_description=new_tag_description,
            new_tag_color=new_tag_color,
            agent=user_obj.username,
        ),
        redis=REDIS,
    )

    return msgs


def add_deploykey_to_project(session, project, ssh_key, pushaccess, user):
    ''' Add a deploy key to a specified project. '''
    ssh_key = ssh_key.strip()

    if '\n' in ssh_key:
        raise pagure.exceptions.PagureException(
            'Deploy key can only be single keys.'
        )

    ssh_short_key = is_valid_ssh_key(ssh_key)
    if ssh_short_key in [None, False]:
        raise pagure.exceptions.PagureException(
            'Deploy key invalid.'
        )

    # We are sure that this only contains a single key, but ssh-keygen still
    # return a \n at the end
    ssh_short_key = ssh_short_key.split('\n')[0]

    # Make sure that this key is not a deploy key in this or another project.
    # If we dupe keys, gitolite might choke.
    ssh_search_key = ssh_short_key.split(' ')[1]
    if session.query(model.DeployKey).filter(
            model.DeployKey.ssh_search_key == ssh_search_key).count() != 0:
        raise pagure.exceptions.PagureException(
            'Deploy key already exists.'
        )

    user_obj = get_user(session, user)
    new_key_obj = model.DeployKey(
        project_id=project.id,
        pushaccess=pushaccess,
        public_ssh_key=ssh_key,
        ssh_short_key=ssh_short_key,
        ssh_search_key=ssh_search_key,
        creator_user_id=user_obj.id)

    session.add(new_key_obj)
    # Make sure we won't have SQLAlchemy error before we continue
    session.flush()

    # We do not send any notifications on purpose

    return 'Deploy key added'


def add_user_to_project(
        session, project, new_user, user, access='admin',
        required_groups=None):
    ''' Add a specified user to a specified project with a specified access
    '''

    new_user_obj = get_user(session, new_user)

    if required_groups and access != 'ticket':
        for key in required_groups:
            if fnmatch.fnmatch(project.fullname, key):
                user_grps = set(new_user_obj.groups)
                req_grps = set(required_groups[key])
                if not user_grps.intersection(req_grps):
                    raise pagure.exceptions.PagureException(
                        'This user must be in one of the following groups '
                        'to be allowed to be added to this project: %s' %
                        ', '.join(req_grps)
                    )

    user_obj = get_user(session, user)

    users = set([
        user_.user
        for user_ in project.get_project_users(access, combine=False)
    ])
    users.add(project.user.user)

    if new_user in users:
        raise pagure.exceptions.PagureException(
            'This user is already listed on this project with the same access'
        )

    # user has some access on project, so update to new access
    if new_user_obj in project.users:
        access_obj = get_obj_access(session, project, new_user_obj)
        access_obj.access = access
        project.date_modified = datetime.datetime.utcnow()
        update_read_only_mode(session, project, read_only=True)
        session.add(access_obj)
        session.add(project)
        session.flush()

        pagure.lib.notify.log(
            project,
            topic='project.user.access.updated',
            msg=dict(
                project=project.to_json(public=True),
                new_user=new_user_obj.username,
                new_access=access,
                agent=user_obj.username,
            ),
            redis=REDIS,
        )

        return 'User access updated'

    project_user = model.ProjectUser(
        project_id=project.id,
        user_id=new_user_obj.id,
        access=access,
    )
    project.date_modified = datetime.datetime.utcnow()
    session.add(project_user)
    # Mark the project as read only, celery will then unmark it
    update_read_only_mode(session, project, read_only=True)
    session.add(project)
    # Make sure we won't have SQLAlchemy error before we continue
    session.flush()

    pagure.lib.notify.log(
        project,
        topic='project.user.added',
        msg=dict(
            project=project.to_json(public=True),
            new_user=new_user_obj.username,
            access=access,
            agent=user_obj.username,
        ),
        redis=REDIS,
    )

    return 'User added'


def add_group_to_project(
        session, project, new_group, user, access='admin',
        create=False, is_admin=False):
    ''' Add a specified group to a specified project with some access '''

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
                display_name=new_group,
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

    groups = set([
        group.group_name
        for group in project.get_project_groups(access, combine=False)
    ])

    if new_group in groups:
        raise pagure.exceptions.PagureException(
            'This group already has this access on this project'
        )

    # the group already has some access, update to new access
    if group_obj in project.groups:
        access_obj = get_obj_access(session, project, group_obj)
        access_obj.access = access
        session.add(access_obj)
        project.date_modified = datetime.datetime.utcnow()
        update_read_only_mode(session, project, read_only=True)
        session.add(project)
        session.flush()

        pagure.lib.notify.log(
            project,
            topic='project.group.access.updated',
            msg=dict(
                project=project.to_json(public=True),
                new_group=group_obj.group_name,
                new_access=access,
                agent=user,
            ),
            redis=REDIS,
        )

        return 'Group access updated'

    project_group = model.ProjectGroup(
        project_id=project.id,
        group_id=group_obj.id,
        access=access,
    )
    session.add(project_group)
    # Make sure we won't have SQLAlchemy error before we continue
    project.date_modified = datetime.datetime.utcnow()
    # Mark the project read_only, celery will then unmark it
    update_read_only_mode(session, project, read_only=True)
    session.add(project)
    session.flush()

    pagure.lib.notify.log(
        project,
        topic='project.group.added',
        msg=dict(
            project=project.to_json(public=True),
            new_group=group_obj.group_name,
            access=access,
            agent=user,
        ),
        redis=REDIS,
    )

    return 'Group added'


def add_pull_request_comment(session, request, commit, tree_id, filename,
                             row, comment, user, requestfolder,
                             notify=True, notification=False,
                             trigger_ci=None):
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

    request.last_updated = datetime.datetime.utcnow()

    pagure.lib.git.update_git(
        request, repo=request.project, repofolder=requestfolder)

    log_action(session, 'commented', request, user_obj)

    if notify:
        pagure.lib.notify.notify_pull_request_comment(pr_comment, user_obj)

    # Send notification for the event-source server
    if REDIS and not request.project.private:
        comment_text = text2markdown(pr_comment.comment)

        REDIS.publish('pagure.%s' % request.uid, json.dumps({
            'request_id': request.id,
            'comment_added': comment_text,
            'comment_user': pr_comment.user.user,
            'comment_id': pr_comment.id,
            'avatar_url': avatar_url_from_email(
                pr_comment.user.default_email, size=16),
            'comment_date': pr_comment.date_created.strftime(
                '%Y-%m-%d %H:%M:%S'),
            'commit_id': commit,
            'filename': filename,
            'line': row,
            'notification': notification,
        }))

        # Send notification to the CI server, if the comment added was a
        # notification and the PR is still open and project is not private
        if notification and request.status == 'Open' \
            and PAGURE_CI and request.project.ci_hook\
                and not request.project.private:
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

    if trigger_ci and comment.strip().lower() in trigger_ci:
        # Send notification to the CI server
        if REDIS and PAGURE_CI and request.project.ci_hook:
            REDIS.publish('pagure.ci', json.dumps({
                'ci_type': request.project.ci_hook.ci_type,
                'pr': request.to_json(public=True, with_comments=False)
            }))

    return 'Comment added'


def edit_comment(session, parent, comment, user,
                 updated_comment, folder):
    ''' Edit a comment. '''
    user_obj = get_user(session, user)
    comment.comment = updated_comment
    comment.edited_on = datetime.datetime.utcnow()
    comment.editor = user_obj
    parent.last_updated = comment.edited_on

    session.add(parent)
    session.add(comment)
    # Make sure we won't have SQLAlchemy error before we continue
    session.flush()

    pagure.lib.git.update_git(
        parent, repo=parent.project, repofolder=folder)

    topic = 'unknown'
    key = 'unknown'
    id_ = 'unknown'
    private = False
    if parent.isa == 'pull-request':
        topic = 'pull-request.comment.edited'
        key = 'pullrequest'
        id_ = 'request_id'
    elif parent.isa == 'issue':
        topic = 'issue.comment.edited'
        key = 'issue'
        id_ = 'issue_id'
        private = parent.private

    if not private:
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

    if REDIS and not parent.project.private:
        if private:
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
                'avatar_url': avatar_url_from_email(
                    comment.user.default_email, size=16),
                'comment_date': comment.edited_on.strftime(
                    '%Y-%m-%d %H:%M:%S'),
            }))

    return "Comment updated"


def add_pull_request_flag(session, request, username, percent, comment, url,
                          status, uid, user, token, requestfolder):
    ''' Add a flag to a pull-request. '''
    user_obj = get_user(session, user)

    action = 'added'
    pr_flag = get_pull_request_flag_by_uid(session, request, uid)
    if pr_flag:
        action = 'updated'
        pr_flag.comment = comment
        pr_flag.status = status
        pr_flag.percent = percent
        pr_flag.url = url
    else:
        pr_flag = model.PullRequestFlag(
            pull_request_uid=request.uid,
            uid=uid or uuid.uuid4().hex,
            username=username,
            percent=percent,
            comment=comment,
            status=status,
            url=url,
            user_id=user_obj.id,
            token_id=token,
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

    return ('Flag %s' % action, pr_flag.uid)


def add_commit_flag(
        session, repo, commit_hash, username, status, percent, comment, url,
        uid, user, token):
    ''' Add a flag to a add_commit_flag. '''
    user_obj = get_user(session, user)

    action = 'added'
    c_flag = get_commit_flag_by_uid(session, commit_hash, uid)
    if c_flag:
        action = 'updated'
        c_flag.comment = comment
        c_flag.percent = percent
        c_flag.status = status
        c_flag.url = url
    else:
        c_flag = model.CommitFlag(
            uid=uid or uuid.uuid4().hex,
            project_id=repo.id,
            commit_hash=commit_hash,
            username=username,
            status=status,
            percent=percent,
            comment=comment,
            url=url,
            user_id=user_obj.id,
            token_id=token,
        )
    session.add(c_flag)
    # Make sure we won't have SQLAlchemy error before we continue
    session.flush()

    pagure.lib.notify.log(
        repo,
        topic='commit.flag.%s' % action,
        msg=dict(
            repo=repo.to_json(public=True),
            flag=c_flag.to_json(public=True),
            agent=user_obj.username,
        ),
        redis=REDIS,
    )

    return ('Flag %s' % action, c_flag.uid)


def get_commit_flag(session, project, commit_hash):
    ''' Return the commit flags corresponding to the specified git hash
    (commitid) in the specified repository.

    :arg session: the session with which to connect to the database
    :arg repo: the pagure.lib.model.Project object corresponding to the
        project whose commit has been flagged
    :arg commit_hash: the hash of the commit who has been flagged
    :return: list of pagure.lib.model.CommitFlag objects or an empty list

    '''
    query = session.query(
        model.CommitFlag
    ).filter(
        model.CommitFlag.project_id == project.id
    ).filter(
        model.CommitFlag.commit_hash == commit_hash
    )

    return query.all()


def new_project(session, user, name, blacklist, allowed_prefix,
                gitfolder, docfolder, ticketfolder, requestfolder,
                description=None, url=None, avatar_email=None,
                parent_id=None, add_readme=False, userobj=None,
                prevent_40_chars=False, namespace=None, user_ns=False,
                ignore_existing_repo=False, private=False):
    ''' Create a new project based on the information provided.

    Is an async operation, and returns task ID.
    '''
    if (not namespace and name in blacklist) \
            or (namespace and '%s/%s' % (namespace, name) in blacklist):
        raise pagure.exceptions.ProjectBlackListedException(
            'No project "%s" are allowed to be created due to potential '
            'conflicts in URLs with pagure itself' % name
        )

    user_obj = get_user(session, user)
    allowed_prefix = allowed_prefix + [grp for grp in user_obj.groups]
    if user_ns:
        allowed_prefix.append(user)
        if not namespace:
            namespace = user
    if private:
        allowed_prefix.append(user)
        namespace = user

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

    # Repo exists on disk
    gitrepo = os.path.join(gitfolder, '%s.git' % path)
    if os.path.exists(gitrepo):
        if not ignore_existing_repo:
            raise pagure.exceptions.RepoExistsException(
                'The project repo "%s" already exists' % path
            )

    # Repo exists in the DB
    repo = pagure.get_authorized_project(session, name, namespace=namespace)
    if repo:
        raise pagure.exceptions.RepoExistsException(
            'The project repo "%s" already exists in the database' % (
                path)
        )

    project = model.Project(
        name=name,
        namespace=namespace,
        description=description if description else None,
        url=url if url else None,
        avatar_email=avatar_email if avatar_email else None,
        user_id=user_obj.id,
        parent_id=parent_id,
        private=private,
        hook_token=pagure.lib.login.id_generator(40)
    )
    session.add(project)
    # Flush so that a project ID is generated
    session.flush()
    for ltype in model.ProjectLock.lock_type.type.enums:
        lock = model.ProjectLock(
            project_id=project.id,
            lock_type=ltype)
        session.add(lock)
    session.commit()

    # Register creation et al
    log_action(session, 'created', project, user_obj)

    pagure.lib.notify.log(
        project,
        topic='project.new',
        msg=dict(
            project=project.to_json(public=True),
            agent=user_obj.username,
        ),
    )

    return tasks.create_project.delay(user_obj.username, namespace, name,
                                      add_readme, ignore_existing_repo).id


def new_issue(session, repo, title, content, user, ticketfolder, issue_id=None,
              issue_uid=None, private=False, status=None, close_status=None,
              notify=True, date_created=None, milestone=None, priority=None,
              assignee=None, tags=None):
    ''' Create a new issue for the specified repo. '''
    user_obj = get_user(session, user)

    # Only store the priority if there is one in the project
    priorities = repo.priorities or []
    try:
        priority = int(priority)
    except (ValueError, TypeError):
        priority = None
    if priorities \
            and priority is not None \
            and str(priority) not in priorities:
        raise pagure.exceptions.PagureException(
            'You are trying to create an issue with a priority that does '
            'not exist in the project.')

    assignee_id = None
    if assignee is not None:
        assignee_id = get_user(session, assignee).id

    issue = model.Issue(
        id=issue_id or get_next_id(session, repo.id),
        project_id=repo.id,
        title=title,
        content=content,
        priority=priority,
        milestone=milestone,
        assignee_id=assignee_id,
        user_id=user_obj.id,
        uid=issue_uid or uuid.uuid4().hex,
        private=private,
        date_created=date_created,
    )

    if status is not None:
        issue.status = status
    if close_status is not None:
        issue.close_status = close_status
    issue.last_updated = datetime.datetime.utcnow()

    session.add(issue)
    # Make sure we won't have SQLAlchemy error before we create the issue
    session.flush()

    # Add the tags if any are specified
    if tags is not None:
        for lbl in tags:
            tagobj = get_colored_tag(session, lbl, repo.id)
            if not tagobj:
                tagobj = model.TagColored(
                    tag=lbl,
                    project_id=repo.id
                )
                session.add(tagobj)
                session.flush()

            dbobjtag = model.TagIssueColored(
                issue_uid=issue.uid,
                tag_id=tagobj.id
            )
            session.add(dbobjtag)

    session.commit()

    pagure.lib.git.update_git(
        issue, repo=repo, repofolder=ticketfolder)

    log_action(session, 'created', issue, user_obj)

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
                     status='Open', notify=True,
                     commit_start=None, commit_stop=None):
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
        commit_start=commit_start,
        commit_stop=commit_stop,
    )
    request.last_updated = datetime.datetime.utcnow()

    session.add(request)
    # Make sure we won't have SQLAlchemy error before we create the request
    session.flush()

    pagure.lib.git.update_git(
        request, repo=request.project, repofolder=requestfolder)

    log_action(session, 'created', request, user_obj)

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
    if REDIS and PAGURE_CI and request.project.ci_hook \
            and not request.project.private:
        REDIS.publish('pagure.ci', json.dumps({
            'ci_type': request.project.ci_hook.ci_type,
            'pr': request.to_json(public=True, with_comments=False)
        }))

    # Create the ref from the start
    tasks.sync_pull_ref.delay(
        request.project.name,
        request.project.namespace,
        request.project.user.username if request.project.is_fork else None,
        request.id
    )

    return request


def new_tag(session, tag_name, tag_description, tag_color, project_id):
    ''' Return a new tag object '''
    tagobj = model.TagColored(
        tag=tag_name,
        tag_description=tag_description,
        tag_color=tag_color,
        project_id=project_id
    )
    session.add(tagobj)
    session.flush()

    return tagobj


def edit_issue(session, issue, ticketfolder, user, repo=None,
               title=None, content=None, status=None,
               close_status=Unspecified, priority=Unspecified,
               milestone=Unspecified, private=None):
    ''' Edit the specified issue.

    :arg session: the session to use to connect to the database.
    :arg issue: the pagure.lib.model.Issue object to edit.
    :arg ticketfolder: the path to the git repo storing the meta-data of
        the issues of this repo
    :arg user: the username of the user editing the issue,
    :kwarg repo: somehow this isn't used anywhere here...
    :kwarg title: the new title of the issue if it's being changed
    :kwarg content: the new content of the issue if it's being changed
    :kwarg status: the new status of the issue if it's being changed
    :kwarg close_status: the new close_status of the issue if it's being
        changed
    :kwarg priority: the new priority of the issue if it's being changed
    :kwarg milestone: the new milestone of the issue if it's being changed
    :kwarg private: the new private of the issue if it's being changed

    '''
    user_obj = get_user(session, user)
    if status and status != 'Open' and issue.parents:
        for parent in issue.parents:
            if parent.status == 'Open':
                raise pagure.exceptions.PagureException(
                    'You cannot close a ticket that has ticket '
                    'depending that are still open.')

    edit = []
    messages = []
    if title and title != issue.title:
        issue.title = title
        edit.append('title')
    if content and content != issue.content:
        issue.content = content
        edit.append('content')
    if status and status != issue.status:
        old_status = issue.status
        issue.status = status
        if status.lower() != 'open':
            issue.closed_at = datetime.datetime.utcnow()
        elif issue.close_status:
            issue.close_status = None
            close_status = Unspecified
            edit.append('close_status')
        edit.append('status')
        messages.append(
            'Issue status updated to: %s (was: %s)' % (status, old_status))
    if close_status != Unspecified and close_status != issue.close_status:
        old_status = issue.close_status
        issue.close_status = close_status
        edit.append('close_status')
        msg = 'Issue close_status updated to: %s' % close_status
        if old_status:
            msg += ' (was: %s)' % old_status
        if issue.status.lower() == 'open' and close_status:
            issue.status = 'Closed'
            issue.closed_at = datetime.datetime.utcnow()
            edit.append('status')
        messages.append(msg)
    if priority != Unspecified:
        priorities = issue.project.priorities
        try:
            priority = int(priority)
        except (ValueError, TypeError):
            priority = None

        if str(priority) not in priorities:
            priority = None

        if priority != issue.priority:
            old_priority = issue.priority
            issue.priority = priority
            edit.append('priority')
            msg = 'Issue priority set to: %s' % (
                priorities[str(priority)] if priority else None)
            if old_priority:
                msg += ' (was: %s)' % priorities.get(
                    str(old_priority), old_priority)
            messages.append(msg)
    if private in [True, False] and private != issue.private:
        old_private = issue.private
        issue.private = private
        edit.append('private')
        msg = 'Issue private status set to: %s' % private
        if old_private:
            msg += ' (was: %s)' % old_private
        messages.append(msg)
    if milestone != Unspecified and milestone != issue.milestone:
        old_milestone = issue.milestone
        issue.milestone = milestone
        edit.append('milestone')
        msg = 'Issue set to the milestone: %s' % milestone
        if old_milestone:
            msg += ' (was: %s)' % old_milestone
        messages.append(msg)
    issue.last_updated = datetime.datetime.utcnow()
    # uniquify the list of edited fields
    edit = list(set(edit))

    pagure.lib.git.update_git(
        issue, repo=issue.project, repofolder=ticketfolder)

    if 'status' in edit:
        log_action(session, issue.status.lower(), issue, user_obj)
        pagure.lib.notify.notify_status_change_issue(issue, user_obj)

    if not issue.private and edit:
        pagure.lib.notify.log(
            issue.project,
            topic='issue.edit',
            msg=dict(
                issue=issue.to_json(public=True),
                project=issue.project.to_json(public=True),
                fields=list(set(edit)),
                agent=user_obj.username,
            ),
            redis=REDIS,
        )

    if REDIS and edit and not issue.project.private:
        if issue.private:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps({
                'issue': 'private',
                'fields': edit,
            }))
        else:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps({
                'fields': edit,
                'issue': issue.to_json(public=True, with_comments=False),
                'priorities': issue.project.priorities,
            }))

    if edit:
        session.add(issue)
        session.flush()
        return messages


def update_project_settings(session, repo, settings, user):
    ''' Update the settings of a project. '''
    user_obj = get_user(session, user)

    update = []
    new_settings = repo.settings
    for key in new_settings:
        if key in settings:
            if key == 'Minimum_score_to_merge_pull-request':
                try:
                    settings[key] = int(settings[key]) \
                        if settings[key] else -1
                except (ValueError, TypeError):
                    raise pagure.exceptions.PagureException(
                        "Please enter a numeric value for the 'minimum "
                        "score to merge pull request' field.")
            elif key == 'Web-hooks':
                settings[key] = settings[key] or None
            else:
                # All the remaining keys are boolean, so True is provided
                # as 'y' by the html, let's convert it back
                settings[key] = settings[key] in ['y', True]

            if new_settings[key] != settings[key]:
                update.append(key)
                new_settings[key] = settings[key]
        else:
            val = False
            if key == 'Web-hooks':
                val = None

            # Ensure the default value is different from what is stored.
            if new_settings[key] != val:
                update.append(key)
                new_settings[key] = val

    if not update:
        return 'No settings to change'
    else:
        repo.settings = new_settings
        repo.date_modified = datetime.datetime.utcnow()
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

        if 'pull_request_access_only' in update:
            update_read_only_mode(session, repo, read_only=True)
            session.add(repo)
            session.flush()
            pagure.lib.git.generate_gitolite_acls(project=repo)

        return 'Edited successfully settings of repo: %s' % repo.fullname


def update_user_settings(session, settings, user):
    ''' Update the settings of a project. '''
    user_obj = get_user(session, user)

    update = []
    new_settings = user_obj.settings
    for key in new_settings:
        if key in settings:
            if new_settings[key] != settings[key]:
                update.append(key)
                new_settings[key] = settings[key]
        else:
            if new_settings[key] is not False:
                update.append(key)
                new_settings[key] = False

    if not update:
        return 'No settings to change'
    else:
        user_obj.settings = new_settings
        session.add(user_obj)
        session.flush()

        return 'Successfully edited your settings'


def fork_project(session, user, repo, gitfolder,
                 docfolder, ticketfolder, requestfolder,
                 editbranch=None, editfile=None):
    ''' Fork a given project into the user's forks. '''
    forkreponame = '%s.git' % os.path.join(
        gitfolder, 'forks', user,
        repo.namespace if repo.namespace else '', repo.name)

    if os.path.exists(forkreponame):
        raise pagure.exceptions.RepoExistsException(
            'Repo "forks/%s/%s" already exists' % (user, repo.name))

    user_obj = get_user(session, user)

    project = model.Project(
        name=repo.name,
        namespace=repo.namespace,
        description=repo.description,
        private=repo.private,
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
    session.commit()

    task = tasks.fork.delay(repo.name,
                            repo.namespace,
                            repo.user.username if repo.is_fork else None,
                            user,
                            editbranch,
                            editfile)
    return task.id


def search_projects(
        session, username=None,
        fork=None, tags=None, namespace=None, pattern=None,
        start=None, limit=None, count=False, sort=None,
        exclude_groups=None, private=None, owner=None):
    '''List existing projects
    '''
    projects = session.query(
        sqlalchemy.distinct(model.Project.id)
    )

    if owner is not None and username is not None:
        raise RuntimeError('You cannot supply both a username and an owner '
                           'as parameters in the `search_projects` function')
    elif owner is not None:
        projects = projects.join(model.User).filter(model.User.user == owner)
    elif username is not None:
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
            # User got admin or commit right
            sqlalchemy.and_(
                model.User.user == username,
                model.User.id == model.ProjectUser.user_id,
                model.ProjectUser.project_id == model.Project.id,
                sqlalchemy.or_(
                    model.ProjectUser.access == 'admin',
                    model.ProjectUser.access == 'commit',
                )
            )
        )
        sub_q3 = session.query(
            model.Project.id
        ).filter(
            # User created a group that has admin or commit right
            sqlalchemy.and_(
                model.User.user == username,
                model.PagureGroup.user_id == model.User.id,
                model.PagureGroup.group_type == 'user',
                model.PagureGroup.id == model.ProjectGroup.group_id,
                model.Project.id == model.ProjectGroup.project_id,
                sqlalchemy.or_(
                    model.ProjectGroup.access == 'admin',
                    model.ProjectGroup.access == 'commit',
                )
            )
        )
        sub_q4 = session.query(
            model.Project.id
        ).filter(
            # User is part of a group that has admin or commit right
            sqlalchemy.and_(
                model.User.user == username,
                model.PagureUserGroup.user_id == model.User.id,
                model.PagureUserGroup.group_id == model.PagureGroup.id,
                model.PagureGroup.group_type == 'user',
                model.PagureGroup.id == model.ProjectGroup.group_id,
                model.Project.id == model.ProjectGroup.project_id,
                sqlalchemy.or_(
                    model.ProjectGroup.access == 'admin',
                    model.ProjectGroup.access == 'commit',
                )

            )
        )

        # Exclude projects that the user has accessed via a group that we
        # do not want to include
        if exclude_groups:
            sub_q3 = sub_q3.filter(
                model.PagureGroup.group_name.notin_(exclude_groups)
            )
            sub_q4 = sub_q4.filter(
                model.PagureGroup.group_name.notin_(exclude_groups)
            )

        projects = projects.union(sub_q2).union(sub_q3).union(sub_q4)

    if not private:
        projects = projects.filter(
            model.Project.private == False  # noqa: E712
        )
    # No filtering is done if private == username i.e  if the owner of the
    # project is viewing the project
    elif isinstance(private, basestring) and private != username:
        projects = projects.filter(
            sqlalchemy.or_(
                model.Project.private == False,  # noqa: E712
                sqlalchemy.and_(
                    model.User.user == private,
                    model.User.id == model.ProjectUser.user_id,
                    model.ProjectUser.project_id == model.Project.id,
                    model.Project.private == True,
                )
            )
        )

    if fork is not None:
        if fork is True:
            projects = projects.filter(
                model.Project.is_fork == True  # noqa: E712
            )
        elif fork is False:
            projects = projects.filter(
                model.Project.is_fork == False  # noqa: E712
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
                model.Project.name.ilike(pattern)
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


def _get_project(session, name, user=None, namespace=None, case=False):
    '''Get a project from the database
    '''
    query = session.query(
        model.Project
    )

    if not case:
        query = query.filter(
            func.lower(model.Project.name) == name.lower()
        )
    else:
        query = query.filter(
            model.Project.name == name
        )

    if namespace:
        if not case:
            query = query.filter(
                func.lower(model.Project.namespace) == namespace.lower()
            )
        else:
            query = query.filter(
                model.Project.namespace == namespace
            )
    else:
        query = query.filter(model.Project.namespace == namespace)

    if user is not None:
        query = query.filter(
            model.User.user == user
        ).filter(
            model.User.id == model.Project.user_id
        ).filter(
            model.Project.is_fork == True  # noqa: E712
        )
    else:
        query = query.filter(
            model.Project.is_fork == False  # noqa: E712
        )

    return query.first()


def search_issues(
        session, repo=None, issueid=None, issueuid=None, status=None,
        closed=False, tags=None, assignee=None, author=None, private=None,
        priority=None, milestones=None, count=False, offset=None,
        limit=None, search_pattern=None, custom_search=None,
        updated_after=None, no_milestones=None, order='desc',
        order_key=None):
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
    :kwarg search_pattern: a string to search in issues title
    :type search_pattern: str or None
    :kwarg custom_search: a dictionary of key/values to be used when
        searching issues with a custom key constraint
    :type custom_search: dict or None
    :kwarg updated_after: datetime's date format (e.g. 2016-11-15) used to
        filter issues updated after that date
    :type updated_after: str or None
    :kwarg no_milestones: Request issues that do not have a milestone set yet
    :type None, True, or False
    :kwarg order: Order issues in 'asc' or 'desc' order.
    :type order: None, str
    :kwarg order_key: Order issues by database column
    :type order_key: None, str

    :return: A single Issue object if issueid is specified, a list of Project
        objects otherwise.
    :rtype: Project or [Project]

    '''
    query = session.query(
        sqlalchemy.distinct(model.Issue.uid)
    )

    if repo is not None:
        query = query.filter(
            model.Issue.project_id == repo.id
        )

    if updated_after:
        query = query.filter(
            model.Issue.last_updated >= updated_after
        )

    if issueid is not None:
        query = query.filter(
            model.Issue.id == issueid
        )

    if issueuid is not None:
        query = query.filter(
            model.Issue.uid == issueuid
        )

    if status is not None:
        if status in ['Open', 'Closed']:
            query = query.filter(
                model.Issue.status == status
            )
        else:
            query = query.filter(
                model.Issue.close_status == status
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
            )
            if repo is not None:
                sub_q2 = sub_q2.filter(
                    model.Issue.project_id == repo.id
                )
            sub_q2 = sub_q2.filter(
                model.Issue.uid == model.TagIssueColored.issue_uid
            ).filter(
                model.TagIssueColored.tag_id == model.TagColored.id
            ).filter(
                model.TagColored.tag.in_(ytags)
            )
        if notags:
            sub_q3 = session.query(
                sqlalchemy.distinct(model.Issue.uid)
            )
            if repo is not None:
                sub_q3 = sub_q3.filter(
                    model.Issue.project_id == repo.id
                )
            sub_q3 = sub_q3.filter(
                model.Issue.uid == model.TagIssueColored.issue_uid
            ).filter(
                model.TagIssueColored.tag_id == model.TagColored.id
            ).filter(
                model.TagColored.tag.in_(notags)
            )
        # Adjust the main query based on the parameters specified
        if ytags and not notags:
            query = query.filter(model.Issue.uid.in_(sub_q2))
        elif not ytags and notags:
            query = query.filter(~model.Issue.uid.in_(sub_q3))
        elif ytags and notags:
            final_set = set(
                [i[0] for i in sub_q2.all()]
            ) - set(
                [i[0] for i in sub_q3.all()]
            )
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
                model.Issue.assignee_id.isnot(None)
            )
        else:
            query = query.filter(
                model.Issue.assignee_id.is_(None)
            )
    if author is not None:
        query = query.filter(
            model.Issue.user_id == model.User.id
        ).filter(
            model.User.user == author
        )

    if private is False:
        query = query.filter(
            model.Issue.private == False  # noqa: E712
        )
    elif isinstance(private, basestring):
        user2 = aliased(model.User)
        query = query.filter(
            sqlalchemy.or_(
                model.Issue.private == False,  # noqa: E712
                sqlalchemy.and_(
                    model.Issue.private == True,  # noqa: E712
                    model.Issue.user_id == user2.id,
                    user2.user == private,
                )
            )
        )

    if no_milestones and milestones is not None and milestones != []:
        # Asking for issues with no milestone or a specific milestone
        if isinstance(milestones, basestring):
            milestones = [milestones]
        query = query.filter(
            (model.Issue.milestone.is_(None)) |
            (model.Issue.milestone.in_(milestones))
        )
    elif no_milestones:
        # Asking for issues without a milestone
        query = query.filter(
            model.Issue.milestone.is_(None)
        )
    elif milestones is not None and milestones != []:
        # Asking for a single specific milestone
        if isinstance(milestones, basestring):
            milestones = [milestones]
        query = query.filter(
            model.Issue.milestone.in_(milestones)
        )
    elif no_milestones is False:
        # Asking for all ticket with a milestone
        query = query.filter(
            model.Issue.milestone.isnot(None)
        )

    if custom_search:
        constraints = []
        for key in custom_search:
            value = custom_search[key]
            if '*' in value:
                value = value.replace('*', '%')
                constraints.append(
                    sqlalchemy.and_(
                        model.IssueKeys.name == key,
                        model.IssueValues.value.ilike(value)
                    )
                )
            else:
                constraints.append(
                    sqlalchemy.and_(
                        model.IssueKeys.name == key,
                        model.IssueValues.value == value
                    )
                )
        if constraints:
            query = query.filter(
                model.Issue.uid == model.IssueValues.issue_uid
            ).filter(
                model.IssueValues.key_id == model.IssueKeys.id
            )
            query = query.filter(
                sqlalchemy.or_(
                    (const for const in constraints)
                )
            )

    query = session.query(
        model.Issue
    ).filter(
        model.Issue.uid.in_(query.subquery())
    )

    if repo is not None:
        query = query.filter(
            model.Issue.project_id == repo.id
        )

    if search_pattern is not None:
        query = query.filter(
            model.Issue.title.ilike('%%%s%%' % search_pattern)
        )

    column = model.Issue.date_created
    if order_key:
        # If we are ordering by assignee, then order by the assignees'
        # usernames
        if order_key == 'assignee':
            # We must do a LEFT JOIN on model.Issue.assignee because there are
            # two foreign keys on model.Issue tied to model.User. This tells
            # SQLAlchemy which foreign key on model.User to order on.
            query = query.outerjoin(model.User, model.Issue.assignee)
            column = model.User.user
        # If we are ordering by user, then order by reporters' usernames
        elif order_key == 'user':
            # We must do a LEFT JOIN on model.Issue.user because there are
            # two foreign keys on model.Issue tied to model.User. This tells
            # SQLAlchemy which foreign key on model.User to order on.
            query = query.outerjoin(model.User, model.Issue.user)
            column = model.User.user
        elif order_key in model.Issue.__table__.columns.keys():
            column = getattr(model.Issue, order_key)

    if str(column.type) == 'TEXT':
        column = func.lower(column)

    # The priority is sorted differently because it is by weight and the lower
    # the number, the higher the priority
    if (order_key != 'priority' and order == 'asc') or \
            (order_key == 'priority' and order == 'desc'):
        query = query.order_by(asc(column))
    else:
        query = query.order_by(desc(column))

    if issueid is not None or issueuid is not None:
        output = query.first()
    elif count:
        output = query.count()
    else:
        if offset is not None:
            query = query.offset(offset)
        if limit:
            query = query.limit(limit)
        output = query.all()

    return output


def get_tags_of_project(session, project, pattern=None):
    ''' Returns the list of tags associated with the issues of a project.
    '''
    query = session.query(
        model.TagColored
    ).filter(
        model.TagColored.tag != ""
    ).filter(
        model.TagColored.project_id == project.id
    ).order_by(
        model.TagColored.tag
    )

    if pattern:
        query = query.filter(
            model.TagColored.tag.ilike(pattern.replace('*', '%'))
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


def get_colored_tag(session, tag, project_id):
    ''' Returns a TagColored object for the given tag text.
    '''
    query = session.query(
        model.TagColored
    ).filter(
        model.TagColored.tag == tag
    ).filter(
        model.TagColored.project_id == project_id
    )

    return query.first()


def search_pull_requests(
        session, requestid=None, project_id=None, project_id_from=None,
        status=None, author=None, assignee=None, count=False,
        offset=None, limit=None, updated_after=None, branch_from=None):
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

    if updated_after:
        query = query.filter(
            model.PullRequest.last_updated >= updated_after
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
                model.PullRequest.assignee_id.isnot(None)
            )
        else:
            query = query.filter(
                model.PullRequest.assignee_id.is_(None)
            )

    if author is not None:
        query = query.filter(
            model.PullRequest.user_id == model.User.id
        ).filter(
            model.User.user == author
        )

    if branch_from is not None:
        query = query.filter(
            model.PullRequest.branch_from == branch_from
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

    log_action(session, request.status.lower(), request, user_obj)

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
    session.query(
        model.PullRequest
    ).filter(
        model.PullRequest.project_id == project.id
    ).filter(
        model.PullRequest.status == 'Open'
    ).update(
        {model.PullRequest.merge_status: None}
    )

    session.commit()


def add_attachment(repo, issue, attachmentfolder, user, filename, filestream):
    ''' Add a file to the attachments folder of repo and update git. '''
    _log.info(
        'Adding file: %s to the git repo: %s',
        repo.path, werkzeug.secure_filename(filename))

    # Prefix the filename with a timestamp:
    filename = '%s-%s' % (
        hashlib.sha256(filestream.read()).hexdigest(),
        werkzeug.secure_filename(filename)
    )
    filedir = os.path.join(attachmentfolder, repo.fullname, 'files')
    filepath = os.path.join(filedir, filename)

    if os.path.exists(filepath):
        return filename

    if not os.path.exists(filedir):
        os.makedirs(filedir)

    # Write file
    filestream.seek(0)
    with open(filepath, 'w') as stream:
        stream.write(filestream.read())

    tasks.add_file_to_git.delay(
        repo.name, repo.namespace,
        repo.user.username if repo.is_fork else None,
        user.username, issue.uid, filename)

    return filename


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


def get_issue_comment_by_user_and_comment(
        session, issue_uid, user_id, content):
    ''' Return a specific comment of a specified issue.
    '''
    query = session.query(
        model.IssueComment
    ).filter(
        model.IssueComment.issue_uid == issue_uid
    ).filter(
        model.IssueComment.user_id == user_id
    ).filter(
        model.IssueComment.comment == content
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


def get_pull_request_flag_by_uid(session, request, flag_uid):
    ''' Return the flag corresponding to the specified unique identifier.

    :arg session: the session to use to connect to the database.
    :arg request: the pull-request that was flagged
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
        model.PullRequestFlag.pull_request_uid == request.uid
    ).filter(
        model.PullRequestFlag.uid == flag_uid.strip()
    )
    return query.first()


def get_commit_flag_by_uid(session, commit_hash, flag_uid):
    ''' Return the flag corresponding to the specified unique identifier.

    :arg session: the session to use to connect to the database.
    :arg commit_hash: the hash of the commit that got flagged
    :arg flag_uid: the unique identifier of a request. This identifier is
        unique accross all flags on this pagure instance and should be
        unique accross multiple pagure instances as well
    :type request_uid: str or None

    :return: A single Issue object.
    :rtype: pagure.lib.model.PullRequestFlag

    '''
    query = session.query(
        model.CommitFlag
    ).filter(
        model.CommitFlag.commit_hash == commit_hash
    ).filter(
        model.CommitFlag.uid == flag_uid.strip() if flag_uid else None
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
        if email_logs_count(session, user_email):
            update_log_email_user(session, user_email, user)


def update_user_ssh(session, user, ssh_key, keydir):
    ''' Set up a new user into the database or update its information. '''
    if isinstance(user, basestring):
        user = get_user(session, user)

    user.public_ssh_key = ssh_key
    if keydir and user.public_ssh_key:
        create_user_ssh_keys_on_disk(user, keydir)
        pagure.lib.git.generate_gitolite_acls(project=None)
    session.add(user)
    session.flush()


def avatar_url_from_email(email, size=64, default='retro', dns=False):
    """
    Our own implementation since fas doesn't support this nicely yet.
    """
    if isinstance(email, unicode):
        email = email.encode('utf-8')

    if dns:  # pragma: no cover
        # This makes an extra DNS SRV query, which can slow down our webapps.
        # It is necessary for libravatar federation, though.
        import libravatar
        return libravatar.libravatar_url(
            openid=email,
            size=size,
            default=default,
        )
    else:
        import urllib
        query = urllib.urlencode({'s': size, 'd': default})
        hashhex = hashlib.sha256(email).hexdigest()
        return "https://seccdn.libravatar.org/avatar/%s?%s" % (
            hashhex, query)


def update_tags(session, obj, tags, username, gitfolder):
    """ Update the tags of a specified object (adding or removing them).
    This object can be either an issue or a project.

    """
    if isinstance(tags, basestring):
        tags = [tags]

    toadd = set(tags) - set(obj.tags_text)
    torm = set(obj.tags_text) - set(tags)
    messages = []
    if toadd:
        add_tag_obj(
            session,
            obj=obj,
            tags=toadd,
            user=username,
            gitfolder=gitfolder,
        )
        messages.append('%s tagged with: %s' % (
            obj.isa.capitalize(), ', '.join(sorted(toadd))))

    if torm:
        remove_tags_obj(
            session,
            obj=obj,
            tags=torm,
            user=username,
            gitfolder=gitfolder,
        )
        messages.append('%s **un**tagged with: %s' % (
            obj.isa.capitalize(), ', '.join(sorted(torm))))

    session.commit()

    return messages


def update_dependency_issue(
        session, repo, issue, depends, username, ticketfolder):
    """ Update the dependency of a specified issue (adding or removing them)

    """
    if isinstance(depends, basestring):
        depends = [depends]

    toadd = set(depends) - set(issue.depending_text)
    torm = set(issue.depending_text) - set(depends)
    messages = []

    # Add issue depending
    for depend in sorted([int(i) for i in toadd]):
        messages.append("Issue marked as depending on: #%s" % depend)
        issue_depend = search_issues(session, repo, issueid=depend)
        if issue_depend is None:
            continue
        if issue_depend.id in issue.depending_text:  # pragma: no cover
            # we should never be in this case but better safe than sorry...
            continue

        add_issue_dependency(
            session,
            issue=issue_depend,
            issue_blocked=issue,
            user=username,
            ticketfolder=ticketfolder,
        )

    # Remove issue depending
    for depend in sorted([int(i) for i in torm]):
        messages.append("Issue **un**marked as depending on: #%s" % depend)
        issue_depend = search_issues(session, repo, issueid=depend)
        if issue_depend is None:  # pragma: no cover
            # We cannot test this as it would mean we managed to put in an
            # invalid ticket as dependency earlier
            continue
        if issue_depend.id not in issue.depending_text:  # pragma: no cover
            # we should never be in this case but better safe than sorry...
            continue

        remove_issue_dependency(
            session,
            issue=issue,
            issue_blocked=issue_depend,
            user=username,
            ticketfolder=ticketfolder,
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

    toadd = set(blocks) - set(issue.blocking_text)
    torm = set(issue.blocking_text) - set(blocks)
    messages = []

    # Add issue blocked
    for block in sorted([int(i) for i in toadd]):
        messages.append("Issue marked as blocking: #%s" % block)
        issue_block = search_issues(session, repo, issueid=block)
        if issue_block is None:
            continue
        if issue_block.id in issue.blocking_text:  # pragma: no cover
            # we should never be in this case but better safe than sorry...
            continue

        add_issue_dependency(
            session,
            issue=issue,
            issue_blocked=issue_block,
            user=username,
            ticketfolder=ticketfolder,
        )
        session.commit()

    # Remove issue blocked
    for block in sorted([int(i) for i in torm]):
        messages.append("Issue **un**marked as blocking: #%s" % block)
        issue_block = search_issues(session, repo, issueid=block)
        if issue_block is None:  # pragma: no cover
            # We cannot test this as it would mean we managed to put in an
            # invalid ticket as dependency earlier
            continue

        if issue_block.id not in issue.blocking_text:  # pragma: no cover
            # we should never be in this case but better safe than sorry...
            continue

        remove_issue_dependency(
            session,
            issue=issue_block,
            issue_blocked=issue,
            user=username,
            ticketfolder=ticketfolder,
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


def search_groups(session, pattern=None, group_name=None, group_type=None,
                  display_name=None):
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
            sqlalchemy.or_(
                model.PagureGroup.group_name.ilike(pattern),
                model.PagureGroup.display_name.ilike(pattern)
            )
        )

    if group_name:
        query = query.filter(
            model.PagureGroup.group_name == group_name
        )

    if display_name:
        query = query.filter(
            model.PagureGroup.display_name == display_name
        )

    if group_type:
        query = query.filter(
            model.PagureGroup.group_type == group_type
        )

    if group_name:
        return query.first()
    else:
        return query.all()


def add_user_to_group(session, username, group, user, is_admin,
                      from_external=False):
    ''' Add the specified user to the given group.

    from_external indicates whether this is a remotely synced group.
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

    if not from_external and \
            group.group_name not in user.groups and not is_admin\
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
                         force=False, from_external=False):
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

    if not from_external and \
            group_obj.group_name not in user.groups and not is_admin:
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

    display = search_groups(session, display_name=display_name)
    if display:
        raise pagure.exceptions.PagureException(
            'There is already a group with display name `%s` created.' %
            display_name)

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


def get_acls(session, restrict=None):
    """ Returns all the possible ACLs a token can have according to the
    database.
    """
    query = session.query(
        model.ACL
    ).order_by(
        model.ACL.name
    )
    if restrict:
        if isinstance(restrict, list):
            query = query.filter(
                model.ACL.name.in_(restrict)
            )
        else:
            query = query.filter(
                model.ACL.name == restrict
            )

    return query.all()


def add_token_to_user(session, project, acls, username, description=None):
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
        project_id=project.id if project else None,
        description=description,
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


def _convert_markdown(md_processor, text):
    """ Small function converting the text to html using the given markdown
    processor.

    This was done in order to make testing it easier.
    """
    return md_processor.convert(text)


def text2markdown(text, extended=True, readme=False):
    """ Simple text to html converter using the markdown library.
    """
    extensions = [
        'markdown.extensions.def_list',
        'markdown.extensions.fenced_code',
        'markdown.extensions.tables',
        'markdown.extensions.smart_strong',
        # All of the above are the .extra extensions
        # w/o the "attribute lists" one
        'markdown.extensions.admonition',
        'markdown.extensions.codehilite',
        'markdown.extensions.sane_lists',
    ]
    # Some extensions are disabled for READMEs and enabled otherwise
    if readme:
        extensions.extend([
            'markdown.extensions.abbr',
            'markdown.extensions.footnotes',
            'markdown.extensions.toc',
        ])
    else:
        extensions.append(
            'markdown.extensions.nl2br',
        )
    if extended:
        # Install our markdown modifications
        extensions.append('pagure.pfmarkdown')

    md_processor = markdown.Markdown(
        extensions=extensions,
        extension_configs={
            'markdown.extensions.codehilite': {
                'guess_lang': False,
            }
        }
    )

    if text:
        try:
            text = _convert_markdown(md_processor, text)
        except Exception:
            _log.debug(
                'A markdown error occured while processing: ``%s``',
                str(text))
        return clean_input(text)

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

    bleach_v = bleach.__version__.split('.')
    for idx, val in enumerate(bleach_v):
        try:
            val = int(val)
        except ValueError:  # pragma: no cover
            pass
        bleach_v[idx] = val

    attrs = bleach.ALLOWED_ATTRIBUTES.copy()
    attrs['table'] = ['class']
    attrs['span'] = ['class', 'id']
    attrs['div'] = ['class']
    attrs['td'] = ['align']
    attrs['th'] = ['align']
    if not ignore or 'img' not in ignore:
        # newer bleach need three args for attribute callable
        if tuple(bleach_v) >= (2, 0, 0):  # pragma: no cover
            attrs['img'] = lambda tag, name, val: filter_img_src(name, val)
        else:
            attrs['img'] = filter_img_src

    tags = bleach.ALLOWED_TAGS + [
        'p', 'br', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'table', 'td', 'tr', 'th', 'thead', 'tbody',
        'col', 'pre', 'img', 'hr', 'dl', 'dt', 'dd', 'span',
        'kbd', 'var', 'del', 'cite',
    ]
    if ignore:
        for tag in ignore:
            if tag in tags:
                tags.remove(tag)

    kwargs = {
        'tags': tags,
        'attributes': attrs
    }

    # newer bleach allow to customize the protocol supported
    if tuple(bleach_v) >= (1, 5, 0):  # pragma: no cover
        protocols = bleach.ALLOWED_PROTOCOLS + ['irc', 'ircs']
        kwargs['protocols'] = protocols

    return bleach.clean(text, **kwargs)


def could_be_text(text):
    """ Returns whether we think this chain of character could be text or not
    """
    try:
        text.decode('utf-8')
        return True
    except (UnicodeDecodeError, UnicodeEncodeError):
        return False


def get_pull_request_of_user(
        session, username, status=None, offset=None, limit=None):
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
            model.ProjectUser.project_id == model.Project.id,
            sqlalchemy.or_(
                model.ProjectUser.access == 'admin',
                model.ProjectUser.access == 'commit',
            )
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
            sqlalchemy.or_(
                model.ProjectGroup.access == 'admin',
                model.ProjectGroup.access == 'commit',
            )
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
            sqlalchemy.or_(
                model.ProjectGroup.access == 'admin',
                model.ProjectGroup.access == 'commit',
            )
        )
    )
    sub_q5 = session.query(
        model.Project.id
    ).filter(
        sqlalchemy.and_(
            model.Project.id == model.PullRequest.project_id,
            model.PullRequest.user_id == model.User.id,
            model.User.user == username
        )
    )

    projects = projects.union(sub_q2).union(sub_q3).union(sub_q4).union(sub_q5)

    query = session.query(
        model.PullRequest
    ).filter(
        model.PullRequest.project_id.in_(projects.subquery())
    ).order_by(
        model.PullRequest.date_created.desc()
    )

    if status:
        query = query.filter(
            model.PullRequest.status == status
        )

    if offset:
        query = query.offset(offset)
    if limit:
        query = query.limit(limit)

    return query.all()


def update_watch_status(session, project, user, watch):
    ''' Update the user status for watching a project.

    The watch status can be:
        -1: reset the watch status to default
         0: unwatch, don't notify the user of anything
         1: watch issues and PRs
         2: watch commits
         3: watch issues, PRs and commits

    '''
    if watch not in ['-1', '0', '1', '2', '3']:
        raise pagure.exceptions.PagureException(
            'The watch value of "%s" is invalid' % watch)

    user_obj = get_user(session, user)

    watcher = session.query(
        model.Watcher
    ).filter(
        sqlalchemy.and_(
            model.Watcher.project_id == project.id,
            model.Watcher.user_id == user_obj.id,
        )
    ).first()

    if watch == '-1':
        if not watcher:
            return 'Watch status is already reset'

        session.delete(watcher)
        session.flush()
        return 'Watch status reset'

    should_watch_issues = False
    should_watch_commits = False
    if watch == '1':
        should_watch_issues = True
    elif watch == '2':
        should_watch_commits = True
    elif watch == '3':
        should_watch_issues = True
        should_watch_commits = True

    if not watcher:
        watcher = model.Watcher(
            project_id=project.id,
            user_id=user_obj.id,
            watch_issues=should_watch_issues,
            watch_commits=should_watch_commits
        )
    else:
        watcher.watch_issues = should_watch_issues
        watcher.watch_commits = should_watch_commits

    session.add(watcher)
    session.flush()

    if should_watch_issues and should_watch_commits:
        return 'You are now watching issues, PRs, and commits on this project'
    elif should_watch_issues:
        return 'You are now watching issues and PRs on this project'
    elif should_watch_commits:
        return 'You are now watching commits on this project'
    else:
        return 'You are no longer watching this project'


def get_watch_level_on_repo(session, user, repo, repouser=None,
                            namespace=None):
    ''' Get a list representing the watch level of the user on the project.
    '''
    # If a user wasn't passed in, we can't determine their watch level
    if user is None:
        return []
    elif isinstance(user, six.string_types):
        user_obj = search_user(session, username=user)
    else:
        user_obj = search_user(session, username=user.username)
    # If we can't find the user in the database, we can't determine their watch
    # level
    if not user_obj:
        return []

    # If the user passed in a Project for the repo parameter, then we don't
    # need to query for it
    if isinstance(repo, model.Project):
        project = repo
    # If the user passed in a string, then assume it is a project name
    elif isinstance(repo, six.string_types):
        project = pagure.get_authorized_project(
            session, repo, user=repouser, namespace=namespace)
    else:
        raise RuntimeError('The passed in repo is an invalid type of "{0}"'
                           .format(type(repo).__name__))

    # If the project is not found, we can't determine the involvement of the
    # user in the project
    if not project:
        return []

    query = session.query(
        model.Watcher
    ).filter(
        model.Watcher.user_id == user_obj.id
    ).filter(
        model.Watcher.project_id == project.id
    )

    watcher = query.first()
    # If there is a watcher issue, that means the user explicitly set a watch
    # level on the project
    if watcher:
        if watcher.watch_issues and watcher.watch_commits:
            return ['issues', 'commits']
        elif watcher.watch_issues:
            return ['issues']
        elif watcher.watch_commits:
            return ['commits']
        else:
            # If a watcher entry is set and both are set to False, that means
            # the user explicitly asked to not be notified
            return []

    # If the user is the project owner, by default they will be watching
    # issues and PRs
    if user_obj.username == project.user.username:
        return ['issues']
    # If the user is a contributor, by default they will be watching issues
    # and PRs
    for contributor in project.users:
        if user_obj.username == contributor.username:
            return ['issues']
    # If the user is in a project group, by default they will be watching
    # issues and PRs
    for group in project.groups:
        for guser in group.users:
            if user_obj.username == guser.username:
                return ['issues']
    # If no other condition is true, then they are not explicitly watching the
    # project or are not involved in the project to the point that comes with a
    # default watch level
    return []


def user_watch_list(session, user, exclude_groups=None):
    ''' Returns list of all the projects which the user is watching '''

    user_obj = search_user(session, username=user)
    if not user_obj:
        return []

    unwatched = session.query(
        model.Watcher
    ).filter(
        model.Watcher.user_id == user_obj.id
    ).filter(
        model.Watcher.watch_issues == False  # noqa: E712
    ).filter(
        model.Watcher.watch_commits == False  # noqa: E712
    )

    unwatched_list = []
    if unwatched:
        unwatched_list = [unwatch.project for unwatch in unwatched.all()]

    watched = session.query(
        model.Watcher
    ).filter(
        model.Watcher.user_id == user_obj.id
    ).filter(
        model.Watcher.watch_issues == True  # noqa: E712
    ).filter(
        model.Watcher.watch_commits == True  # noqa: E712
    )

    watched_list = []
    if watched:
        watched_list = [watch.project for watch in watched.all()]

    user_projects = search_projects(
        session, username=user_obj.user, exclude_groups=exclude_groups)
    watch = set(watched_list + user_projects)

    for project in user_projects:
        if project in unwatched_list:
            watch.remove(project)

    return sorted(list(watch), key=lambda proj: proj.name)


def set_watch_obj(session, user, obj, watch_status):
    ''' Set the watch status of the user on the specified object.

    Objects can be either an issue or a pull-request
    '''

    user_obj = get_user(session, user)

    if obj.isa == "issue":
        query = session.query(
            model.IssueWatcher
        ).filter(
            model.IssueWatcher.user_id == user_obj.id
        ).filter(
            model.IssueWatcher.issue_uid == obj.uid
        )
    elif obj.isa == "pull-request":
        query = session.query(
            model.PullRequestWatcher
        ).filter(
            model.PullRequestWatcher.user_id == user_obj.id
        ).filter(
            model.PullRequestWatcher.pull_request_uid == obj.uid
        )
    else:
        raise pagure.exceptions.InvalidObjectException(
            'Unsupported object found: "%s"' % obj
        )

    dbobj = query.first()

    if not dbobj:
        if obj.isa == "issue":
            dbobj = model.IssueWatcher(
                user_id=user_obj.id,
                issue_uid=obj.uid,
                watch=watch_status,
            )
        elif obj.isa == "pull-request":
            dbobj = model.PullRequestWatcher(
                user_id=user_obj.id,
                pull_request_uid=obj.uid,
                watch=watch_status,
            )
    else:
        dbobj.watch = watch_status

    session.add(dbobj)

    output = 'You are no longer watching this %s' % obj.isa
    if watch_status:
        output = 'You are now watching this %s' % obj.isa
    return output


def get_watch_list(session, obj):
    """ Return a list of all the users that are watching the "object"
    """
    private = False
    if obj.isa == "issue":
        private = obj.private
        obj_watchers_query = session.query(
            model.IssueWatcher
        ).filter(
            model.IssueWatcher.issue_uid == obj.uid
        )
    elif obj.isa == "pull-request":
        obj_watchers_query = session.query(
            model.PullRequestWatcher
        ).filter(
            model.PullRequestWatcher.pull_request_uid == obj.uid
        )
    else:
        raise pagure.exceptions.InvalidObjectException(
            'Unsupported object found: "%s"' % obj
        )

    project_watchers_query = session.query(
        model.Watcher
    ).filter(
        model.Watcher.project_id == obj.project.id
    )

    users = set()

    # Add the person who opened the object
    users.add(obj.user.username)

    # Add all the people who commented on that object
    for comment in obj.comments:
        users.add(comment.user.username)

    # Add the user of the project
    users.add(obj.project.user.username)

    # Add the regular contributors
    for contributor in obj.project.users:
        users.add(contributor.username)

    # Add people in groups with commit access
    for group in obj.project.groups:
        for member in group.users:
            users.add(member.username)

    # If the issue isn't private:
    if not private:
        # Add all the people watching the repo, remove those who opted-out
        for watcher in project_watchers_query.all():
            if watcher.watch_issues:
                users.add(watcher.user.username)
            else:
                if watcher.user.username in users:
                    users.remove(watcher.user.username)

        # Add all the people watching this object, remove those who opted-out
        for watcher in obj_watchers_query.all():
            if watcher.watch:
                users.add(watcher.user.username)
            else:
                if watcher.user.username in users:
                    users.remove(watcher.user.username)

    return users


def save_report(session, repo, name, url, username):
    """ Save the report of issues based on the given URL of the project.
    """
    url_obj = urlparse.urlparse(url)
    url = url_obj.geturl().replace(url_obj.query, '')
    query = {}
    for k, v in urlparse.parse_qsl(url_obj.query):
        if k in query:
            if isinstance(query[k], list):
                query[k].append(v)
            else:
                query[k] = [query[k], v]
        else:
            query[k] = v
    reports = repo.reports
    reports[name] = query
    repo.reports = reports
    session.add(repo)


def set_custom_key_fields(
        session, project, fields, types, data, notify=None):
    """ Set or update the custom key fields of a project with the values
    provided.  "data" is currently only used for lists
    """

    current_keys = {}
    for key in project.issue_keys:
        current_keys[key.name] = key

    for idx, key in enumerate(fields):
        if types[idx] != "list":
            # Only Lists use data, strip it otherwise
            data[idx] = None
        else:
            if data[idx]:
                data[idx] = [
                    item.strip()
                    for item in data[idx].split(',')
                ]

        if notify and notify[idx] == "on":
            notify_flag = True
        else:
            notify_flag = False

        if key in current_keys:
            issuekey = current_keys[key]
            issuekey.key_type = types[idx]
            issuekey.data = data[idx]
            issuekey.key_notify = notify_flag
        else:
            issuekey = model.IssueKeys(
                project_id=project.id,
                name=key,
                key_type=types[idx],
                data=data[idx],
                key_notify=notify_flag
            )
        session.add(issuekey)

    # Delete keys
    for key in current_keys:
        if key not in fields:
            session.delete(current_keys[key])

    return 'List of custom fields updated'


def set_custom_key_value(session, issue, key, value):
    """ Set or update the value of the specified custom key.
    """

    query = session.query(
        model.IssueValues
    ).filter(
        model.IssueValues.key_id == key.id
    ).filter(
        model.IssueValues.issue_uid == issue.uid
    )

    current_field = query.first()
    updated = False
    delete = False
    old_value = None
    if current_field:
        old_value = current_field.value
        if current_field.key.key_type == 'boolean':
            value = value or False
        if value is None or value == '':
            session.delete(current_field)
            updated = True
            delete = True
        elif current_field.value != value:
            current_field.value = value
            updated = True
    else:
        if value is None or value == '':
            delete = True
        else:
            current_field = model.IssueValues(
                issue_uid=issue.uid,
                key_id=key.id,
                value=value,
            )
            updated = True

    if not delete:
        session.add(current_field)

    if REDIS and updated:
        if issue.private:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps({
                'issue': 'private',
                'custom_fields': [key.name],
            }))
        else:
            REDIS.publish('pagure.%s' % issue.uid, json.dumps({
                'custom_fields': [key.name],
                'issue': issue.to_json(public=True, with_comments=False),
            }))

    if updated and value:
        output = 'Custom field %s adjusted to %s' % (key.name, value)
        if old_value:
            output += ' (was: %s)' % old_value
        return output
    elif updated and old_value:
        return 'Custom field %s reset (from %s)' % (key.name, old_value)


def get_yearly_stats_user(session, user, date):
    """ Return the activity of the specified user in the year preceding the
    specified date.
    """
    start_date = datetime.datetime(date.year - 1, date.month, date.day)

    query = session.query(
        model.PagureLog.date, func.count(model.PagureLog.id)
    ).filter(
        model.PagureLog.date_created.between(start_date, date)
    ).filter(
        model.PagureLog.user_id == user.id
    ).group_by(
        model.PagureLog.date
    ).order_by(
        model.PagureLog.date
    )

    return query.all()


def get_user_activity_day(session, user, date):
    """ Return the activity of the specified user on the specified date.
    """
    query = session.query(
        model.PagureLog
    ).filter(
        model.PagureLog.date == date
    ).filter(
        model.PagureLog.user_id == user.id
    ).order_by(
        model.PagureLog.id.asc()
    )

    return query.all()


def log_action(session, action, obj, user_obj):
    ''' Log an user action on a project/issue/PR. '''
    project_id = None
    if obj.isa in ['issue', 'pull-request']:
        project_id = obj.project_id
    elif obj.isa == 'project':
        project_id = obj.id
    else:
        raise pagure.exceptions.InvalidObjectException(
            'Unsupported object found: "%s"' % obj
        )

    log = model.PagureLog(
        user_id=user_obj.id,
        project_id=project_id,
        log_type=action,
        ref_id=obj.id
    )
    if obj.isa == 'issue':
        setattr(log, 'issue_uid', obj.uid)
    elif obj.isa == 'pull-request':
        setattr(log, 'pull_request_uid', obj.uid)

    session.add(log)
    session.commit()


def email_logs_count(session, email):
    """ Returns the number of logs associated with a given email."""
    query = session.query(
        model.PagureLog
    ).filter(
        model.PagureLog.user_email == email
    )

    return query.count()


def update_log_email_user(session, email, user):
    """ Update the logs with the provided email to point to the specified
    user.
    """
    session.query(
        model.PagureLog
    ).filter(
        model.PagureLog.user_email == email
    ).update(
        {model.PagureLog.user_id: user.id},
        synchronize_session=False
    )


def get_custom_key(session, project, keyname):
    ''' Returns custom key object given it's name and the project '''

    query = session.query(
        model.IssueKeys
    ).filter(
        model.IssueKeys.project_id == project.id
    ).filter(
        model.IssueKeys.name == keyname
    )

    return query.first()


def get_active_milestones(session, project):
    ''' Returns the list of all the active milestones for a given project.
    '''

    query = session.query(
        model.Issue.milestone
    ).filter(
        model.Issue.project_id == project.id
    ).filter(
        model.Issue.status == 'Open'
    ).filter(
        model.Issue.milestone.isnot(None)
    )

    return sorted([item[0] for item in query.distinct()])


def add_metadata_update_notif(session, obj, messages, user, gitfolder):
    ''' Add a notification to the specified issue with the given messages
    which should reflect changes made to the meta-data of the issue.
    '''
    if not messages:
        return

    if not isinstance(messages, (list, set)):
        messages = [messages]

    user_id = None
    if user:
        user_obj = get_user(session, user)
        user_id = user_obj.id

    if obj.isa == 'issue':
        obj_comment = model.IssueComment(
            issue_uid=obj.uid,
            comment='**Metadata Update from @%s**:\n- %s' % (
                user, '\n- '.join(sorted(messages))),
            user_id=user_id,
            notification=True,
        )
    elif obj.isa == 'pull-request':
        obj_comment = model.PullRequestComment(
            pull_request_uid=obj.uid,
            comment='**Metadata Update from @%s**:\n- %s' % (
                user, '\n- '.join(sorted(messages))),
            user_id=user_id,
            notification=True,
        )
    obj.last_updated = datetime.datetime.utcnow()
    session.add(obj)
    session.add(obj_comment)
    # Make sure we won't have SQLAlchemy error before we continue
    session.commit()

    if gitfolder:
        pagure.lib.git.update_git(
            obj, repo=obj.project, repofolder=gitfolder)


def tokenize_search_string(pattern):
    """This function tokenizes search patterns into key:value and rest.

    It will also correctly parse key values between quotes.
    """
    if pattern is None:
        return {}, None

    def finalize_token(token, custom_search):
        if ':' in token:
            # This was a "key:value" parameter
            key, value = token.split(':', 1)
            custom_search[key] = value
            return ''
        else:
            # This was a token without colon, thus a search pattern
            return '%s ' % token

    custom_search = {}
    # Remaining is the remaining real search_pattern (aka, non-key:values)
    remaining = ''
    # Token is the current "search token" we are processing
    token = ''
    in_quotes = False
    for char in pattern:
        if char == ' ' and not in_quotes:
            remaining += finalize_token(token, custom_search)
            token = ''
        elif char == '"':
            in_quotes = not in_quotes
        else:
            token += char

    # Parse the final token
    remaining += finalize_token(token, custom_search)

    return custom_search, remaining.strip()


def get_access_levels(session):
    ''' Returns all the access levels a user/group can have for a project '''

    access_level_objs = session.query(model.AccessLevels).all()
    return [access_level.access for access_level in access_level_objs]


def get_obj_access(session, project_obj, obj):
    ''' Returns the level of access the user/group has on the project.

    :arg session: the session to use to connect to the database.
    :arg project_obj: SQLAlchemy object of Project class
    :arg obj: SQLAlchemy object of either User or PagureGroup class
    '''

    if isinstance(obj, model.User):
        query = session.query(
            model.ProjectUser
        ).filter(
            model.ProjectUser.project_id == project_obj.id
        ).filter(
            model.ProjectUser.user_id == obj.id
        )
    else:
        query = session.query(
            model.ProjectGroup
        ).filter(
            model.ProjectGroup.project_id == project_obj.id
        ).filter(
            model.ProjectGroup.group_id == obj.id
        )

    return query.first()


def search_token(
        session, acls, user=None, token=None, active=False, expired=False):
    ''' Searches the API tokens corresponding to the criterias specified.

    :arg session: the session to use to connect to the database.
    :arg acls: List of the ACL associated with these API tokens
    :arg user: restrict the API tokens to this given user
    :arg token: restrict the API tokens to this specified token (if it
        exists)
    '''
    query = session.query(
        model.Token
    ).filter(
        model.Token.id == model.TokenAcl.token_id
    ).filter(
        model.TokenAcl.acl_id == model.ACL.id
    )

    if acls:
        if isinstance(acls, list):
            query = query.filter(
                model.ACL.name.in_(acls)
            )
        else:
            query = query.filter(
                model.ACL.name == acls
            )

    if user:
        query = query.filter(
            model.Token.user_id == model.User.id
        ).filter(
            model.User.user == user
        )

    if active:
        query = query.filter(
            model.Token.expiration > datetime.datetime.utcnow()
        )
    elif expired:
        query = query.filter(
            model.Token.expiration <= datetime.datetime.utcnow()
        )

    if token:
        query = query.filter(
            model.Token.id == token
        )
        return query.first()
    else:
        return query.all()


def set_project_owner(session, project, user):
    ''' Set the ownership of a project
    :arg session: the session to use to connect to the database.
    :arg project: a Project object representing the project's ownership to
    change.
    :arg user: a User object representing the new owner of the project.
    :return: None
    '''
    for contributor in project.users:
        if user.id == contributor.id:
            project.users.remove(contributor)
            break
    project.user = user
    session.add(project)


def get_pagination_metadata(flask_request, page, per_page, total):
    """
    Returns pagination metadata for an API. The code was inspired by
    Flask-SQLAlchemy.
    :param flask_request: flask.request object
    :param page: int of the current page
    :param per_page: int of results per page
    :param total: int of total results
    :return: dictionary of pagination metadata
    """
    pages = int(ceil(total / float(per_page)))
    request_args_wo_page = dict(copy.deepcopy(flask_request.args))
    # Remove pagination related args because those are handled elsewhere
    # Also, remove any args that url_for accepts in case the user entered
    # those in
    for key in ['page', 'per_page', 'endpoint']:
        if key in request_args_wo_page:
            request_args_wo_page.pop(key)
    for key in flask_request.args:
        if key.startswith('_'):
            request_args_wo_page.pop(key)

    next_page = None
    if page < pages:
        next_page = url_for(
            flask_request.endpoint, page=page + 1, per_page=per_page,
            _external=True, **request_args_wo_page)

    prev_page = None
    if page > 1:
        prev_page = url_for(
            flask_request.endpoint, page=page - 1, per_page=per_page,
            _external=True, **request_args_wo_page)

    first_page = url_for(
        flask_request.endpoint, page=1, per_page=per_page, _external=True,
        **request_args_wo_page)

    last_page = url_for(
        flask_request.endpoint, page=pages, per_page=per_page,
        _external=True, **request_args_wo_page)

    return {
        'page': page,
        'pages': pages,
        'per_page': per_page,
        'prev': prev_page,
        'next': next_page,
        'first': first_page,
        'last': last_page
    }


def update_star_project(session, repo, star, user):
    ''' Unset or set the star status depending on the star value.

    :arg session: the session to use to connect to the database.
    :arg repo: a model.Project object representing the project to star/unstar
    :arg star: '1' for starring and '0' for unstarring
    :arg user: string representing the user
    :return: None or string containing 'You starred this project' or
            'You unstarred this project'
    '''

    if not all([repo, user, star]):
        return
    user_obj = get_user(session, user)
    msg = None
    if star == '1':
        msg = _star_project(
            session,
            repo=repo,
            user=user_obj,
        )
    elif star == '0':
        msg = _unstar_project(
            session,
            repo=repo,
            user=user_obj,
        )
    return msg


def _star_project(session, repo, user):
    ''' Star a project

    :arg session: Session object to connect to db with
    :arg repo: model.Project object representing the repo to star
    :arg user: model.User object who is starring this repo
    :return: None or string containing 'You starred this project'
    '''

    if not all([repo, user]):
        return
    stargazer_obj = model.Star(
        project_id=repo.id,
        user_id=user.id,
    )
    session.add(stargazer_obj)
    return 'You starred this project'


def _unstar_project(session, repo, user):
    ''' Unstar a project
    :arg session: Session object to connect to db with
    :arg repo: model.Project object representing the repo to unstar
    :arg user: model.User object who is unstarring this repo
    :return: None or string containing 'You unstarred this project'
            or 'You never starred the project'
    '''

    if not all([repo, user]):
        return
    # First find the stargazer_obj object
    stargazer_obj = _get_stargazer_obj(session, repo, user)
    if isinstance(stargazer_obj, model.Star):
        session.delete(stargazer_obj)
        msg = 'You unstarred this project'
    else:
        msg = 'You never starred the project'
    return msg


def _get_stargazer_obj(session, repo, user):
    ''' Query the db to find stargazer object with given repo and user
    :arg session: Session object to connect to db with
    :arg repo: model.Project object
    :arg user: model.User object
    :return: None or model.Star object
    '''

    if not all([repo, user]):
        return
    stargazer_obj = session.query(
        model.Star,
    ).filter(
        model.Star.project_id == repo.id,
    ).filter(
        model.Star.user_id == user.id,
    )

    return stargazer_obj.first()


def has_starred(session, repo, user):
    ''' Check if a given user has starred a particular project

    :arg session: The session object to query the db with
    :arg repo: model.Project object for which the star is checked
    :arg user: The username of the user in question
    :return: True if user has starred the project, False otherwise
    '''

    if not all([repo, user]):
        return
    user_obj = search_user(session, username=user)
    stargazer_obj = _get_stargazer_obj(session, repo, user_obj)
    if isinstance(stargazer_obj, model.Star):
        return True
    return False


def update_read_only_mode(session, repo, read_only=True):
    ''' Remove the read only mode from the project

    :arg session: The session object to query the db with
    :arg repo: model.Project object to mark/unmark read only
    :arg read_only: True if project is to be made read only,
        False otherwise
    '''

    if (
            not repo
            or not isinstance(repo, model.Project)
            or read_only not in [True, False]):
        return
    if repo.read_only != read_only:
        repo.read_only = read_only
        session.add(repo)


def issues_history_stats(session, project):
    ''' Returns the number of opened issues on the specified project over
    the last 365 days

    :arg session: The session object to query the db with
    :arg repo: model.Project object to get the issues stats about

    '''

    # Some ticket got imported as closed but without a closed_at date, so
    # let's ignore them all
    to_ignore = session.query(
        model.Issue
    ).filter(
        model.Issue.project_id == project.id
    ).filter(
        model.Issue.closed_at == None,  # noqa
    ).filter(
        model.Issue.status == 'Closed'
    ).count()

    # For each week from tomorrow, get the number of open tickets
    tomorrow = datetime.datetime.utcnow() + datetime.timedelta(days=1)
    output = {}
    for week in range(53):
        start = tomorrow - datetime.timedelta(days=(week * 7))
        closed_ticket = session.query(
            model.Issue
        ).filter(
            model.Issue.project_id == project.id
        ).filter(
            model.Issue.closed_at >= start
        ).filter(
            model.Issue.date_created <= start
        )
        open_ticket = session.query(
            model.Issue
        ).filter(
            model.Issue.project_id == project.id
        ).filter(
            model.Issue.status == 'Open'
        ).filter(
            model.Issue.date_created <= start
        )
        cnt = open_ticket.count() + closed_ticket.count() - to_ignore
        if cnt < 0:
            cnt = 0
        output[start.isoformat()] = cnt

    return output
