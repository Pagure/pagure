# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

pagure notifications.
"""
from __future__ import print_function, unicode_literals, absolute_import


# pylint: disable=too-many-branches
# pylint: disable=too-many-arguments


import datetime
import hashlib
import json
import logging
import os
import re
import smtplib
import time
import six
import ssl
from email.header import Header
from email.mime.text import MIMEText
from six.moves.urllib_parse import urljoin

import blinker
import flask
import pagure.lib.query
import pagure.lib.tasks_services
from pagure.config import config as pagure_config
from pagure.pfmarkdown import MENTION_RE
from markdown.extensions.fenced_code import FencedBlockPreprocessor


_log = logging.getLogger(__name__)


REPLY_MSG = "To reply, visit the link below"
if pagure_config["EVENTSOURCE_SOURCE"]:
    REPLY_MSG += " or just reply to this email"


def fedmsg_publish(*args, **kwargs):  # pragma: no cover
    """ Try to publish a message on the fedmsg bus. """
    if not pagure_config.get("FEDMSG_NOTIFICATIONS", True):
        return

    _log.warning(
        "fedmsg support is being deprecated in favor of fedora-messaging "
        "you likely want to stop relying on it as it will disapear in the "
        "future, most likely in the 6.0 release"
    )

    # We catch Exception if we want :-p
    # pylint: disable=broad-except
    # Ignore message about fedmsg import
    # pylint: disable=import-error
    kwargs["modname"] = "pagure"
    kwargs["cert_prefix"] = "pagure"
    kwargs["active"] = True
    try:
        import fedmsg

        fedmsg.publish(*args, **kwargs)
    except Exception:
        _log.exception("Error sending fedmsg")


def fedora_messaging_publish(topic, message):  # pragma: no cover
    """ Try to publish a message on AMQP using fedora-messaging. """
    if not pagure_config.get("FEDORA_MESSAGING_NOTIFICATIONS", False):
        return

    try:
        import fedora_messaging.api
        import fedora_messaging.exceptions
        import pagure_messages

        msg_cls = pagure_messages.get_message_object_from_topic(
            "pagure.{}".format(topic)
        )

        if not hasattr(msg_cls, "app_name") is False:
            _log.warning(
                "pagure is about to send a message that has no schemas: %s",
                topic,
            )

        msg = msg_cls(body=message)
        if not msg.topic:
            msg.topic = "pagure.{}".format(topic)
        fedora_messaging.api.publish(msg)
    except ImportError:
        _log.warning(
            "Fedora messaging or pagure-messages does not appear to be "
            "available"
        )
    except fedora_messaging.exceptions.PublishReturned as e:
        _log.warning(
            "Fedora Messaging broker rejected message %s: %s", msg.id, e
        )
    except fedora_messaging.exceptions.ConnectionException as e:
        _log.warning("Error sending message %s: %s", msg.id, e)
    except Exception:
        _log.exception("Error sending fedora-messaging message")


stomp_conn = None


def stomp_publish(topic, message):
    """ Try to publish a message on a Stomp-compliant message bus. """
    if not pagure_config.get("STOMP_NOTIFICATIONS", False):
        return
    # We catch Exception if we want :-p
    # pylint: disable=broad-except
    # Ignore message about stomp import
    # pylint: disable=import-error
    try:
        import stomp

        global stomp_conn
        if not stomp_conn or not stomp_conn.is_connected():
            stomp_conn = stomp.Connection12(pagure_config["STOMP_BROKERS"])
            if pagure_config.get("STOMP_SSL"):
                stomp_conn.set_ssl(
                    pagure_config["STOMP_BROKERS"],
                    key_file=pagure_config.get("STOMP_KEY_FILE"),
                    cert_file=pagure_config.get("STOMP_CERT_FILE"),
                    password=pagure_config.get("STOMP_CREDS_PASSWORD"),
                )
            from stomp import PrintingListener

            stomp_conn.set_listener("", PrintingListener())
            stomp_conn.start()
            stomp_conn.connect(wait=True)
        hierarchy = pagure_config["STOMP_HIERARCHY"]
        stomp_conn.send(
            destination=hierarchy + topic, body=json.dumps(message)
        )
    except Exception:
        _log.exception("Error sending stomp message")


def blinker_publish(topic, message):
    _log.info("Sending blinker signal to: pagure - topic: %s", topic)
    ready = blinker.signal("pagure")
    ready.send("pagure", topic=topic, message=message)


def mqtt_publish(topic, message):
    """ Try to publish a message on a MQTT message bus. """
    if not pagure_config.get("MQTT_NOTIFICATIONS", False):
        return

    mqtt_host = pagure_config.get("MQTT_HOST")
    mqtt_port = pagure_config.get("MQTT_PORT")

    mqtt_username = pagure_config.get("MQTT_USERNAME")
    mqtt_pass = pagure_config.get("MQTT_PASSWORD")

    mqtt_ca_certs = pagure_config.get("MQTT_CA_CERTS")
    mqtt_certfile = pagure_config.get("MQTT_CERTFILE")
    mqtt_keyfile = pagure_config.get("MQTT_KEYFILE")
    mqtt_cert_reqs = pagure_config.get("MQTT_CERT_REQS", ssl.CERT_REQUIRED)
    mqtt_tls_version = pagure_config.get(
        "MQTT_TLS_VERSION", ssl.PROTOCOL_TLSv1_2
    )
    mqtt_ciphers = pagure_config.get("MQTT_CIPHERS")

    mqtt_topic_prefix = pagure_config.get("MQTT_TOPIC_PREFIX") or None
    if mqtt_topic_prefix:
        topic = "/".join([mqtt_topic_prefix.rstrip("/"), topic])

    # We catch Exception if we want :-p
    # pylint: disable=broad-except
    # Ignore message about mqtt import
    # pylint: disable=import-error
    try:
        import paho.mqtt.client as mqtt

        client = mqtt.Client(os.uname()[1])
        client.tls_set(
            ca_certs=mqtt_ca_certs,
            certfile=mqtt_certfile,
            keyfile=mqtt_keyfile,
            cert_reqs=mqtt_cert_reqs,
            tls_version=mqtt_tls_version,
            ciphers=mqtt_ciphers,
        )
        if mqtt_username and mqtt_pass:
            client.username_pw_set(mqtt_username, mqtt_pass)

        client.connect(mqtt_host, mqtt_port)
        client.publish(topic, json.dumps(message))
        client.disconnect()

    except Exception:
        _log.exception("Error sending mqtt message")


def log(project, topic, msg, webhook=True):
    """ This is the place where we send notifications to user about actions
    occuring in pagure.
    """

    # Send fedmsg notification (if fedmsg is there and set-up)
    if not project or (
        project.settings.get("fedmsg_notifications", True)
        and not project.private
    ):
        fedmsg_publish(topic, msg)
        fedora_messaging_publish(topic, msg)

    # Send stomp notification (if stomp is there and set-up)
    if not project or (
        project.settings.get("stomp_notifications", True)
        and not project.private
    ):
        stomp_publish(topic, msg)

    # Send mqtt notification (if mqtt is there and set-up)
    if not project or (
        project.settings.get("mqtt_notifications", True)
        and not project.private
    ):
        mqtt_publish(topic, msg)

    # Send blink notification to any 3rd party plugins, if there are any
    blinker_publish(topic, msg)

    if webhook and project and not project.private:
        pagure.lib.tasks_services.webhook_notification.delay(
            topic=topic,
            msg=msg,
            namespace=project.namespace,
            name=project.name,
            user=project.user.username if project.is_fork else None,
        )


def _add_mentioned_users(emails, comment):
    """ Check the comment to see if an user is mentioned in it and if
    so add this user to the list of people to notify.
    """
    filtered_comment = re.sub(
        FencedBlockPreprocessor.FENCED_BLOCK_RE, "", comment
    )
    for username in re.findall(MENTION_RE, filtered_comment):
        user = pagure.lib.query.search_user(flask.g.session, username=username)
        if user:
            emails.add(user.default_email)
    return emails


def _clean_emails(emails, user):
    """ Remove the email of the user doing the action if it is in the list.

    This avoids receiving emails about action you do.
    """
    # Remove the user doing the action from the list of person to email
    # unless they actively asked for it
    if (
        user
        and user.emails
        and not user.settings.get("cc_me_to_my_actions", False)
    ):
        for email in user.emails:
            if email.email in emails:
                emails.remove(email.email)
    return emails


def _get_emails_for_obj(obj):
    """ Return the list of emails to send notification to when notifying
    about the specified issue or pull-request.
    """
    emails = set()
    # Add project creator/owner
    if obj.project.user.default_email:
        emails.add(obj.project.user.default_email)

    # Add committers is object is private, otherwise all contributors
    if obj.isa in ["issue", "pull-request"] and obj.private:
        for user in obj.project.committers:
            if user.default_email:
                emails.add(user.default_email)
    else:
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
    if obj.isa in ["issue", "pull-request"]:
        for comment in obj.comments:
            if comment.user.default_email:
                emails.add(comment.user.default_email)

    # Add public notifications to lists/users set project-wide
    if obj.isa == "issue" and not obj.private:
        for notifs in obj.project.notifications.get("issues", []):
            emails.add(notifs)
    elif obj.isa == "pull-request":
        for notifs in obj.project.notifications.get("requests", []):
            emails.add(notifs)

    # Add the person watching this project, if it's a public issue or a
    # pull-request
    if (obj.isa == "issue" and not obj.private) or obj.isa == "pull-request":
        for watcher in obj.project.watchers:
            if watcher.watch_issues:
                emails.add(watcher.user.default_email)
            else:
                # If there is a watch entry and it is false, it means the user
                # explicitly requested to not watch the issue
                if watcher.user.default_email in emails:
                    emails.remove(watcher.user.default_email)

    # Add/Remove people who explicitly asked to be added/removed
    if obj.isa in ["issue", "pull-request"]:
        for watcher in obj.watchers:
            if not watcher.watch and watcher.user.default_email in emails:
                emails.remove(watcher.user.default_email)
            elif watcher.watch:
                emails.add(watcher.user.default_email)

    # Drop the email used by pagure when sending
    emails = _clean_emails(
        emails,
        pagure_config.get(
            pagure_config.get("FROM_EMAIL", "pagure@fedoraproject.org")
        ),
    )

    # Add the person that opened the issue/PR
    if obj.user.default_email:
        emails.add(obj.user.default_email)

    # Add the person assigned to the issue/PR
    if obj.isa in ["issue", "pull-request"]:
        if obj.assignee and obj.assignee.default_email:
            emails.add(obj.assignee.default_email)

    return emails


def _get_emails_for_commit_notification(project):
    emails = set()
    for watcher in project.watchers:
        if watcher.watch_commits:
            emails.add(watcher.user.default_email)

    # Drop the email used by pagure when sending
    emails = _clean_emails(
        emails,
        pagure_config.get(
            pagure_config.get("FROM_EMAIL", "pagure@fedoraproject.org")
        ),
    )

    return emails


def _build_url(*args):
    """ Build a URL from a given list of arguments. """
    items = []
    for idx, arg in enumerate(args):
        arg = "%s" % arg
        if arg.startswith("/"):
            arg = arg[1:]
        if arg.endswith("/") and not idx + 1 == len(args):
            arg = arg[:-1]
        items.append(arg)

    return "/".join(items)


def _fullname_to_url(fullname):
    """ For forked projects, fullname is 'forks/user/...' but URL is
    'fork/user/...'. This is why we can't have nice things.
    """
    if fullname.startswith("forks/"):
        fullname = fullname.replace("forks", "fork", 1)
    return fullname


def send_email(
    text,
    subject,
    to_mail,
    mail_id=None,
    in_reply_to=None,
    project_name=None,
    user_from=None,
    reporter=None,
    assignee=None,
):  # pragma: no cover
    """ Send an email with the specified information.

    :arg text: the content of the email to send
    :type text: unicode
    :arg subject: the subject of the email
    :arg to_mail: a string representing a list of recipient separated by a
        comma
    :kwarg mail_id: if defined, the header `mail-id` is set with this value
    :kwarg in_reply_to: if defined, the header `In-Reply-To` is set with
        this value
    :kwarg project_name: if defined, the name of the project

    """
    if not to_mail:
        return

    from_email = pagure_config.get("FROM_EMAIL", "pagure@fedoraproject.org")
    if isinstance(from_email, bytes):
        from_email = from_email.decode("utf-8")
    if user_from:
        header = Header(user_from, "utf-8")
        from_email = "%s <%s>" % (header.encode(), from_email)

    if project_name is not None:
        subject_tag = project_name
    else:
        subject_tag = "Pagure"
    if mail_id:
        mail_id = mail_id + "@%s" % pagure_config["DOMAIN_EMAIL_NOTIFICATIONS"]
    if in_reply_to:
        in_reply_to = (
            in_reply_to + "@%s" % pagure_config["DOMAIN_EMAIL_NOTIFICATIONS"]
        )

    smtp = None
    for mailto in to_mail.split(","):
        try:
            pagure.lib.query.allowed_emailaddress(mailto)
        except pagure.exceptions.PagureException:
            continue
        msg = MIMEText(text.encode("utf-8"), "plain", "utf-8")
        msg["Subject"] = Header("[%s] %s" % (subject_tag, subject), "utf-8")
        msg["From"] = from_email

        if mail_id:
            msg["mail-id"] = mail_id
            msg["Message-Id"] = "<%s>" % mail_id

        if in_reply_to:
            msg["In-Reply-To"] = "<%s>" % in_reply_to

        msg["X-Auto-Response-Suppress"] = "All"
        msg["X-pagure"] = pagure_config["APP_URL"]
        if project_name is not None:
            msg["X-pagure-project"] = project_name
            msg["List-ID"] = project_name
            msg["List-Archive"] = _build_url(
                pagure_config["APP_URL"], _fullname_to_url(project_name)
            )
        if reporter is not None:
            msg["X-pagure-reporter"] = reporter
        if assignee is not None:
            msg["X-pagure-assignee"] = assignee

        # Send the message via our own SMTP server, but don't include the
        # envelope header.
        msg["To"] = mailto
        salt = pagure_config.get("SALT_EMAIL")
        if salt and not isinstance(salt, bytes):
            salt = salt.encode("utf-8")

        if mail_id and pagure_config["EVENTSOURCE_SOURCE"]:

            key = (
                b"<"
                + mail_id.encode("utf-8")
                + b">"
                + salt
                + mailto.encode("utf-8")
            )
            if isinstance(key, six.text_type):
                key = key.encode("utf-8")
            mhash = hashlib.sha512(key)

            msg["Reply-To"] = "reply+%s@%s" % (
                mhash.hexdigest(),
                pagure_config["DOMAIN_EMAIL_NOTIFICATIONS"],
            )
            msg["Mail-Followup-To"] = msg["Reply-To"]
        if not pagure_config.get("EMAIL_SEND", True):
            _log.debug("******EMAIL******")
            _log.debug("From: %s", from_email)
            _log.debug("To: %s", to_mail)
            _log.debug("Subject: %s", subject)
            _log.debug("in_reply_to: %s", in_reply_to)
            _log.debug("mail_id: %s", mail_id)
            _log.debug("Contents:")
            _log.debug("%s" % text)
            _log.debug("*****************")
            _log.debug(msg.as_string())
            _log.debug("*****/EMAIL******")
            continue
        try:
            if smtp is None:
                if pagure_config["SMTP_SSL"]:
                    smtp = smtplib.SMTP_SSL(
                        pagure_config["SMTP_SERVER"],
                        pagure_config["SMTP_PORT"],
                    )
                else:
                    smtp = smtplib.SMTP(
                        pagure_config["SMTP_SERVER"],
                        pagure_config["SMTP_PORT"],
                    )

            if pagure_config.get("SMTP_STARTTLS"):
                context = ssl.create_default_context()
                keyfile = pagure_config.get("SMTP_KEYFILE") or None
                certfile = pagure_config.get("SMTP_CERTFILE") or None
                respcode, _ = smtp.starttls(
                    keyfile=keyfile, certfile=certfile, context=context,
                )
                if respcode != 220:
                    _log.warning(
                        "The starttls command did not return the 220 "
                        "response code expected."
                    )

            if (
                pagure_config["SMTP_USERNAME"]
                and pagure_config["SMTP_PASSWORD"]
            ):
                smtp.login(
                    pagure_config["SMTP_USERNAME"],
                    pagure_config["SMTP_PASSWORD"],
                )

            smtp.sendmail(from_email, [mailto], msg.as_string())
        except smtplib.SMTPException as err:
            _log.exception(err)
    if smtp:
        smtp.quit()
    return msg


def notify_new_comment(comment, user=None):
    """ Notify the people following an issue that a new comment was added
    to the issue.
    """

    text = """
%s added a new comment to an issue you are following:
``
%s
``

%s
%s
""" % (
        comment.user.user,
        comment.comment,
        REPLY_MSG,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(comment.issue.project.fullname),
            "issue",
            comment.issue.id,
        ),
    )
    mail_to = _get_emails_for_obj(comment.issue)
    if comment.user and comment.user.default_email:
        mail_to.add(comment.user.default_email)

    mail_to = _add_mentioned_users(mail_to, comment.comment)
    mail_to = _clean_emails(mail_to, user)

    assignee = comment.issue.assignee.user if comment.issue.assignee else None

    send_email(
        text,
        "Issue #%s: %s" % (comment.issue.id, comment.issue.title),
        ",".join(mail_to),
        mail_id=comment.mail_id,
        in_reply_to=comment.issue.mail_id,
        project_name=comment.issue.project.fullname,
        user_from=comment.user.fullname or comment.user.user,
        reporter=comment.issue.user.user,
        assignee=assignee,
    )


def notify_new_issue(issue, user=None):
    """ Notify the people following a project that a new issue was added
    to it.
    """
    text = """
%s reported a new issue against the project: `%s` that you are following:
``
%s
``

%s
%s
""" % (
        issue.user.user,
        issue.project.name,
        issue.content,
        REPLY_MSG,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(issue.project.fullname),
            "issue",
            issue.id,
        ),
    )
    mail_to = _get_emails_for_obj(issue)
    mail_to = _add_mentioned_users(mail_to, issue.content)
    mail_to = _clean_emails(mail_to, user)

    assignee = issue.assignee.user if issue.assignee else None

    send_email(
        text,
        "Issue #%s: %s" % (issue.id, issue.title),
        ",".join(mail_to),
        mail_id=issue.mail_id,
        project_name=issue.project.fullname,
        user_from=issue.user.fullname or issue.user.user,
        reporter=issue.user.user,
        assignee=assignee,
    )


def notify_assigned_issue(issue, new_assignee, user):
    """ Notify the people following an issue that the assignee changed.
    """
    action = "reset"
    if new_assignee:
        action = "assigned to `%s`" % new_assignee.user
    text = """
The issue: `%s` of project: `%s` has been %s by %s.

%s
""" % (
        issue.title,
        issue.project.name,
        action,
        user.username,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(issue.project.fullname),
            "issue",
            issue.id,
        ),
    )
    mail_to = _get_emails_for_obj(issue)
    if new_assignee and new_assignee.default_email:
        mail_to.add(new_assignee.default_email)

    mail_to = _clean_emails(mail_to, user)

    uid = time.mktime(datetime.datetime.now().timetuple())

    assignee = issue.assignee.user if issue.assignee else None

    send_email(
        text,
        "Issue #%s: %s" % (issue.id, issue.title),
        ",".join(mail_to),
        mail_id="%s/assigned/%s" % (issue.mail_id, uid),
        in_reply_to=issue.mail_id,
        project_name=issue.project.fullname,
        user_from=user.fullname or user.user,
        reporter=issue.user.user,
        assignee=assignee,
    )


def notify_status_change_issue(issue, user):
    """ Notify the people following a project that an issue changed status.
    """
    status = issue.status
    if status.lower() != "open" and issue.close_status:
        status = "%s as %s" % (status, issue.close_status)
    text = """
The status of the issue: `%s` of project: `%s` has been updated to: %s by %s.

%s
""" % (
        issue.title,
        issue.project.fullname,
        status,
        user.username,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(issue.project.fullname),
            "issue",
            issue.id,
        ),
    )
    mail_to = _get_emails_for_obj(issue)

    uid = time.mktime(datetime.datetime.now().timetuple())

    assignee = issue.assignee.user if issue.assignee else None

    send_email(
        text,
        "Issue #%s: %s" % (issue.id, issue.title),
        ",".join(mail_to),
        mail_id="%s/close/%s" % (issue.mail_id, uid),
        in_reply_to=issue.mail_id,
        project_name=issue.project.fullname,
        user_from=user.fullname or user.user,
        reporter=issue.user.user,
        assignee=assignee,
    )


def notify_meta_change_issue(issue, user, msg):
    """ Notify that a custom field changed
    """
    text = """
`%s` updated issue.

%s

%s
""" % (
        user.username,
        msg,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(issue.project.fullname),
            "issue",
            issue.id,
        ),
    )
    mail_to = _get_emails_for_obj(issue)
    uid = time.mktime(datetime.datetime.now().timetuple())

    assignee = issue.assignee.user if issue.assignee else None

    send_email(
        text,
        "Issue #%s: %s" % (issue.id, issue.title),
        ",".join(mail_to),
        mail_id="%s/close/%s" % (issue.mail_id, uid),
        in_reply_to=issue.mail_id,
        project_name=issue.project.fullname,
        user_from=user.fullname or user.user,
        reporter=issue.user.user,
        assignee=assignee,
    )


def notify_assigned_request(request, new_assignee, user):
    """ Notify the people following a pull-request that the assignee changed.
    """
    action = "reset"
    if new_assignee:
        action = "assigned to `%s`" % new_assignee.user
    text = """
The pull-request: `%s` of project: `%s` has been %s by %s.

%s
""" % (
        request.title,
        request.project.name,
        action,
        user.username,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(request.project.fullname),
            "pull-request",
            request.id,
        ),
    )
    mail_to = _get_emails_for_obj(request)
    if new_assignee and new_assignee.default_email:
        mail_to.add(new_assignee.default_email)

    mail_to = _clean_emails(mail_to, user)

    uid = time.mktime(datetime.datetime.now().timetuple())

    assignee = request.assignee.user if request.assignee else None

    send_email(
        text,
        "PR #%s: %s" % (request.id, request.title),
        ",".join(mail_to),
        mail_id="%s/assigned/%s" % (request.mail_id, uid),
        in_reply_to=request.mail_id,
        project_name=request.project.fullname,
        user_from=user.fullname or user.user,
        reporter=request.user.user,
        assignee=assignee,
    )


def notify_new_pull_request(request):
    """ Notify the people following a project that a new pull-request was
    added to it.
    """
    text = """
%s opened a new pull-request against the project: `%s` that you are following:
``
%s
``

%s
%s
""" % (
        request.user.user,
        request.project.name,
        request.title,
        REPLY_MSG,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(request.project.fullname),
            "pull-request",
            request.id,
        ),
    )
    mail_to = _get_emails_for_obj(request)

    assignee = request.assignee.user if request.assignee else None

    send_email(
        text,
        "PR #%s: %s" % (request.id, request.title),
        ",".join(mail_to),
        mail_id=request.mail_id,
        project_name=request.project.fullname,
        user_from=request.user.fullname or request.user.user,
        reporter=request.user.user,
        assignee=assignee,
    )


def notify_merge_pull_request(request, user):
    """ Notify the people following a project that a pull-request was merged
    in it.
    """
    text = """
%s merged a pull-request against the project: `%s` that you are following.

Merged pull-request:

``
%s
``

%s
""" % (
        user.username,
        request.project.name,
        request.title,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(request.project.fullname),
            "pull-request",
            request.id,
        ),
    )
    mail_to = _get_emails_for_obj(request)

    uid = time.mktime(datetime.datetime.now().timetuple())

    assignee = request.assignee.user if request.assignee else None

    send_email(
        text,
        "PR #%s: %s" % (request.id, request.title),
        ",".join(mail_to),
        mail_id="%s/close/%s" % (request.mail_id, uid),
        in_reply_to=request.mail_id,
        project_name=request.project.fullname,
        user_from=user.fullname or user.user,
        reporter=request.user.user,
        assignee=assignee,
    )


def notify_reopen_pull_request(request, user):
    """ Notify the people following a project that a closed pull-request
    has been reopened.
    """
    text = """
%s reopened a pull-request against the project: `%s` that you are following.

Reopened pull-request:

``
%s
``

%s
""" % (
        user.username,
        request.project.name,
        request.title,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(request.project.fullname),
            "pull-request",
            request.id,
        ),
    )
    mail_to = _get_emails_for_obj(request)

    uid = time.mktime(datetime.datetime.now().timetuple())

    assignee = request.assignee.user if request.assignee else None

    send_email(
        text,
        "PR #%s: %s" % (request.id, request.title),
        ",".join(mail_to),
        mail_id="%s/close/%s" % (request.mail_id, uid),
        in_reply_to=request.mail_id,
        project_name=request.project.fullname,
        user_from=user.fullname or user.user,
        reporter=request.user.user,
        assignee=assignee,
    )


def notify_closed_pull_request(request, user):
    """ Notify the people following a project that a pull-request was
    closed in it.
    """
    text = """
%s closed without merging a pull-request against the project: `%s` that you
are following.

Closed pull-request:

``
%s
``

%s
""" % (
        user.username,
        request.project.name,
        request.title,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(request.project.fullname),
            "pull-request",
            request.id,
        ),
    )
    mail_to = _get_emails_for_obj(request)

    uid = time.mktime(datetime.datetime.now().timetuple())

    assignee = request.assignee.user if request.assignee else None

    send_email(
        text,
        "PR #%s: %s" % (request.id, request.title),
        ",".join(mail_to),
        mail_id="%s/close/%s" % (request.mail_id, uid),
        in_reply_to=request.mail_id,
        project_name=request.project.fullname,
        user_from=user.fullname or user.user,
        reporter=request.user.user,
        assignee=assignee,
    )


def notify_pull_request_comment(comment, user):
    """ Notify the people following a pull-request that a new comment was
    added to it.
    """
    text = """
%s commented on the pull-request: `%s` that you are following:
``
%s
``

%s
%s
""" % (
        comment.user.user,
        comment.pull_request.title,
        comment.comment,
        REPLY_MSG,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(comment.pull_request.project.fullname),
            "pull-request",
            comment.pull_request.id,
        ),
    )
    mail_to = _get_emails_for_obj(comment.pull_request)
    mail_to = _add_mentioned_users(mail_to, comment.comment)
    mail_to = _clean_emails(mail_to, user)

    assignee = (
        comment.pull_request.assignee.user
        if comment.pull_request.assignee
        else None
    )

    send_email(
        text,
        "PR #%s: %s" % (comment.pull_request.id, comment.pull_request.title),
        ",".join(mail_to),
        mail_id=comment.mail_id,
        in_reply_to=comment.pull_request.mail_id,
        project_name=comment.pull_request.project.fullname,
        user_from=comment.user.fullname or comment.user.user,
        reporter=comment.pull_request.user.user,
        assignee=assignee,
    )


def notify_pull_request_flag(flag, request, user):
    """ Notify the people following a pull-request that a new flag was
    added to it.
    """
    text = """
%s flagged the pull-request `%s` as %s: %s

%s
""" % (
        flag.username,
        request.title,
        flag.status,
        flag.comment,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(request.project.fullname),
            "pull-request",
            request.id,
        ),
    )
    mail_to = _get_emails_for_obj(request)

    assignee = request.assignee.user if request.assignee else None

    send_email(
        text,
        "PR #%s - %s: %s" % (request.id, flag.username, flag.status),
        ",".join(mail_to),
        mail_id=flag.mail_id,
        in_reply_to=request.mail_id,
        project_name=request.project.fullname,
        user_from=flag.username,
        reporter=request.user.user,
        assignee=assignee,
    )


def notify_new_email(email, user):
    """ Ask the user to confirm to the email belong to them.
    """

    root_url = pagure_config.get("APP_URL", flask.request.url_root)

    url = urljoin(
        root_url or flask.request.url_root,
        flask.url_for("ui_ns.confirm_email", token=email.token),
    )

    text = """Dear %(username)s,

You have registered a new email on pagure at %(root_url)s.

To finish your validate this registration, please click on the following
link or copy/paste it in your browser, this link will remain valid only 2 days:
  %(url)s

The email will not be activated until you finish this step.

Sincerely,
Your pagure admin.
""" % (
        {"username": user.username, "url": url, "root_url": root_url}
    )

    send_email(
        text,
        "Confirm new email",
        email.email,
        user_from=user.fullname or user.user,
    )


def notify_new_commits(abspath, project, branch, commits):
    """ Notify the people following a project's commits that new commits have
    been added.
    """
    # string note: abspath, project and branch can only contain ASCII
    # by policy (pagure and/or gitolite)
    commits_info = []
    for commit in commits:
        commits_info.append(
            {
                "commit": commit,
                "author": pagure.lib.git.get_author(commit, abspath),
                "subject": pagure.lib.git.get_commit_subject(commit, abspath),
            }
        )

    # make sure this is unicode
    commits_string = "\n".join(
        "{0}    {1}    {2}".format(
            commit_info["commit"],
            commit_info["author"],
            commit_info["subject"],
        )
        for commit_info in commits_info
    )
    commit_url = _build_url(
        pagure_config["APP_URL"],
        _fullname_to_url(project.fullname),
        "commits",
        branch,
    )

    email_body = """
The following commits were pushed to the repo %s on branch
%s, which you are following:
%s



To view more about the commits, visit:
%s
""" % (
        project.fullname,
        branch,
        commits_string,
        commit_url,
    )
    mail_to = _get_emails_for_commit_notification(project)

    send_email(
        email_body,
        'New Commits To "{0}" ({1})'.format(project.fullname, branch),
        ",".join(mail_to),
        project_name=project.fullname,
    )


def notify_commit_flag(flag, user):
    """ Notify the people following a project that a new flag was added
    to one of its commit.
    """
    text = """
%s flagged the commit `%s` as %s: %s

%s
""" % (
        flag.username,
        flag.commit_hash,
        flag.status,
        flag.comment,
        _build_url(
            pagure_config["APP_URL"],
            _fullname_to_url(flag.project.fullname),
            "c",
            flag.commit_hash,
        ),
    )
    mail_to = _get_emails_for_obj(flag)

    send_email(
        text,
        "Commit #%s - %s: %s" % (flag.commit_hash, flag.username, flag.status),
        ",".join(mail_to),
        mail_id=flag.mail_id,
        in_reply_to=flag.project.mail_id,
        project_name=flag.project.fullname,
        user_from=flag.username,
    )
