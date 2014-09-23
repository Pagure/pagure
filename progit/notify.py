#-*- coding: utf-8 -*-

"""
 (c) 2014 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

progit notifications.
"""

import smtplib

import progit

from email.mime.text import MIMEText


def send_email(text, subject, to_mail, from_mail=None):
    ''' Send an email with the specified information.

    :arg text: the content of the email to send
    :arg subject: the subject of the email
    :arg to_mail: a string representing a list of recipient separated by a
        coma
    :kwarg from_mail: the email address the email is sent from.
        Defaults to nobody@progit

    '''
    msg = MIMEText(text.encode('utf-8'), 'plain', 'utf-8')
    msg['Subject'] = '[Progit] %s' % subject
    if not from_mail:
        from_email = 'progit@fedoraproject.org'
    msg['From'] = from_email
    msg['To'] = to_mail.replace(',', ', ')

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
%s added a new comment has been added to an issue you are following.

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
    send_email(
        text,
        'Update to issue `%s`' % comment.issue.title,
        ','.join(mail_to)
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
    send_email(
        text,
        'New issue `%s`' % issue.title,
        ','.join(mail_to)
    )
