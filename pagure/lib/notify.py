# -*- coding: utf-8 -*-

"""
 (c) 2014-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

pagure notifications.
"""
from __future__ import print_function

# pylint: disable=too-many-branches
# pylint: disable=too-many-arguments


import datetime
import hashlib
import json
import logging
import urlparse
import re
import smtplib
import time
import warnings

import flask
import pagure

from email.header import Header
from email.mime.text import MIMEText


_log = logging.getLogger(__name__)


REPLY_MSG = 'To reply, visit the link below'
if pagure.APP.config['EVENTSOURCE_SOURCE']:
    REPLY_MSG += ' or just reply to this email'


def fedmsg_publish(*args, **kwargs):  # pragma: no cover
    ''' Try to publish a message on the fedmsg bus. '''
    # We catch Exception if we want :-p
    # pylint: disable=broad-except
    # Ignore message about fedmsg import
    # pylint: disable=import-error
    kwargs['modname'] = 'pagure'
    try:
        import fedmsg
        fedmsg.publish(*args, **kwargs)
    except Exception as err:
        warnings.warn(str(err))


def log(project, topic, msg, redis=None):
    ''' This is the place where we send notifications to user about actions
    occuring in pagure.
    '''

    # Send fedmsg notification (if fedmsg is there and set-up)
    if not project or (project.settings.get('fedmsg_notifications', True)
                       and not project.private):
        fedmsg_publish(topic, msg)

    if redis and project and not project.private:
        redis.publish(
            'pagure.hook',
            json.dumps({
                'project': project.fullname,
                'topic': topic,
                'msg': msg,
            }))


def _add_mentioned_users(emails, comment):
    ''' Check the comment to see if an user is mentioned in it and if
    so add this user to the list of people to notify.
    '''
    mentio_re = r'@(\w+)'
    for username in re.findall(mentio_re, comment):
        user = pagure.lib.search_user(pagure.SESSION, username=username)
        if user:
            emails.add(user.default_email)
    return emails


def _clean_emails(emails, user):
    ''' Remove the email of the user doing the action if it is in the list.

    This avoids receiving emails about action you do.
    '''
    # Remove the user doing the action from the list of person to email
    # unless they actively asked for it
    if user and user.emails \
            and not user.settings.get('cc_me_to_my_actions', False):
        for email in user.emails:
            if email.email in emails:
                emails.remove(email.email)
    return emails


def _get_emails_for_obj(obj):
    ''' Return the list of emails to send notification to when notifying
    about the specified issue or pull-request.
    '''
    emails = set()
    # Add project creator/owner
    if obj.project.user.default_email:
        emails.add(obj.project.user.default_email)

    # Add project maintainers
    for user in obj.project.users:
        if user.default_email:
            emails.add(user.default_email)

    # Add people in groups with any access to the project:
    for group in obj.project.groups:
        if group.creator.default_email:
            emails.add(group.creator.default_email)
        for user in group.users:
            if user.default_email:
                emails.add(user.default_email)

    # Add people that commented on the issue/PR
    for comment in obj.comments:
        if comment.user.default_email:
            emails.add(comment.user.default_email)

    # Add the person that opened the issue/PR
    if obj.user.default_email:
        emails.add(obj.user.default_email)

    # Add the person assigned to the issue/PR
    if obj.assignee and obj.assignee.default_email:
        emails.add(obj.assignee.default_email)

    # Add the person watching this project, if the issue is public
    if obj.isa == 'issue' and not obj.private:
        for watcher in obj.project.watchers:
            emails.add(watcher.user.default_email)
    elif obj.isa == 'pull-request':
        for watcher in obj.project.watchers:
            emails.add(watcher.user.default_email)

    # Add public notifications to lists/users set project-wide
    if obj.isa == 'issue' and not obj.private:
        for notifs in obj.project.notifications.get('issues', []):
            emails.add(notifs)
    elif obj.isa == 'pull-request':
        for notifs in obj.project.notifications.get('requests', []):
            emails.add(notifs)

    # Remove the person list in unwatch
    for unwatcher in obj.project.unwatchers:
        if unwatcher.user.default_email in emails:
            emails.remove(unwatcher.user.default_email)

    # Add/Remove people who explicitly asked to be added/removed
    for watcher in obj.watchers:
        if not watcher.watch and watcher.user.default_email in emails:
            emails.remove(watcher.user.default_email)
        elif watcher.watch:
            emails.add(watcher.user.default_email)

    # Drop the email used by pagure when sending
    emails = _clean_emails(
        emails, pagure.APP.config.get(pagure.APP.config.get(
            'FROM_EMAIL', 'pagure@fedoraproject.org'))
    )

    return emails


def _build_url(*args):
    ''' Build a URL from a given list of arguments. '''
    items = []
    for idx, arg in enumerate(args):
        arg = str(arg)
        if arg.startswith('/'):
            arg = arg[1:]
        if arg.endswith('/') and not idx + 1 == len(args):
            arg = arg[:-1]
        items.append(arg)

    return '/'.join(items)


def _fullname_to_url(fullname):
    ''' For forked projects, fullname is 'forks/user/...' but URL is
    'fork/user/...'. This is why we can't have nice things.
    '''
    if fullname.startswith('forks/'):
        fullname = fullname.replace('forks', 'fork', 1)
    return fullname


def send_email(text, subject, to_mail,
               mail_id=None, in_reply_to=None,
               project_name=None, user_from=None):  # pragma: no cover
    ''' Send an email with the specified information.

    :arg text: the content of the email to send
    :arg subject: the subject of the email
    :arg to_mail: a string representing a list of recipient separated by a
        coma
    :kwarg mail_id: if defined, the header `mail-id` is set with this value
    :kwarg in_reply_to: if defined, the header `In-Reply-To` is set with
        this value
    :kwarg project_name: if defined, the name of the project

    '''
    if not to_mail:
        return

    from_email = pagure.APP.config.get(
        'FROM_EMAIL', 'pagure@fedoraproject.org')
    if user_from:
        header = Header(user_from, 'utf-8')
        from_email = '%s <%s>' % (header, from_email)

    if project_name is not None:
        subject_tag = project_name
    else:
        subject_tag = 'Pagure'

    smtp = None
    for mailto in to_mail.split(','):
        msg = MIMEText(text.encode('utf-8'), 'plain', 'utf-8')
        msg['Subject'] = header = Header(
            '[%s] %s' % (subject_tag, subject), 'utf-8')
        msg['From'] = from_email

        if mail_id:
            msg['mail-id'] = mail_id
            msg['Message-Id'] = '<%s>' % mail_id

        if in_reply_to:
            msg['In-Reply-To'] = '<%s>' % in_reply_to

        msg['X-pagure'] = pagure.APP.config['APP_URL']
        if project_name is not None:
            msg['X-pagure-project'] = project_name

        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        if isinstance(mailto, unicode):
            mailto = mailto.encode('utf-8')
        msg['To'] = mailto
        salt = pagure.APP.config.get('SALT_EMAIL')
        if isinstance(mail_id, unicode):
            mail_id = mail_id.encode('utf-8')
        mhash = hashlib.sha512('<%s>%s%s' % (mail_id, salt, mailto))
        msg['Reply-To'] = 'reply+%s@%s' % (
            mhash.hexdigest(),
            pagure.APP.config['DOMAIN_EMAIL_NOTIFICATIONS'])
        msg['Mail-Followup-To'] = msg['Reply-To']
        if not pagure.APP.config.get('EMAIL_SEND', True):
            print('******EMAIL******')
            print('From: %s' % from_email)
            print('To: %s' % to_mail)
            print('Subject: %s' % subject)
            print('in_reply_to: %s' % in_reply_to)
            print('mail_id: %s' % mail_id)
            print('Contents:')
            print(text.encode('utf-8'))
            print('*****************')
            print(msg.as_string())
            print('*****/EMAIL******')
            continue
        try:
            if smtp is None:
                if pagure.APP.config['SMTP_SSL']:
                    smtp = smtplib.SMTP_SSL(
                        pagure.APP.config['SMTP_SERVER'],
                        pagure.APP.config['SMTP_PORT'])
                else:
                    smtp = smtplib.SMTP(
                        pagure.APP.config['SMTP_SERVER'],
                        pagure.APP.config['SMTP_PORT'])
            if pagure.APP.config['SMTP_USERNAME'] \
                    and pagure.APP.config['SMTP_PASSWORD']:
                smtp.login(
                    pagure.APP.config['SMTP_USERNAME'],
                    pagure.APP.config['SMTP_PASSWORD']
                )

            smtp.sendmail(
                from_email,
                [mailto],
                msg.as_string())
        except smtplib.SMTPException as err:
            _log.exception(err)
    if smtp:
        smtp.quit()
    return msg


def notify_new_comment(comment, user=None):
    ''' Notify the people following an issue that a new comment was added
    to the issue.
    '''

    text = u"""
%s added a new comment to an issue you are following:
``
%s
``

%s
%s
""" % (comment.user.user,
       comment.comment,
       REPLY_MSG,
       _build_url(
           pagure.APP.config['APP_URL'],
           _fullname_to_url(comment.issue.project.fullname),
           'issue',
           comment.issue.id))
    mail_to = _get_emails_for_obj(comment.issue)
    if comment.user and comment.user.default_email:
        mail_to.add(comment.user.default_email)

    mail_to = _add_mentioned_users(mail_to, comment.comment)
    mail_to = _clean_emails(mail_to, user)

    send_email(
        text,
        'Issue #%s: %s' % (comment.issue.id, comment.issue.title),
        ','.join(mail_to),
        mail_id=comment.mail_id,
        in_reply_to=comment.issue.mail_id,
        project_name=comment.issue.project.fullname,
        user_from=comment.user.fullname or comment.user.user,
    )


def notify_new_issue(issue, user=None):
    ''' Notify the people following a project that a new issue was added
    to it.
    '''
    text = u"""
%s reported a new issue against the project: `%s` that you are following:
``
%s
``

%s
%s
""" % (issue.user.user,
       issue.project.name,
       issue.content,
       REPLY_MSG,
       _build_url(
           pagure.APP.config['APP_URL'],
           _fullname_to_url(issue.project.fullname),
           'issue',
           issue.id))
    mail_to = _get_emails_for_obj(issue)
    mail_to = _add_mentioned_users(mail_to, issue.content)
    mail_to = _clean_emails(mail_to, user)

    send_email(
        text,
        'Issue #%s: %s' % (issue.id, issue.title),
        ','.join(mail_to),
        mail_id=issue.mail_id,
        project_name=issue.project.fullname,
        user_from=issue.user.fullname or issue.user.user,
    )


def notify_assigned_issue(issue, new_assignee, user):
    ''' Notify the people following an issue that the assignee changed.
    '''
    action = 'reset'
    if new_assignee:
        action = 'assigned to `%s`' % new_assignee.user
    text = u"""
The issue: `%s` of project: `%s` has been %s by %s.

%s
""" % (issue.title,
       issue.project.name,
       action,
       user.username,
       _build_url(
           pagure.APP.config['APP_URL'],
           _fullname_to_url(issue.project.fullname),
           'issue',
           issue.id))
    mail_to = _get_emails_for_obj(issue)
    if new_assignee and new_assignee.default_email:
        mail_to.add(new_assignee.default_email)

    mail_to = _clean_emails(mail_to, user)

    uid = time.mktime(datetime.datetime.now().timetuple())
    send_email(
        text,
        'Issue #%s: %s' % (issue.id, issue.title),
        ','.join(mail_to),
        mail_id='%s/assigned/%s' % (issue.mail_id, uid),
        in_reply_to=issue.mail_id,
        project_name=issue.project.fullname,
        user_from=user.fullname or user.user,
    )


def notify_status_change_issue(issue, user):
    ''' Notify the people following a project that an issue changed status.
    '''
    status = issue.status
    if status.lower() != 'open' and issue.close_status:
        status = '%s as %s' % (status, issue.close_status)
    text = u"""
The status of the issue: `%s` of project: `%s` has been updated to: %s by %s.

%s
""" % (issue.title,
       issue.project.fullname,
       status,
       user.username,
       _build_url(
           pagure.APP.config['APP_URL'],
           _fullname_to_url(issue.project.fullname),
           'issue',
           issue.id))
    mail_to = _get_emails_for_obj(issue)

    uid = time.mktime(datetime.datetime.now().timetuple())
    send_email(
        text,
        'Issue #%s: %s' % (issue.id, issue.title),
        ','.join(mail_to),
        mail_id='%s/close/%s' % (issue.mail_id, uid),
        in_reply_to=issue.mail_id,
        project_name=issue.project.fullname,
        user_from=user.fullname or user.user,
    )


def notify_meta_change_issue(issue, user, msg):
    ''' Notify that a custom field changed
    '''
    text = u"""
`%s` updated issue.

%s

%s
""" % (user.username,
       msg,
       _build_url(
           pagure.APP.config['APP_URL'],
           _fullname_to_url(issue.project.fullname),
           'issue',
           issue.id))
    mail_to = _get_emails_for_obj(issue)
    uid = time.mktime(datetime.datetime.now().timetuple())
    send_email(
        text,
        'Issue #%s: %s' % (issue.id, issue.title),
        ','.join(mail_to),
        mail_id='%s/close/%s' % (issue.mail_id, uid),
        in_reply_to=issue.mail_id,
        project_name=issue.project.fullname,
        user_from=user.fullname or user.user,
    )


def notify_assigned_request(request, new_assignee, user):
    ''' Notify the people following a pull-request that the assignee changed.
    '''
    action = 'reset'
    if new_assignee:
        action = 'assigned to `%s`' % new_assignee.user
    text = u"""
The pull-request: `%s` of project: `%s` has been %s by %s.

%s
""" % (request.title,
       request.project.name,
       action,
       user.username,
       _build_url(
           pagure.APP.config['APP_URL'],
           _fullname_to_url(request.project.fullname),
           'pull-request',
           request.id))
    mail_to = _get_emails_for_obj(request)
    if new_assignee and new_assignee.default_email:
        mail_to.add(new_assignee.default_email)

    mail_to = _clean_emails(mail_to, user)

    uid = time.mktime(datetime.datetime.now().timetuple())
    send_email(
        text,
        'PR #%s: %s' % (request.id, request.title),
        ','.join(mail_to),
        mail_id='%s/assigned/%s' % (request.mail_id, uid),
        in_reply_to=request.mail_id,
        project_name=request.project.fullname,
        user_from=user.fullname or user.user,
    )


def notify_new_pull_request(request):
    ''' Notify the people following a project that a new pull-request was
    added to it.
    '''
    text = u"""
%s opened a new pull-request against the project: `%s` that you are following:
``
%s
``

%s
%s
""" % (request.user.user,
       request.project.name,
       request.title,
       REPLY_MSG,
       _build_url(
           pagure.APP.config['APP_URL'],
           _fullname_to_url(request.project.fullname),
           'pull-request',
           request.id))
    mail_to = _get_emails_for_obj(request)

    send_email(
        text,
        'PR #%s: %s' % (request.id, request.title),
        ','.join(mail_to),
        mail_id=request.mail_id,
        project_name=request.project.fullname,
        user_from=request.user.fullname or request.user.user,
    )


def notify_merge_pull_request(request, user):
    ''' Notify the people following a project that a pull-request was merged
    in it.
    '''
    text = u"""
%s merged a pull-request against the project: `%s` that you are following.

Merged pull-request:

``
%s
``

%s
""" % (user.username,
       request.project.name,
       request.title,
       _build_url(
           pagure.APP.config['APP_URL'],
           _fullname_to_url(request.project.fullname),
           'pull-request',
           request.id))
    mail_to = _get_emails_for_obj(request)

    uid = time.mktime(datetime.datetime.now().timetuple())
    send_email(
        text,
        'PR #%s: %s' % (request.id, request.title),
        ','.join(mail_to),
        mail_id='%s/close/%s' % (request.mail_id, uid),
        in_reply_to=request.mail_id,
        project_name=request.project.fullname,
        user_from=user.fullname or user.user,
    )


def notify_cancelled_pull_request(request, user):
    ''' Notify the people following a project that a pull-request was
    cancelled in it.
    '''
    text = u"""
%s canceled a pull-request against the project: `%s` that you are following.

Cancelled pull-request:

``
%s
``

%s
""" % (user.username,
       request.project.name,
       request.title,
       _build_url(
           pagure.APP.config['APP_URL'],
           _fullname_to_url(request.project.fullname),
           'pull-request',
           request.id))
    mail_to = _get_emails_for_obj(request)

    uid = time.mktime(datetime.datetime.now().timetuple())
    send_email(
        text,
        'PR #%s: %s' % (request.id, request.title),
        ','.join(mail_to),
        mail_id='%s/close/%s' % (request.mail_id, uid),
        in_reply_to=request.mail_id,
        project_name=request.project.fullname,
        user_from=user.fullname or user.user,
    )


def notify_pull_request_comment(comment, user):
    ''' Notify the people following a pull-request that a new comment was
    added to it.
    '''
    text = u"""
%s commented on the pull-request: `%s` that you are following:
``
%s
``

%s
%s
""" % (comment.user.user,
       comment.pull_request.title,
       comment.comment,
       REPLY_MSG,
       _build_url(
           pagure.APP.config['APP_URL'],
           _fullname_to_url(comment.pull_request.project.fullname),
           'pull-request',
           comment.pull_request.id))
    mail_to = _get_emails_for_obj(comment.pull_request)
    mail_to = _add_mentioned_users(mail_to, comment.comment)
    mail_to = _clean_emails(mail_to, user)

    send_email(
        text,
        'PR #%s: %s' % (comment.pull_request.id, comment.pull_request.title),
        ','.join(mail_to),
        mail_id=comment.mail_id,
        in_reply_to=comment.pull_request.mail_id,
        project_name=comment.pull_request.project.fullname,
        user_from=comment.user.fullname or comment.user.user,
    )


def notify_new_email(email, user):
    ''' Ask the user to confirm to the email belong to them.
    '''

    root_url = pagure.APP.config.get('APP_URL', flask.request.url_root)

    url = urlparse.urljoin(
        root_url or flask.request.url_root,
        flask.url_for('confirm_email', token=email.token),
    )

    text = u"""Dear %(username)s,

You have registered a new email on pagure at %(root_url)s.

To finish your validate this registration, please click on the following
link or copy/paste it in your browser, this link will remain valid only 2 days:
  %(url)s

The email will not be activated until you finish this step.

Sincerely,
Your pagure admin.
""" % ({'username': user.username, 'url': url, 'root_url': root_url})

    send_email(
        text,
        'Confirm new email',
        email.email,
        user_from=user.fullname or user.user,
    )
