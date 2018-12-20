# -*- coding: utf-8 -*-

"""
 (c) 2018 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import hashlib
import hmac
import json
import os
import os.path
import time
import uuid

import requests
import six

from celery import Celery
from celery.signals import after_setup_task_logger
from celery.utils.log import get_task_logger
from kitchen.text.converters import to_bytes
from sqlalchemy.exc import SQLAlchemyError

import pagure.lib.query
from pagure.config import config as pagure_config
from pagure.lib.tasks_utils import pagure_task
from pagure.mail_logging import format_callstack
from pagure.lib.lib_ci import trigger_jenkins_build
from pagure.utils import split_project_fullname, set_up_logging

# logging.config.dictConfig(pagure_config.get('LOGGING') or {'version': 1})
_log = get_task_logger(__name__)
_i = 0


if os.environ.get("PAGURE_BROKER_URL"):  # pragma: no cover
    broker_url = os.environ["PAGURE_BROKER_URL"]
elif pagure_config.get("BROKER_URL"):
    broker_url = pagure_config["BROKER_URL"]
else:
    broker_url = "redis://%s" % pagure_config["REDIS_HOST"]

conn = Celery("tasks", broker=broker_url, backend=broker_url)
conn.conf.update(pagure_config["CELERY_CONFIG"])


@after_setup_task_logger.connect
def augment_celery_log(**kwargs):
    set_up_logging(force=True)


def call_web_hooks(project, topic, msg, urls):
    """ Sends the web-hook notification. """
    _log.info("Processing project: %s - topic: %s", project.fullname, topic)
    _log.debug("msg: %s", msg)

    # Send web-hooks notification
    global _i
    _i += 1
    year = datetime.datetime.utcnow().year
    if isinstance(topic, six.text_type):
        topic = to_bytes(topic, encoding="utf8", nonstring="passthru")
    msg["pagure_instance"] = pagure_config["APP_URL"]
    msg["project_fullname"] = project.fullname
    msg = dict(
        topic=topic.decode("utf-8"),
        msg=msg,
        timestamp=int(time.time()),
        msg_id="%s-%s" % (year, uuid.uuid4()),
        i=_i,
    )

    content = json.dumps(msg, sort_keys=True)
    hashhex = hmac.new(
        project.hook_token.encode("utf-8"),
        content.encode("utf-8"),
        hashlib.sha1,
    ).hexdigest()
    hashhex256 = hmac.new(
        project.hook_token.encode("utf-8"),
        content.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    headers = {
        "X-Pagure": pagure_config["APP_URL"],
        "X-Pagure-project": project.fullname,
        "X-Pagure-Signature": hashhex,
        "X-Pagure-Signature-256": hashhex256,
        "X-Pagure-Topic": topic,
        "Content-Type": "application/json",
    }
    for url in sorted(urls):
        url = url.strip()
        _log.info("Calling url %s" % url)
        try:
            req = requests.post(url, headers=headers, data=content, timeout=60)
            if not req:
                _log.info(
                    "An error occured while querying: %s - "
                    "Error code: %s" % (url, req.status_code)
                )
        except (requests.exceptions.RequestException, Exception) as err:
            _log.info(
                "An error occured while querying: %s - Error: %s" % (url, err)
            )


@conn.task(queue=pagure_config.get("WEBHOOK_CELERY_QUEUE", None), bind=True)
@pagure_task
def webhook_notification(
    self, session, topic, msg, namespace=None, name=None, user=None
):
    """ Send webhook notifications about an event on that project.

    :arg session: SQLAlchemy session object
    :type session: sqlalchemy.orm.session.Session
    :arg topic: the topic for the notification
    :type topic: str
    :arg msg: the message to send via web-hook
    :type msg: str
    :kwarg namespace: the namespace of the project
    :type namespace: None or str
    :kwarg name: the name of the project
    :type name: None or str
    :kwarg user: the user of the project, only set if the project is a fork
    :type user: None or str

    """
    project = pagure.lib.query._get_project(
        session, namespace=namespace, name=name, user=user
    )

    if not project:
        session.close()
        raise RuntimeError(
            "Project: %s/%s from user: %s not found in the DB"
            % (namespace, name, user)
        )

    urls = project.settings.get("Web-hooks")
    if not urls:
        _log.info("No URLs set: %s" % urls)
        return

    urls = urls.split("\n")
    _log.info("Got the project and urls, going to the webhooks")
    call_web_hooks(project, topic, msg, urls)


@conn.task(queue=pagure_config.get("LOGCOM_CELERY_QUEUE", None), bind=True)
@pagure_task
def log_commit_send_notifications(
    self,
    session,
    name,
    commits,
    abspath,
    branch,
    default_branch,
    namespace=None,
    username=None,
):
    """ Send webhook notifications about an event on that project.

    :arg session: SQLAlchemy session object
    :type session: sqlalchemy.orm.session.Session
    :arg topic: the topic for the notification
    :type topic: str
    :arg msg: the message to send via web-hook
    :type msg: str
    :kwarg namespace: the namespace of the project
    :type namespace: None or str
    :kwarg name: the name of the project
    :type name: None or str
    :kwarg user: the user of the project, only set if the project is a fork
    :type user: None or str

    """
    _log.info(
        "Looking for project: %s%s of %s",
        "%s/" % namespace if namespace else "",
        name,
        username,
    )
    project = pagure.lib.query._get_project(
        session, name, user=username, namespace=namespace
    )

    if not project:
        _log.info("No project found")
        return

    _log.info("Found project: %s", project.fullname)

    _log.info("Processing %s commits in %s", len(commits), abspath)

    # Only log commits when the branch is the default branch
    log_all = pagure_config.get("LOG_ALL_COMMITS", False)
    if log_all or branch == default_branch:
        pagure.lib.git.log_commits_to_db(session, project, commits, abspath)
    else:
        _log.info(
            "Not logging commits not made on the default branch: %s",
            default_branch,
        )

    # Notify subscribed users that there are new commits
    email_watchcommits = pagure_config.get("EMAIL_ON_WATCHCOMMITS", True)
    _log.info("Sending notification about the commit: %s", email_watchcommits)
    if email_watchcommits:
        pagure.lib.notify.notify_new_commits(abspath, project, branch, commits)

    try:
        session.commit()
    except SQLAlchemyError as err:  # pragma: no cover
        _log.exception(err)
        session.rollback()


def get_files_to_load(title, new_commits_list, abspath):

    _log.info("%s: Retrieve the list of files changed" % title)
    file_list = []
    new_commits_list.reverse()
    n = len(new_commits_list)
    for idx, commit in enumerate(new_commits_list):
        if (idx % 100) == 0:
            _log.info(
                "Loading files change in commits for %s: %s/%s", title, idx, n
            )
        if commit == new_commits_list[0]:
            filenames = pagure.lib.git.read_git_lines(
                [
                    "diff-tree",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    "--root",
                    commit,
                ],
                abspath,
            )
        else:
            filenames = pagure.lib.git.read_git_lines(
                ["diff-tree", "--no-commit-id", "--name-only", "-r", commit],
                abspath,
            )
        for line in filenames:
            if line.strip():
                file_list.append(line.strip())

    return file_list


@conn.task(queue=pagure_config.get("LOADJSON_CELERY_QUEUE", None), bind=True)
@pagure_task
def load_json_commits_to_db(
    self,
    session,
    name,
    commits,
    abspath,
    data_type,
    agent,
    namespace=None,
    username=None,
):
    """ Loads into the database the specified commits that have been pushed
    to either the tickets or the pull-request repository.

    """

    if data_type not in ["ticket", "pull-request"]:
        _log.info("LOADJSON: Invalid data_type retrieved: %s", data_type)
        return

    _log.info(
        "LOADJSON: Looking for project: %s%s of user: %s",
        "%s/" % namespace if namespace else "",
        name,
        username,
    )

    project = pagure.lib.query._get_project(
        session, name, user=username, namespace=namespace
    )

    if not project:
        _log.info("LOADJSON: No project found")
        return

    _log.info("LOADJSON: Found project: %s", project.fullname)

    _log.info(
        "LOADJSON: %s: Processing %s commits in %s",
        project.fullname,
        len(commits),
        abspath,
    )

    file_list = set(get_files_to_load(project.fullname, commits, abspath))
    n = len(file_list)
    _log.info("LOADJSON: %s files to process" % n)
    mail_body = []

    for idx, filename in enumerate(sorted(file_list)):
        _log.info(
            "LOADJSON: Loading: %s: %s -- %s/%s",
            project.fullname,
            filename,
            idx + 1,
            n,
        )
        tmp = "Loading: %s -- %s/%s" % (filename, idx + 1, n)
        try:
            json_data = None
            data = "".join(
                pagure.lib.git.read_git_lines(
                    ["show", "HEAD:%s" % filename], abspath
                )
            )
            if data and not filename.startswith("files/"):
                try:
                    json_data = json.loads(data)
                except ValueError:
                    pass
            if json_data:
                if data_type == "ticket":
                    pagure.lib.git.update_ticket_from_git(
                        session,
                        reponame=name,
                        namespace=namespace,
                        username=username,
                        issue_uid=filename,
                        json_data=json_data,
                        agent=agent,
                    )
                elif data_type == "pull-request":
                    pagure.lib.git.update_request_from_git(
                        session,
                        reponame=name,
                        namespace=namespace,
                        username=username,
                        request_uid=filename,
                        json_data=json_data,
                    )
                tmp += " ... ... Done"
            else:
                tmp += " ... ... SKIPPED - No JSON data"
                mail_body.append(tmp)
        except Exception as err:
            _log.info("data: %s", json_data)
            session.rollback()
            _log.exception(err)
            tmp += " ... ... FAILED\n"
            tmp += format_callstack()
            break
        finally:
            mail_body.append(tmp)

    try:
        session.commit()
        _log.info(
            "LOADJSON: Emailing results for %s to %s", project.fullname, agent
        )
        try:
            if not agent:
                raise pagure.exceptions.PagureException(
                    "No agent found: %s" % agent
                )
            if agent != "pagure":
                user_obj = pagure.lib.query.get_user(session, agent)
                pagure.lib.notify.send_email(
                    "\n".join(mail_body),
                    "Issue import report",
                    user_obj.default_email,
                )
        except pagure.exceptions.PagureException:
            _log.exception("LOADJSON: Could not find user %s" % agent)
    except SQLAlchemyError:  # pragma: no cover
        session.rollback()
    _log.info("LOADJSON: Ready for another")


@conn.task(queue=pagure_config.get("CI_CELERY_QUEUE", None), bind=True)
@pagure_task
def trigger_ci_build(
    self, session, cause, branch, ci_type, project_name=None, pr_uid=None
):

    """ Triggers a new run of the CI system on the specified pull-request.

    """
    pagure.lib.plugins.get_plugin("Pagure CI")

    if not pr_uid and not project_name:
        _log.debug("No PR UID nor project name specified, can't trigger CI")
        session.close()
        return

    if pr_uid:
        pr = pagure.lib.query.get_request_by_uid(session, pr_uid)
        if pr.remote:
            project_name = pr.project_to.fullname
        else:
            project_name = pr.project_from.fullname

    user, namespace, project_name = split_project_fullname(project_name)

    _log.info("Pagure-CI: Looking for project: %s", project_name)
    project = pagure.lib.query.get_authorized_project(
        session=session,
        project_name=project_name,
        user=user,
        namespace=namespace,
    )

    if project is None:
        _log.warning(
            "Pagure-CI: No project could be found for the name %s",
            project_name,
        )
        session.close()
        return

    if project.is_fork:
        if (
            project.parent.ci_hook is None
            or project.parent.ci_hook.ci_url is None
        ):
            raise pagure.exceptions.PagureException(
                "Project %s not configured or incorectly configured for ci",
                project.parent.fullname,
            )
    elif project.ci_hook is None or project.ci_hook.ci_url is None:
        raise pagure.exceptions.PagureException(
            "Project %s not configured or incorectly configured for ci",
            project.fullname,
        )

    _log.info("Pagure-CI: project retrieved: %s", project.fullname)

    _log.info(
        "Pagure-CI: Trigger from %s cause (PR# or commit) %s branch: %s",
        project.fullname,
        cause,
        branch,
    )

    if ci_type == "jenkins":

        if project.is_fork:
            url = project.parent.ci_hook.ci_url
            job = project.parent.ci_hook.ci_job
            token = project.parent.ci_hook.pagure_ci_token
        else:
            url = project.ci_hook.ci_url
            job = project.ci_hook.ci_job
            token = project.ci_hook.pagure_ci_token

        trigger_jenkins_build(
            project_path=project.path,
            url=url,
            job=job,
            token=token,
            branch=branch,
            cause=cause,
        )

    else:
        _log.warning("Pagure-CI:Un-supported CI type")

    _log.info("Pagure-CI: Ready for another")
