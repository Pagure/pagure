# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

progit notifications.
"""

import smtplib

import progit

from email.mime.text import MIMEText


def send_email(text, subject, to_mail, from_mail=None, mail_id=None,
               in_reply_to=None):  # pragma: no cover
    ''' Send an email with the specified information.

    :arg text: the content of the email to send
    :arg subject: the subject of the email
    :arg to_mail: a string representing a list of recipient separated by a
        coma
    :kwarg from_mail: the email address the email is sent from.
        Defaults to nobody@progit
    :kwarg mail_id: if defined, the header `mail-id` is set with this value
    :kwarg in_reply_to: if defined, the header `In-Reply-To` is set with
        this value

    '''
    msg = MIMEText(text.encode('utf-8'), 'plain', 'utf-8')
    msg['Subject'] = '[Progit] %s' % subject
    if not from_mail:
        from_email = 'progit@fedoraproject.org'
    msg['From'] = from_email
    msg['Bcc'] = to_mail.replace(',', ', ')

    if mail_id:
        msg['mail-id'] = mail_id
        msg['Message-Id'] = '<%s>' % mail_id

    if in_reply_to:
        msg['In-Reply-To'] = '<%s>' % in_reply_to

    # Send the message via our own SMTP server, but don't include the
    # envelope header.
    smtp = smtplib.SMTP(progit.APP.config['SMTP_SERVER'])
    smtp.sendmail(
        from_email,
        to_mail.split(','),
        msg.as_string())
    smtp.quit()
    return msg


def notify_new_comment(comment):
    ''' Notify the people following an issue that a new comment was added
    to the issue.
    '''
    text = """
%s added a new comment to an issue you are following.

New comment:

``
%s
``

%s
""" % (
        comment.user.user,
        comment.comment,
        '%s/%s/issue/%s' % (
            progit.APP.config['APP_URL'],
            comment.issue.project.name,
            comment.issue.id,
        ),
    )
    mail_to = set([cmt.user.emails[0].email for cmt in comment.issue.comments])
    mail_to.add(comment.issue.project.user.emails[0].email)
    if comment.issue.assignee and comment.issue.assignee.emails:
        mail_to.add(comment.issue.assignee.emails[0].email)
    send_email(
        text,
        'Update to issue `%s`' % comment.issue.title,
        ','.join(mail_to),
        in_reply_to=comment.issue.mail_id,
    )


def notify_new_issue(issue):
    ''' Notify the people following a project that a new issue was added
    to it.
    '''
    text = """
%s reported a new issue against the project: `%s` that you are following.

New issue:

``
%s
``

%s
""" % (
        issue.user.user,
        issue.project.name,
        issue.content,
        '%s/%s/issue/%s' % (
            progit.APP.config['APP_URL'],
            issue.project.name,
            issue.id,
        ),
    )
    mail_to = set([cmt.user.emails[0].email for cmt in issue.comments])
    mail_to.add(issue.project.user.emails[0].email)
    if issue.assignee:
        mail_to.add(issue.assignee.emails[0].email)
    for prouser in issue.project.users:
        if prouser.emails:
            mail_to.add(prouser.emails[0].email)

    send_email(
        text,
        'New issue `%s`' % issue.title,
        ','.join(mail_to),
        mail_id=issue.mail_id,
    )


def notify_assigned_issue(issue, new_assignee, username):
    ''' Notify the people following an issue that the assignee changed.
    '''
    action = 'reset'
    if new_assignee:
        action = 'assigned to `%s`' % new_assignee.user
    text = """
The issue: `%s` of project: `%s` has been %s by %s.

%s
""" % (
        issue.title,
        issue.project.name,
        action,
        username,
        '%s/%s/issue/%s' % (
            progit.APP.config['APP_URL'],
            issue.project.name,
            issue.id,
        ),
    )
    mail_to = set([cmt.user.emails[0].email for cmt in issue.comments])
    mail_to.add(issue.project.user.emails[0].email)
    if issue.assignee and issue.assignee.emails:
        mail_to.add(issue.assignee.emails[0].email)
    if new_assignee and new_assignee.emails:
        mail_to.add(new_assignee.emails[0].email)

    send_email(
        text,
        'Issue `%s` assigned' % issue.title,
        ','.join(mail_to),
        mail_id=issue.mail_id,
    )


def notify_new_pull_request(request):
    ''' Notify the people following a project that a new pull-request was
    added to it.
    '''
    text = """
%s opened a new pull-request against the project: `%s` that you are following.

New pull-request:

``
%s
``

%s
""" % (
        request.user.user,
        request.repo.name,
        request.title,
        '%s/%s/request-pull/%s' % (
            progit.APP.config['APP_URL'],
            request.repo.name,
            request.id,
        ),
    )
    mail_to = set([cmt.user.emails[0].email for cmt in request.comments])
    mail_to.add(request.repo.user.emails[0].email)
    for prouser in request.repo.users:
        if prouser.emails:
            mail_to.add(prouser.emails[0].email)

    send_email(
        text,
        'Pull-Request #%s `%s`' % (request.id, request.title),
        ','.join(mail_to),
        mail_id=request.mail_id,
    )


def notify_merge_pull_request(request, user):
    ''' Notify the people following a project that a pull-request was merged
    in it.
    '''
    text = """
%s merged a pull-request against the project: `%s` that you are following.

Merged pull-request:

``
%s
``

%s
""" % (
        user.username,
        request.repo.name,
        request.title,
        '%s/%s/request-pull/%s' % (
            progit.APP.config['APP_URL'],
            request.repo.name,
            request.id,
        ),
    )
    mail_to = set([cmt.user.emails[0].email for cmt in request.comments])
    mail_to.add(request.repo.user.emails[0].email)
    for prouser in request.repo.users:
        if prouser.emails:
            mail_to.add(prouser.emails[0].email)

    send_email(
        text,
        'Pull-Request #%s `%s`' % (request.id, request.title),
        ','.join(mail_to),
        mail_id=request.mail_id,
    )


def notify_cancelled_pull_request(request, user):
    ''' Notify the people following a project that a pull-request was
    cancelled in it.
    '''
    text = """
%s canceled a pull-request against the project: `%s` that you are following.

Cancelled pull-request:

``
%s
``

%s
""" % (
        user.username,
        request.repo.name,
        request.title,
        '%s/%s/request-pull/%s' % (
            progit.APP.config['APP_URL'],
            request.repo.name,
            request.id,
        ),
    )
    mail_to = set([cmt.user.emails[0].email for cmt in request.comments])
    mail_to.add(request.repo.user.emails[0].email)
    for prouser in request.repo.users:
        if prouser.emails:
            mail_to.add(prouser.emails[0].email)

    send_email(
        text,
        'Pull-Request #%s `%s`' % (request.id, request.title),
        ','.join(mail_to),
        mail_id=request.mail_id,
    )
