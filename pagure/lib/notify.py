# -*- coding: utf-8 -*-

"""
 (c) 2014-2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

pagure notifications.
"""

import datetime
import hashlib
import hmac
import json
import urlparse
import smtplib
import six
import time
import uuid
import warnings

import flask
import requests
import pagure

from email.mime.text import MIMEText
from kitchen.text.converters import to_bytes


_i = 0


def fedmsg_publish(*args, **kwargs):  # pragma: no cover
    ''' Try to publish a message on the fedmsg bus. '''
    # We catch Exception if we want :-p
    # pylint: disable=W0703
    # Ignore message about fedmsg import
    # pylint: disable=F0401
    kwargs['modname'] = 'pagure'
    try:
        import fedmsg
        fedmsg.publish(*args, **kwargs)
    except Exception, err:
        warnings.warn(str(err))


def log(project, topic, msg):
    ''' This is the place where we send notifications to user about actions
    occuring in pagure.
    '''
    # Send fedmsg notification (if fedmsg is there and set-up)
    fedmsg_publish(topic, msg)

    # Send web-hooks notification
    if not isinstance(project, basestring) \
            and project.settings.get('Web-hooks'):  # pragma: no cover
        global _i
        _i += 1
        year = datetime.datetime.now().year
        if isinstance(topic, six.text_type):
            topic = to_bytes(topic, encoding='utf8', nonstring="passthru")
        msg = dict(
            topic=topic.decode('utf-8'),
            msg=msg,
            timestamp=int(time.time()),
            msg_id=str(year) + '-' + str(uuid.uuid4()),
            i=_i,
        )

        content = json.dumps(msg)
        hashhex = hmac.new(
            str(project.hook_token), content, hashlib.sha1).hexdigest()
        headers = {
            'X-Pagure-Topic': topic,
            'X-Pagure-Signature': hashhex
        }
        msg = flask.json.dumps(msg)
        for url in project.settings.get('Web-hooks').split('\n'):
            url = url.strip()
            try:
                req = requests.post(
                    url,
                    headers=headers,
                    data={'payload': msg}
                )
                if not req:
                    raise pagure.exceptions.PagureException(
                        'An error occured while querying: %s - '
                        'Error code: %s' % (url, req.status_code))
            except (requests.exceptions.RequestException, Exception) as err:
                raise pagure.exceptions.PagureException(
                    'An error occured while querying: %s - Error: %s' % (
                        url, err))


def _clean_emails(emails, user):
    ''' Remove the email of the user doing the action if it is in the list.

    This avoids receiving emails about action you do.
    '''
    # Remove the user doing the action from the list of person to email
    if user and user.emails:
        for email in user.emails:
            if email.email in emails:
                emails.remove(email.email)
    return emails


def _get_emails_for_issue(issue):
    ''' Return the list of emails to send notification to when notifying
    about the specified issue.
    '''
    emails = set()
    # Add project creator/owner
    if issue.project.user.emails:
        emails.add(issue.project.user.emails[0].email)

    # Add project maintainers
    for user in issue.project.users:
        if user.default_email:
            emails.add(user.default_email)

    # Add people that commented on the ticket
    for comment in issue.comments:
        if comment.user.default_email:
            emails.add(comment.user.default_email)

    # Add the person that opened the issue
    if issue.user.default_email:
        emails.add(issue.user.default_email)

    # Add the person assigned to the ticket
    if issue.assignee and issue.assignee.default_email:
        emails.add(issue.assignee.default_email)

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


def send_email(text, subject, to_mail,
               mail_id=None, in_reply_to=None):  # pragma: no cover
    ''' Send an email with the specified information.

    :arg text: the content of the email to send
    :arg subject: the subject of the email
    :arg to_mail: a string representing a list of recipient separated by a
        coma
    :kwarg mail_id: if defined, the header `mail-id` is set with this value
    :kwarg in_reply_to: if defined, the header `In-Reply-To` is set with
        this value

    '''
    if not to_mail:
        return

    if not pagure.APP.config.get('EMAIL_SEND', True):
        print '******EMAIL******'
        print 'To: %s' % to_mail
        print 'Subject: %s' % subject
        print 'in_reply_to: %s' % in_reply_to
        print 'mail_id: %s' % mail_id
        print 'Contents:'
        print text
        print '*****/EMAIL******'
        return

    smtp = smtplib.SMTP(pagure.APP.config['SMTP_SERVER'])
    for mailto in to_mail.split(','):
        msg = MIMEText(text.encode('utf-8'), 'plain', 'utf-8')
        msg['Subject'] = '[Pagure] %s' % subject
        from_email = pagure.APP.config.get(
            'FROM_EMAIL', 'pagure@fedoraproject.org')
        msg['From'] = from_email

        if mail_id:
            msg['mail-id'] = mail_id
            msg['Message-Id'] = '<%s>' % mail_id

        if in_reply_to:
            msg['In-Reply-To'] = '<%s>' % in_reply_to

        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        msg['To'] = mailto
        salt = pagure.APP.config.get('SALT_EMAIL')
        mhash = hashlib.sha512('<%s>%s%s' % (mail_id, salt, mailto))
        msg['Reply-To'] = 'reply+%s@%s' % (
            mhash.hexdigest(),
            pagure.APP.config['DOMAIN_EMAIL_NOTIFICATIONS'])
        try:
            smtp.sendmail(
                from_email,
                [mailto],
                msg.as_string())
        except smtplib.SMTPException as err:
            pagure.LOG.exception(err)
    smtp.quit()
    return msg


def notify_new_comment(comment, user=None):
    ''' Notify the people following an issue that a new comment was added
    to the issue.
    '''
    text = """
%s added a new comment to an issue you are following:
``
%s
``

To reply, visit the link below or just reply to this email
%s
""" % (comment.user.user,
       comment.comment,
       _build_url(
           pagure.APP.config['APP_URL'],
           comment.issue.project.name,
           'issue',
           comment.issue.id))
    mail_to = _get_emails_for_issue(comment.issue)
    if comment.user and comment.user.default_email:
        mail_to.add(comment.user.default_email)

    mail_to = _clean_emails(mail_to, user)

    send_email(
        text,
        'Update to issue #%s `%s`' % (comment.issue.id, comment.issue.title),
        ','.join(mail_to),
        mail_id=comment.mail_id,
        in_reply_to=comment.issue.mail_id,
    )


def notify_new_issue(issue, user=None):
    ''' Notify the people following a project that a new issue was added
    to it.
    '''
    text = """
%s reported a new issue against the project: `%s` that you are following:
``
%s
``

To reply, visit the link below or just reply to this email
%s
""" % (issue.user.user,
       issue.project.name,
       issue.content,
       _build_url(
           pagure.APP.config['APP_URL'],
           issue.project.name,
           'issue',
           issue.id))
    mail_to = _get_emails_for_issue(issue)
    mail_to = _clean_emails(mail_to, user)

    send_email(
        text,
        'New issue `%s`' % issue.title,
        ','.join(mail_to),
        mail_id=issue.mail_id,
    )


def notify_assigned_issue(issue, new_assignee, user):
    ''' Notify the people following an issue that the assignee changed.
    '''
    action = 'reset'
    if new_assignee:
        action = 'assigned to `%s`' % new_assignee.user
    text = """
The issue: `%s` of project: `%s` has been %s by %s.

%s
""" % (issue.title,
       issue.project.name,
       action,
       user.username,
       _build_url(
           pagure.APP.config['APP_URL'],
           issue.project.name,
           'issue',
           issue.id))
    mail_to = _get_emails_for_issue(issue)
    if new_assignee and new_assignee.default_email:
        mail_to.add(new_assignee.default_email)

    mail_to = _clean_emails(mail_to, user)

    uid = time.mktime(datetime.datetime.now().timetuple())
    send_email(
        text,
        'Issue `%s` assigned' % issue.title,
        ','.join(mail_to),
        mail_id='%s/assigned/%s' % (issue.mail_id, uid),
        in_reply_to=issue.mail_id,
    )


def notify_assigned_request(request, new_assignee, user):
    ''' Notify the people following a pull-request that the assignee changed.
    '''
    action = 'reset'
    if new_assignee:
        action = 'assigned to `%s`' % new_assignee.user
    text = """
The pull-request: `%s` of project: `%s` has been %s by %s.

%s
""" % (request.title,
       request.project.name,
       action,
       user.username,
       _build_url(
           pagure.APP.config['APP_URL'],
           request.project.name,
           'pull-request',
           request.id))
    mail_to = _get_emails_for_issue(request)
    if new_assignee and new_assignee.default_email:
        mail_to.add(new_assignee.default_email)

    mail_to = _clean_emails(mail_to, user)

    uid = time.mktime(datetime.datetime.now().timetuple())
    send_email(
        text,
        'Pull-request `%s` assigned' % request.title,
        ','.join(mail_to),
        mail_id='%s/assigned/%s' % (request.mail_id, uid),
        in_reply_to=request.mail_id,
    )


def notify_new_pull_request(request):
    ''' Notify the people following a project that a new pull-request was
    added to it.
    '''
    text = """
%s opened a new pull-request against the project: `%s` that you are following:
``
%s
``

To reply, visit the link below or just reply to this email
%s
""" % (request.user.user,
       request.project.name,
       request.title,
       _build_url(
           pagure.APP.config['APP_URL'],
           request.project.name,
           'pull-request',
           request.id))
    mail_to = _get_emails_for_issue(request)

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
""" % (user.username,
       request.project.name,
       request.title,
       _build_url(
           pagure.APP.config['APP_URL'],
           request.project.name,
           'pull-request',
           request.id))
    mail_to = _get_emails_for_issue(request)

    uid = time.mktime(datetime.datetime.now().timetuple())
    send_email(
        text,
        'Pull-Request #%s `%s`' % (request.id, request.title),
        ','.join(mail_to),
        mail_id='%s/close/%s' % (request.mail_id, uid),
        in_reply_to=request.mail_id,
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
""" % (user.username,
       request.project.name,
       request.title,
       _build_url(
           pagure.APP.config['APP_URL'],
           request.project.name,
           'pull-request',
           request.id))
    mail_to = _get_emails_for_issue(request)

    uid = time.mktime(datetime.datetime.now().timetuple())
    send_email(
        text,
        'Pull-Request #%s `%s`' % (request.id, request.title),
        ','.join(mail_to),
        mail_id='%s/close/%s' % (request.mail_id, uid),
        in_reply_to=request.mail_id,
    )


def notify_pull_request_comment(comment, user):
    ''' Notify the people following a pull-request that a new comment was
    added to it.
    '''
    text = """
%s commented on the pull-request: `%s` that you are following:
``
%s
``

To reply, visit the link below or just reply to this email
%s
""" % (comment.user.user,
       comment.pull_request.title,
       comment.comment,
       _build_url(
           pagure.APP.config['APP_URL'],
           comment.pull_request.project.name,
           'pull-request',
           comment.pull_request.id))
    mail_to = _get_emails_for_issue(comment.pull_request)
    mail_to = _clean_emails(mail_to, user)

    send_email(
        text,
        'Update to %s pull-Request #%s `%s`' % (
            comment.pull_request.project.name,
            comment.pull_request.id,
            comment.pull_request.title),
        ','.join(mail_to),
        mail_id=comment.mail_id,
        in_reply_to=comment.pull_request.mail_id,
    )


def notify_new_email(email, user):
    ''' Ask the user to confirm to the email belong to them.
    '''

    root_url = pagure.APP.config.get('APP_URL', flask.request.url_root)

    url = urlparse.urljoin(
        root_url or flask.request.url_root,
        flask.url_for('confirm_email', token=email.token),
    )

    text = """Dear %(username)s,

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
    )
