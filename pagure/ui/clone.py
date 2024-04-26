# -*- coding: utf-8 -*-

"""
 (c) 2014-2018 - Copyright Red Hat Inc

 Authors:
   Patrick Uiterwijk <puiterwijk@redhat.com>

"""

from __future__ import absolute_import, unicode_literals

import base64
import logging
import os
import subprocess
import tempfile

import flask
import werkzeug.wsgi

import pagure.exceptions
import pagure.forms
import pagure.lib.git
import pagure.lib.mimetype
import pagure.lib.plugins
import pagure.lib.query
import pagure.lib.tasks
import pagure.ui.plugins
from pagure.config import config as pagure_config
from pagure.ui import UI_NS

_log = logging.getLogger(__name__)
_auth_log = logging.getLogger("pagure_auth")


def _get_remote_user(project):
    """Returns the remote user using either the content of
    ``flask.g.remote_user`` or checking the headers for ``Authorization``
    and check if the provided API token is valid.
    """
    remote_user = flask.request.remote_user

    if not remote_user:
        # Check the headers
        if "Authorization" in flask.request.headers:
            auth = flask.request.headers["Authorization"]
            if "Basic" in auth:
                auth_token = auth.split("Basic ", 1)[-1]
                info = base64.b64decode(auth_token).decode("utf-8")
                if ":" in info:
                    username, token_str = info.split(":")
                    auth = pagure_config.get("PAGURE_AUTH", None)
                    if auth == "local":
                        import pagure.lib.login

                        try:
                            pagure.lib.login.check_username_and_password(
                                flask.g.session, username, token_str
                            )
                        except pagure.exceptions.PagureException as ex:
                            _log.exception(ex)
                        else:
                            remote_user = username

                    # We're doing a second check here, if the user/password
                    # approach above didn't work, the user may still be
                    # using an API token, so we want to check that as well.
                    if not remote_user:
                        import pagure.lib.query

                        token = pagure.lib.query.get_api_token(
                            flask.g.session, token_str
                        )
                        if token:
                            if (
                                not token.expired
                                and username == token.user.username
                                and "commit" in token.acls_list
                            ):
                                if (
                                    project
                                    and token.project
                                    and token.project.fullname
                                    != project.fullname
                                ):
                                    return remote_user

                                flask.g.authenticated = True
                                remote_user = token.user.username

    return remote_user


def proxy_raw_git(project):
    """Proxy a request to Git via a subprocess."""
    _log.debug("Raw git clone proxy started")
    remote_user = _get_remote_user(project)
    # We are going to shell out, prepare the env it needs.
    gitenv = {
        "PATH": os.environ["PATH"],
        # These are the vars git-http-backend needs
        "PATH_INFO": flask.request.path,
        "REMOTE_USER": remote_user,
        "USER": remote_user,
        "REMOTE_ADDR": flask.request.remote_addr,
        "CONTENT_TYPE": flask.request.content_type,
        "QUERY_STRING": flask.request.query_string,
        "REQUEST_METHOD": flask.request.method,
        "GIT_PROJECT_ROOT": pagure_config["GIT_FOLDER"],
        # We perform access checks, so can bypass that of Git
        "GIT_HTTP_EXPORT_ALL": "true",
        # This might be needed by hooks
        "PAGURE_CONFIG": os.environ.get("PAGURE_CONFIG"),
        "PYTHONPATH": os.environ.get("PYTHONPATH"),
        # Some HTTP headers that we want to pass through because they
        # impact the request/response. Only add headers here that are
        # "safe", as in they don't allow for other issues.
        "HTTP_CONTENT_ENCODING": flask.request.content_encoding,
    }

    _auth_log.info(
        "Serving git to |user: %s|IP: %s|method: %s|repo: %s|query: %s"
        % (
            remote_user,
            flask.request.remote_addr,
            flask.request.method,
            project.path,
            flask.request.query_string,
        )
    )

    if remote_user:
        gitenv.update({"GL_USER": remote_user})

    # These keys are optional
    for key in (
        "REMOTE_USER",
        "USER",
        "REMOTE_ADDR",
        "CONTENT_TYPE",
        "QUERY_STRING",
        "PYTHONPATH",
        "PATH",
        "HTTP_CONTENT_ENCODING",
    ):
        if not gitenv[key]:
            del gitenv[key]

    for key in gitenv:
        if not gitenv[key]:
            raise ValueError("Value for key %s unknown" % key)

    _log.debug("Running git via git directly")
    cmd = ["/usr/bin/git", "http-backend"]

    # Note: using a temporary files to buffer the input contents
    # is non-ideal, but it is a way to make sure we don't need to have
    # the full input (which can be very long) in memory.
    # Ideally, we'd directly stream, but that's an RFE for the future,
    # since that needs to happen in other threads so as to not block.
    # (See the warnings in the subprocess module)
    with tempfile.SpooledTemporaryFile() as infile:
        while True:
            block = flask.request.stream.read(4096)
            if not block:
                break
            infile.write(block)
        infile.seek(0)

        _log.debug("Calling: %s", cmd)
        proc = subprocess.Popen(
            cmd, stdin=infile, stdout=subprocess.PIPE, stderr=None, env=gitenv
        )

        out = proc.stdout

        # First, gather the response head
        headers = {}
        while True:
            line = out.readline()
            if not line:
                raise Exception("End of file while reading headers?")
            # This strips the \n, meaning end-of-headers
            line = line.strip()
            if not line:
                break
            header = line.split(b": ", 1)
            header[0] = header[0].decode("utf-8")
            headers[str(header[0].lower())] = header[1]

        if len(headers) == 0:
            raise Exception("No response at all received")

        if "status" not in headers:
            # If no status provided, assume 200 OK as per RFC3875
            headers[str("status")] = "200 OK"

        respcode, respmsg = headers.pop("status").split(" ", 1)
        wrapout = werkzeug.wsgi.wrap_file(flask.request.environ, out)
        return flask.Response(
            wrapout,
            status=int(respcode),
            headers=headers,
            direct_passthrough=True,
        )


def clone_proxy(project, username=None, namespace=None):
    """Proxy the /info/refs endpoint for HTTP pull/push.

    Note that for the clone endpoints, it's very explicit that <repo> has been
    renamed to <project>, to avoid the automatic repo searching from flask_app.
    This means that we have a chance to trust REMOTE_USER to verify the users'
    access to the attempted repository.
    """
    if not pagure_config["ALLOW_HTTP_PULL_PUSH"]:
        _auth_log.info(
            "User tried to access the git repo via http but this is not "
            "enabled -- |user: N/A|IP: %s|method: %s|repo: %s|query: %s"
            % (
                flask.request.remote_addr,
                flask.request.method,
                project,
                flask.request.query_string,
            )
        )
        flask.abort(403, description="HTTP pull/push is not allowed")

    service = None
    # name it p1 so there is no risk of variable shadowing, we do not want
    # this to be used elsewhere since there is no check here if the user
    # is allowed to access this project (this is done lower down)
    p1 = pagure.lib.query.get_authorized_project(
        flask.g.session, project, user=username, namespace=namespace
    )
    p1_path = "invalid repo: %s/%s/%s" % (username, namespace, project)
    if p1:
        p1_path = p1.path
    remote_user = _get_remote_user(p1)

    if flask.request.path.endswith("/info/refs"):
        service = flask.request.args.get("service")
        if not service:
            # This is a Git client older than 1.6.6, and it doesn't work with
            # the smart protocol. We do not support the old protocol via HTTP.
            _auth_log.info(
                "User is using a git client to old (pre-1.6.6) -- "
                "|user: %s|IP: %s|method: %s|repo: %s|query: %s"
                % (
                    remote_user,
                    flask.request.remote_addr,
                    flask.request.method,
                    p1_path,
                    flask.request.query_string,
                )
            )
            flask.abort(400, description="Please switch to newer Git client")
        if service not in ("git-upload-pack", "git-receive-pack"):
            _auth_log.info(
                "User asked for an unknown service "
                "|user: %s|IP: %s|method: %s|repo: %s|query: %s"
                % (
                    remote_user,
                    flask.request.remote_addr,
                    flask.request.method,
                    p1_path,
                    flask.request.query_string,
                )
            )
            flask.abort(400, description="Unknown service requested")

    if "git-receive-pack" in flask.request.full_path:
        if not pagure_config["ALLOW_HTTP_PUSH"]:
            _auth_log.info(
                "User tried a git push over http while this is not enabled -- "
                "|user: %s|IP: %s|method: %s|repo: %s|query: %s"
                % (
                    remote_user,
                    flask.request.remote_addr,
                    flask.request.method,
                    p1_path,
                    flask.request.query_string,
                )
            )
            # Pushing (git-receive-pack) over HTTP is not allowed
            flask.abort(403, description="HTTP pushing disabled")

        if not remote_user:
            # Anonymous pushing... nope
            realm = "Pagure API token"
            if pagure_config.get("PAGURE_AUTH") == "local":
                realm = "Pagure password or API token"
            headers = {
                "WWW-Authenticate": 'Basic realm="%s"' % realm,
                "X-Frame-Options": "DENY",
            }
            _auth_log.info(
                "User tried a git push over http but was not authenticated -- "
                "|user: %s|IP: %s|method: %s|repo: %s|query: %s"
                % (
                    remote_user,
                    flask.request.remote_addr,
                    flask.request.method,
                    p1_path,
                    flask.request.query_string,
                )
            )
            response = flask.Response(
                response="Authorization Required",
                status=401,
                headers=headers,
                content_type="text/plain",
            )
            flask.abort(response)

    project_obj = pagure.lib.query.get_authorized_project(
        flask.g.session,
        project,
        user=username,
        namespace=namespace,
        asuser=remote_user,
    )
    if not project_obj:
        _auth_log.info(
            "User asked to access a git repo that they are not allowed to "
            "access -- |user: %s|IP: %s|method: %s|repo: %s|query: %s"
            % (
                remote_user,
                flask.request.remote_addr,
                flask.request.method,
                p1_path,
                flask.request.query_string,
            )
        )
        _log.info(
            "%s could not find project: %s for user %s and namespace %s",
            remote_user,
            project,
            username,
            namespace,
        )
        flask.abort(404, description="Project not found")

    return proxy_raw_git(project_obj)


def add_clone_proxy_cmds():
    """This function adds flask routes for all possible clone paths.

    This comes down to:
    /(fork/<username>/)(<namespace>/)<project>(.git)
    with an operation following, where operation is one of:
    - /info/refs (generic)
    - /git-upload-pack (pull)
    - /git-receive-pack (push)
    """
    for prefix in (
        "<project>",
        "<namespace>/<project>",
        "forks/<username>/<project>",
        "forks/<username>/<namespace>/<project>",
    ):
        for suffix in ("", ".git"):
            for oper in ("info/refs", "git-receive-pack", "git-upload-pack"):
                route = "/%s%s/%s" % (prefix, suffix, oper)
                methods = ("GET",) if oper == "info/refs" else ("POST",)
                UI_NS.add_url_rule(
                    route, view_func=clone_proxy, methods=methods
                )
