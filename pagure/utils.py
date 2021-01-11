# -*- coding: utf-8 -*-

"""
 (c) 2017-2020 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

from __future__ import unicode_literals, absolute_import

import datetime
import fnmatch
import logging
import logging.config
import os
import re
from six.moves.urllib.parse import urlparse, urljoin
from functools import wraps

import flask
import pygit2
import six
import werkzeug.utils

from pagure.exceptions import (
    PagureException,
    InvalidTimestampException,
    InvalidDateformatException,
)
from pagure.config import config as pagure_config


_log = logging.getLogger(__name__)
LOGGER_SETUP = False


def set_up_logging(app=None, force=False, configkey="LOGGING"):
    global LOGGER_SETUP
    if LOGGER_SETUP and not force:
        _log.info("logging already setup")
        return

    logging.basicConfig()
    logging.config.dictConfig(pagure_config.get(configkey) or {"version": 1})

    LOGGER_SETUP = True


def authenticated():
    """Utility function checking if the current user is logged in or not."""
    fas_user = None
    try:
        fas_user = flask.g.fas_user
    except (RuntimeError, AttributeError):
        pass

    return fas_user is not None


def api_authenticated():
    """Utility function checking if the current user is logged in or not
    in the API.
    """
    return (
        hasattr(flask.g, "fas_user")
        and flask.g.fas_user is not None
        and hasattr(flask.g, "token")
        and flask.g.token is not None
    )


def check_api_acls(acls, optional=False):
    """Checks if the user provided an API token with its request and if
    this token allows the user to access the endpoint desired.

    :arg acls: A list of access control
    :arg optional: Only check the API token is valid. Skip the ACL validation.
    """
    import pagure.api
    import pagure.lib.query

    if authenticated():
        return

    flask.g.token = None
    flask.g.fas_user = None
    token = None
    token_str = None

    if "Authorization" in flask.request.headers:
        authorization = flask.request.headers["Authorization"]
        if "token" in authorization:
            token_str = authorization.split("token", 1)[1].strip()

    token_auth = False
    error_msg = None
    if token_str:
        token = pagure.lib.query.get_api_token(flask.g.session, token_str)
        if token:
            if token.expired:
                error_msg = "Expired token"
            else:
                flask.g.authenticated = True

                # Some ACLs are required
                if acls:
                    token_acls_set = set(token.acls_list)
                    needed_acls_set = set(acls or [])
                    overlap = token_acls_set.intersection(needed_acls_set)
                    # Our token has some of the required ACLs:  auth successful
                    if overlap:
                        token_auth = True
                        flask.g.fas_user = token.user
                        # To get a token, in the `fas` auth user must have
                        # signed the CLA, so just set it to True
                        flask.g.fas_user.cla_done = True
                        flask.g.token = token
                        flask.g.authenticated = True
                    # Our token has none of the required ACLs -> auth fail
                    else:
                        error_msg = "Missing ACLs: %s" % ", ".join(
                            sorted(set(acls) - set(token.acls_list))
                        )
                # No ACL required
                else:
                    if optional:
                        token_auth = True
                        flask.g.fas_user = token.user
                        # To get a token, in the `fas` auth user must have
                        # signed the CLA, so just set it to True
                        flask.g.fas_user.cla_done = True
                        flask.g.token = token
                        flask.g.authenticated = True
        else:
            error_msg = "Invalid token"

    elif optional:
        return

    else:
        error_msg = "Invalid token"

    if not token_auth:
        output = {
            "error_code": pagure.api.APIERROR.EINVALIDTOK.name,
            "error": pagure.api.APIERROR.EINVALIDTOK.value,
            "errors": error_msg,
        }
        jsonout = flask.jsonify(output)
        jsonout.status_code = 401
        return jsonout


def is_safe_url(target):  # pragma: no cover
    """Checks that the target url is safe and sending to the current
    website not some other malicious one.
    """
    ref_url = urlparse(flask.request.host_url)
    test_url = urlparse(urljoin(flask.request.host_url, target))
    return (
        test_url.scheme in ("http", "https")
        and ref_url.netloc == test_url.netloc
    )


def is_admin():
    """ Return whether the user is admin for this application or not. """
    if not authenticated():
        return False

    user = flask.g.fas_user

    auth_method = pagure_config.get("PAGURE_AUTH", None)
    if auth_method == "fas":
        if not user.cla_done:
            return False

    admin_users = pagure_config.get("PAGURE_ADMIN_USERS", [])
    if not isinstance(admin_users, list):
        admin_users = [admin_users]
    if user.username in admin_users:
        return True

    admins = pagure_config["ADMIN_GROUP"]
    if not isinstance(admins, list):
        admins = [admins]
    admins = set(admins or [])
    groups = set(flask.g.fas_user.groups)

    return not groups.isdisjoint(admins)


def is_repo_admin(repo_obj, username=None):
    """ Return whether the user is an admin of the provided repo. """
    if not authenticated():
        return False

    if username:
        user = username
    else:
        user = flask.g.fas_user.username

    if is_admin():
        return True

    usergrps = [usr.user for grp in repo_obj.admin_groups for usr in grp.users]

    return (
        user == repo_obj.user.user
        or (user in [usr.user for usr in repo_obj.admins])
        or (user in usergrps)
    )


def is_repo_committer(repo_obj, username=None, session=None):
    """ Return whether the user is a committer of the provided repo. """
    import pagure.lib.query

    usergroups = set()
    if username is None:
        if not authenticated():
            return False
        if is_admin():
            return True
        username = flask.g.fas_user.username
        usergroups = set(flask.g.fas_user.groups)

    if not session:
        session = flask.g.session
    try:
        user = pagure.lib.query.get_user(session, username)
        usergroups = usergroups.union(set(user.groups))
    except pagure.exceptions.PagureException:
        return False

    # If the user is main admin -> yep
    if repo_obj.user.user == username:
        return True

    # If they are in the list of committers -> yep
    for user in repo_obj.committers:
        if user.user == username:
            return True

    # If they are in a group that has commit access -> yep
    for group in repo_obj.committer_groups:
        if group.group_name in usergroups:
            return True

    # If no direct committer, check EXTERNAL_COMMITTER info
    ext_committer = pagure_config.get("EXTERNAL_COMMITTER", None)
    if ext_committer:
        overlap = set(ext_committer) & usergroups
        if overlap:
            for grp in overlap:
                restrict = ext_committer[grp].get("restrict", [])
                exclude = ext_committer[grp].get("exclude", [])
                if restrict and repo_obj.fullname not in restrict:
                    continue
                elif repo_obj.fullname in exclude:
                    continue
                else:
                    return True

    # The user is not in an external_committer group that grants access, and
    # not a direct committer -> You have no power here
    return False


def is_repo_collaborator(repo_obj, refname, username=None, session=None):
    """Return whether the user has commit on the specified branch of the
    provided repo."""
    committer = is_repo_committer(repo_obj, username=username, session=session)
    if committer:
        _log.debug("User is a committer")
        return committer

    import pagure.lib.query

    if username is None:
        if not authenticated():
            return False
        if is_admin():
            return True
        username = flask.g.fas_user.username
        usergroups = set(flask.g.fas_user.groups)

    if not session:
        session = flask.g.session
    try:
        user = pagure.lib.query.get_user(session, username)
        usergroups = set(user.groups)
    except pagure.exceptions.PagureException:
        return False

    # If they are in the list of committers -> maybe
    for user in repo_obj.collaborators:
        if user.user.username == username:
            # if branch is None when the user tries to read,
            # so we'll allow that
            if refname is None:
                return True
            # If the branch is specified: the user is trying to write, we'll
            # check if they are allowed to
            for pattern in user.branches.split(","):
                pattern = "refs/heads/{}".format(pattern.strip())
                if fnmatch.fnmatch(refname, pattern):
                    return True

    # If they are in a group that has commit access -> maybe
    for project_group in repo_obj.collaborator_project_groups:
        if project_group.group.group_name in usergroups:
            # if branch is None when the user tries to read,
            # so we'll allow that
            if refname is None:
                return True
            # If the branch is specified: the user is trying to write, we'll
            # check if they are allowed to
            for pattern in project_group.branches.split(","):
                pattern = "refs/heads/{}".format(pattern.strip())
                if fnmatch.fnmatch(refname, pattern):
                    return True

    return False


def is_repo_user(repo_obj, username=None):
    """ Return whether the user has some access in the provided repo. """
    if username:
        user = username
    else:
        if not authenticated():
            return False
        user = flask.g.fas_user.username

    if is_admin():
        return True

    usergrps = [usr.user for grp in repo_obj.groups for usr in grp.users]

    return (
        user == repo_obj.user.user
        or (user in [usr.user for usr in repo_obj.users])
        or (user in usergrps)
    )


def get_user_repo_access(repo_obj, username):
    """return a string of the highest level of access
    a user has on a repo.
    """
    if repo_obj.user.username == username:
        return "main admin"

    if is_repo_admin(repo_obj, username):
        return "admin"

    if is_repo_committer(repo_obj, username):
        return "commit"

    if is_repo_user(repo_obj, username):
        return "ticket"

    return None


def login_required(function):
    """Flask decorator to retrict access to logged in user.
    If the auth system is ``fas`` it will also require that the user sign
    the FPCA.
    """

    @wraps(function)
    def decorated_function(*args, **kwargs):
        """ Decorated function, actually does the work. """
        auth_method = pagure_config.get("PAGURE_AUTH", None)
        if flask.session.get("_justloggedout", False):
            return flask.redirect(flask.url_for("ui_ns.index"))
        elif not authenticated():
            return flask.redirect(
                flask.url_for("auth_login", next=flask.request.url)
            )
        elif auth_method == "fas" and not flask.g.fas_user.cla_done:
            flask.session["_requires_fpca"] = True
            flask.flash(
                flask.Markup(
                    'You must <a href="https://admin.fedoraproject'
                    '.org/accounts/">sign the FPCA</a> (Fedora Project '
                    "Contributor Agreement) to use pagure"
                ),
                "errors",
            )
            return flask.redirect(flask.url_for("ui_ns.index"))
        return function(*args, **kwargs)

    return decorated_function


def __get_file_in_tree(repo_obj, tree, filepath, bail_on_tree=False):
    """Retrieve the entry corresponding to the provided filename in a
    given tree.
    """

    filename = filepath[0]
    if isinstance(tree, pygit2.Blob):
        return
    for entry in tree:
        fname = entry.name
        if six.PY2:
            fname = entry.name.decode("utf-8")
        if fname == filename:
            if len(filepath) == 1:
                blob = repo_obj.get(entry.id)
                # If we can't get the content (for example: an empty folder)
                if blob is None:
                    return
                # If we get a tree instead of a blob, let's escape
                if isinstance(blob, pygit2.Tree) and bail_on_tree:
                    return blob
                content = blob.data
                # If it's a (sane) symlink, we try a single-level dereference
                if (
                    entry.filemode == pygit2.GIT_FILEMODE_LINK
                    and os.path.normpath(content) == content
                    and not os.path.isabs(content)
                ):
                    try:
                        dereferenced = tree[content]
                    except KeyError:
                        pass
                    else:
                        if dereferenced.filemode == pygit2.GIT_FILEMODE_BLOB:
                            blob = repo_obj[dereferenced.oid]

                return blob
            else:
                try:
                    nextitem = repo_obj[entry.oid]
                except KeyError:
                    # We could not find the blob/entry in the git repo
                    # so we bail
                    return
                # If we can't get the content (for example: an empty folder)
                if nextitem is None:
                    return
                return __get_file_in_tree(
                    repo_obj, nextitem, filepath[1:], bail_on_tree=bail_on_tree
                )


ip_middle_octet = r"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5]))"
ip_last_octet = r"(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))"

"""
regex based on https://github.com/kvesteri/validators/blob/
master/validators/url.py
LICENSED on Dec 16th 2016 as MIT:

The MIT License (MIT)

Copyright (c) 2013-2014 Konsta Vesterinen

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.

"""
urlregex = re.compile(
    "^"
    # protocol identifier
    r"(?:(?:https?|ftp|git)://)"
    # user:pass authentication
    "(?:[-a-z\u00a1-\uffff0-9._~%!$&'()*+,;=:]+"
    "(?::[-a-z0-9._~%!$&'()*+,;=:]*)?@)?"
    "(?:"
    "(?P<private_ip>"
    # IP address exclusion
    # private & local networks
    "(?:(?:10|127)" + ip_middle_octet + "{2}" + ip_last_octet + ")|"
    r"(?:(?:169\.254|192\.168)" + ip_middle_octet + ip_last_octet + ")|"
    r"(?:172\.(?:1[6-9]|2\d|3[0-1])" + ip_middle_octet + ip_last_octet + "))"
    "|"
    # private & local hosts
    "(?P<private_host>" "(?:localhost))" "|"
    # IP address dotted notation octets
    # excludes loopback network 0.0.0.0
    # excludes reserved space >= 224.0.0.0
    # excludes network & broadcast addresses
    # (first & last IP address of each class)
    "(?P<public_ip>"
    r"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
    "" + ip_middle_octet + "{2}"
    "" + ip_last_octet + ")"
    "|"
    # IPv6 RegEx from https://stackoverflow.com/a/17871737
    r"\[("
    # 1:2:3:4:5:6:7:8
    "([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|"
    # 1::                              1:2:3:4:5:6:7::
    "([0-9a-fA-F]{1,4}:){1,7}:|"
    # 1::8             1:2:3:4:5:6::8  1:2:3:4:5:6::8
    "([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|"
    # 1::7:8           1:2:3:4:5::7:8  1:2:3:4:5::8
    "([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|"
    # 1::6:7:8         1:2:3:4::6:7:8  1:2:3:4::8
    "([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|"
    # 1::5:6:7:8       1:2:3::5:6:7:8  1:2:3::8
    "([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|"
    # 1::4:5:6:7:8     1:2::4:5:6:7:8  1:2::8
    "([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|"
    # 1::3:4:5:6:7:8   1::3:4:5:6:7:8  1::8
    "[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|"
    # ::2:3:4:5:6:7:8  ::2:3:4:5:6:7:8 ::8       ::
    ":((:[0-9a-fA-F]{1,4}){1,7}|:)|"
    # fe80::7:8%eth0   fe80::7:8%1
    # (link-local IPv6 addresses with zone index)
    "fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|"
    "::(ffff(:0{1,4}){0,1}:){0,1}"
    r"((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}"
    # ::255.255.255.255   ::ffff:255.255.255.255  ::ffff:0:255.255.255.255
    # (IPv4-mapped IPv6 addresses and IPv4-translated addresses)
    "(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|"
    "([0-9a-fA-F]{1,4}:){1,4}:"
    r"((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}"
    # 2001:db8:3:4::192.0.2.33  64:ff9b::192.0.2.33
    # (IPv4-Embedded IPv6 Address)
    "(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])" r")\]|"
    # host name
    "(?:(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)"
    # domain name
    r"(?:\.(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)*"
    # TLD identifier
    r"(?:\.(?:[a-z\u00a1-\uffff]{2,}))" ")"
    # port number
    r"(?::\d{2,5})?"
    # resource path
    r"(?:/[-a-z\u00a1-\uffff0-9._~%!$&'()*+,;=:@/]*)?"
    # query string
    r"(?:\?\S*)?"
    # fragment
    r"(?:#\S*)?" "$",
    re.UNICODE | re.IGNORECASE,
)
urlpattern = re.compile(urlregex)


ssh_urlregex = re.compile(
    "^"
    # protocol identifier
    r"(?:(?:ssh|git\+ssh)://)?"
    # user@ authentication
    "[-a-z\u00a1-\uffff0-9._~%!$&'()*+,;=:]+@"
    # Opening section about host
    "(?:"
    # IP address exclusion
    "(?P<private_ip>"
    # private & local networks
    "(?:(?:10|127)" + ip_middle_octet + "{2}" + ip_last_octet + ")|"
    r"(?:(?:169\.254|192\.168)" + ip_middle_octet + ip_last_octet + ")|"
    r"(?:172\.(?:1[6-9]|2\d|3[0-1])" + ip_middle_octet + ip_last_octet + "))"
    "|"
    # private & local hosts
    "(?P<private_host>" "(?:localhost))" "|"
    # IP address dotted notation octets
    # excludes loopback network 0.0.0.0
    # excludes reserved space >= 224.0.0.0
    # excludes network & broadcast addresses
    # (first & last IP address of each class)
    "(?P<public_ip>"
    r"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
    "" + ip_middle_octet + "{2}"
    "" + ip_last_octet + ")"
    "|"
    # IPv6 RegEx from https://stackoverflow.com/a/17871737
    r"\[("
    # 1:2:3:4:5:6:7:8
    "([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|"
    # 1::                              1:2:3:4:5:6:7::
    "([0-9a-fA-F]{1,4}:){1,7}:|"
    # 1::8             1:2:3:4:5:6::8  1:2:3:4:5:6::8
    "([0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|"
    # 1::7:8           1:2:3:4:5::7:8  1:2:3:4:5::8
    "([0-9a-fA-F]{1,4}:){1,5}(:[0-9a-fA-F]{1,4}){1,2}|"
    # 1::6:7:8         1:2:3:4::6:7:8  1:2:3:4::8
    "([0-9a-fA-F]{1,4}:){1,4}(:[0-9a-fA-F]{1,4}){1,3}|"
    # 1::5:6:7:8       1:2:3::5:6:7:8  1:2:3::8
    "([0-9a-fA-F]{1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|"
    # 1::4:5:6:7:8     1:2::4:5:6:7:8  1:2::8
    "([0-9a-fA-F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|"
    # 1::3:4:5:6:7:8   1::3:4:5:6:7:8  1::8
    "[0-9a-fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|"
    # ::2:3:4:5:6:7:8  ::2:3:4:5:6:7:8 ::8       ::
    ":((:[0-9a-fA-F]{1,4}){1,7}|:)|"
    # fe80::7:8%eth0   fe80::7:8%1
    # (link-local IPv6 addresses with zone index)
    "fe80:(:[0-9a-fA-F]{0,4}){0,4}%[0-9a-zA-Z]{1,}|"
    "::(ffff(:0{1,4}){0,1}:){0,1}"
    r"((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}"
    # ::255.255.255.255   ::ffff:255.255.255.255  ::ffff:0:255.255.255.255
    # (IPv4-mapped IPv6 addresses and IPv4-translated addresses)
    "(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])|"
    "([0-9a-fA-F]{1,4}:){1,4}:"
    r"((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])\.){3,3}"
    # 2001:db8:3:4::192.0.2.33  64:ff9b::192.0.2.33
    # (IPv4-Embedded IPv6 Address)
    r"(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9])" r")\]|"
    # host name
    r"(?:(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)"
    # domain name
    r"(?:\.(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)*"
    # TLD identifier
    r"(?:\.(?:[a-z\u00a1-\uffff]{2,}))"
    # Closing the entire section about host
    ")"
    # port number
    r"(?::\d{2,5})?"
    # resource path
    r"(?:[:/][-a-z\u00a1-\uffff0-9._~%!$&'()*+,;=:@/]*)?"
    # query string
    r"(?:\?\S*)?"
    # fragment
    r"(?:#\S*)?" "$",
    re.UNICODE | re.IGNORECASE,
)
ssh_urlpattern = re.compile(ssh_urlregex)


def get_repo_path(repo):
    """Return the path of the git repository corresponding to the provided
    Repository object from the DB.
    """
    repopath = repo.repopath("main")
    if not os.path.exists(repopath):
        _log.debug("Git repo not found at: %s", repopath)
        flask.abort(404, description="No git repo found")

    return repopath


def get_remote_repo_path(remote_git, branch_from, ignore_non_exist=False):
    """Return the path of the remote git repository corresponding to the
    provided information.
    """
    repopath = os.path.join(
        pagure_config["REMOTE_GIT_FOLDER"],
        werkzeug.utils.secure_filename("%s_%s" % (remote_git, branch_from)),
    )

    if not os.path.exists(repopath) and not ignore_non_exist:
        return None
    else:
        return repopath


def get_task_redirect_url(task, prev):
    if not task.ready():
        return flask.url_for("ui_ns.wait_task", taskid=task.id, prev=prev)
    result = task.get(timeout=0, propagate=False)
    if task.failed():
        flask.flash("Your task failed: %s" % result)
        task.forget()
        return prev
    if isinstance(result, dict):
        endpoint = result.pop("endpoint")
        task.forget()
        return flask.url_for(endpoint, **result)
    else:
        task.forget()
        flask.abort(418)


def wait_for_task(task, prev=None):
    if prev is None:
        prev = flask.request.full_path
    elif not is_safe_url(prev):
        prev = flask.url_for("index")
    return flask.redirect(get_task_redirect_url(task, prev))


def wait_for_task_post(taskid, form, endpoint, initial=False, **kwargs):
    form_action = flask.url_for(endpoint, **kwargs)
    return flask.render_template(
        "waiting_post.html",
        taskid=taskid,
        form_action=form_action,
        form_data=form.data,
        csrf=form.csrf_token,
        initial=initial,
    )


def split_project_fullname(project_name):
    """Returns the user, namespace and
    project name from a project fullname"""

    user = None
    namespace = None
    if "/" in project_name:
        project_items = project_name.split("/")

        if len(project_items) == 2:
            namespace, project_name = project_items
        elif len(project_items) == 3:
            _, user, project_name = project_items
        elif len(project_items) == 4:
            _, user, namespace, project_name = project_items

    return (user, namespace, project_name)


def get_parent_repo_path(repo, repotype="main"):
    """Return the path of the parent git repository corresponding to the
    provided Repository object from the DB.
    """
    if repo.parent:
        return repo.parent.repopath(repotype)
    else:
        return repo.repopath(repotype)


def stream_template(app, template_name, **context):
    app.update_template_context(context)
    t = app.jinja_env.get_template(template_name)
    rv = t.stream(context)
    rv.enable_buffering(5)
    return rv


def is_true(value, trueish=("1", "true", "t", "y")):
    if isinstance(value, bool):
        return value
    if isinstance(value, six.binary_type):
        # In Py3, str(b'true') == "b'true'", not b'true' as in Py2.
        value = value.decode()
    else:
        value = str(value)
    return value.strip().lower() in trueish


def validate_date(input_date, allow_empty=False):
    """Validate a given time.
    The time can either be given as an unix timestamp or using the
    yyyy-mm-dd format.
    If either fail to parse, we raise a 400 error
    """
    if allow_empty and input_date == "":
        return None
    # Validate and convert the time
    if input_date.isdigit():
        # We assume its a timestamp, so convert it to datetime
        try:
            output_date = datetime.datetime.fromtimestamp(int(input_date))
        except ValueError:
            raise InvalidTimestampException()
    else:
        # We assume datetime format, so validate it
        try:
            output_date = datetime.datetime.strptime(input_date, "%Y-%m-%d")
        except ValueError:
            raise InvalidDateformatException()

    return output_date


def validate_date_range(value):
    """Validate a given date range specified using the format since..until.
    If .. is not present in the range, it is assumed that only since was
    provided.
    """
    since = until = None
    if value is not None:
        if ".." in value:
            since, _, until = value.partition("..")
        else:
            since = value
        if since is not None:
            since = validate_date(since, allow_empty=True)
        if until is not None:
            until = validate_date(until, allow_empty=True)
    return (since, until)


def get_merge_options(request, merge_status):
    MERGE_OPTIONS = {
        "NO_CHANGE": {
            "code": "NO_CHANGE",
            "short_code": "No changes",
            "message": "Nothing to change, git is up to date",
        },
        "FFORWARD": {
            "code": "FFORWARD",
            "short_code": "Ok",
            "message": "The pull-request can be merged and fast-forwarded",
        },
        "CONFLICTS": {
            "code": "CONFLICTS",
            "short_code": "Conflicts",
            "message": "The pull-request cannot be merged due to conflicts",
        },
        "MERGE-non-ff-ok": {
            "code": "MERGE",
            "short_code": "With merge",
            "message": "The pull-request can be merged with a merge commit",
        },
        "MERGE-non-ff-bad": {
            "code": "NEEDSREBASE",
            "short_code": "Needs rebase",
            "message": "The pull-request must be rebased before merging",
        },
    }

    if merge_status == "MERGE":
        if request.project.settings.get(
            "disable_non_fast-forward_merges", False
        ):
            merge_status += "-non-ff-bad"
        else:
            merge_status += "-non-ff-ok"

    return MERGE_OPTIONS[merge_status]


def lookup_deploykey(project, username):
    """Finds the Deploy Key specified by the username.

    Args:
        project (model.Project): The project to look in
        username (string): The username string provided for the deploy key
    Returns (model.SSHKey or None): The SSHKey instance representing the
        project-specific deploy key by the username. None if the username is
        not a deploykey username or is not a valid deploy key for project.
    """
    # The username to look for is: deploykey_(filename(project.fullname))_keyid
    if not username.startswith("deploykey_"):
        return None
    username = username[len("deploykey_") :]
    rest, keyid = username.rsplit("_", 1)
    if rest != werkzeug.utils.secure_filename(project.fullname):
        # This is not a deploykey for the specified project
        return None
    keyid = int(keyid)
    for key in project.deploykeys:
        if key.id == keyid:
            return key
    return None


def project_has_hook_attr_value(project, hook, attr, value):
    """Finds out if project's hook has attribute of given value.

    :arg project: The project to inspect
    :type project: pagure.lib.model.Project
    :arg hook: Name of the hook to inspect
    :type hook: str
    :arg attr: Name of hook attribute to inspect
    :type attr: str
    :arg value: Value to compare project's hook attribute value with
    :type value: object
    :return: True if project's hook attribute value is equal with given
        value, False otherwise
    """
    retval = False
    hook_obj = getattr(project, hook, None)
    if hook_obj is not None:
        attr_obj = getattr(hook_obj, attr, None)
        if attr_obj == value:
            retval = True

    return retval


def parse_path(path):
    """Get the repo name, object type, object ID, and (if present)
    username and/or namespace from a URL path component. Will only
    handle the known object types from the OBJECTS dict. Assumes:
    * Project name comes immediately before object type
    * Object ID comes immediately after object type
    * If a fork, path starts with /fork/(username)
    * Namespace, if present, comes after fork username (if present) or at start
    * No other components come before the project name
    * None of the parsed items can contain a /
    """
    username = None
    namespace = None
    # path always starts with / so split and throw away first item
    items = path.split("/")[1:]
    # find the *last* match for any object type
    try:
        objtype = [
            item for item in items if item in ["issue", "pull-request"]
        ][-1]
    except IndexError:
        raise PagureException("No known object type found in path: %s" % path)
    try:
        # objid is the item after objtype, we need all items up to it
        items = items[: items.index(objtype) + 2]
        # now strip the repo, objtype and objid off the end
        (repo, objtype, objid) = items[-3:]
        items = items[:-3]
    except (IndexError, ValueError):
        raise PagureException(
            "No project or object ID found in path: %s" % path
        )
    # now check for a fork
    if items and items[0] == "fork":
        try:
            # get the username and strip it and 'fork'
            username = items[1]
            items = items[2:]
        except IndexError:
            raise PagureException(
                "Path starts with /fork but no user found! Path: %s" % path
            )
    # if we still have an item left, it must be the namespace
    if items:
        namespace = items.pop(0)
    # if we have any items left at this point, we've no idea
    if items:
        raise PagureException(
            "More path components than expected! Path: %s" % path
        )

    return username, namespace, repo, objtype, objid
