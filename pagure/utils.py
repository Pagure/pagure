# -*- coding: utf-8 -*-

"""
 (c) 2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import os
import re
import urlparse
from functools import wraps

import flask
import pygit2
import werkzeug

from pagure.config import config as pagure_config


def authenticated():
    ''' Utility function checking if the current user is logged in or not.
    '''
    return hasattr(flask.g, 'fas_user') and flask.g.fas_user is not None


def api_authenticated():
    ''' Utility function checking if the current user is logged in or not
    in the API.
    '''
    return hasattr(flask.g, 'fas_user') \
        and flask.g.fas_user is not None \
        and hasattr(flask.g, 'token') \
        and flask.g.token is not None


def is_safe_url(target):  # pragma: no cover
    """ Checks that the target url is safe and sending to the current
    website not some other malicious one.
    """
    ref_url = urlparse.urlparse(flask.request.host_url)
    test_url = urlparse.urlparse(
        urlparse.urljoin(flask.request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
        ref_url.netloc == test_url.netloc


def is_admin():
    """ Return whether the user is admin for this application or not. """
    if not authenticated():
        return False

    user = flask.g.fas_user

    auth_method = pagure_config.get('PAGURE_AUTH', None)
    if auth_method == 'fas':
        if not user.cla_done:
            return False

    admin_users = pagure_config.get('PAGURE_ADMIN_USERS', [])
    if not isinstance(admin_users, list):
        admin_users = [admin_users]
    if user.username in admin_users:
        return True

    admins = pagure_config['ADMIN_GROUP']
    if not isinstance(admins, list):
        admins = [admins]
    admins = set(admins or [])
    groups = set(flask.g.fas_user.groups)

    return not groups.isdisjoint(admins)


def is_repo_admin(repo_obj):
    """ Return whether the user is an admin of the provided repo. """
    if not authenticated():
        return False

    user = flask.g.fas_user.username

    if is_admin():
        return True

    usergrps = [
        usr.user
        for grp in repo_obj.admin_groups
        for usr in grp.users]

    return user == repo_obj.user.user or (
        user in [usr.user for usr in repo_obj.admins]
    ) or (user in usergrps)


def is_repo_committer(repo_obj):
    """ Return whether the user is a committer of the provided repo. """
    if not authenticated():
        return False

    user = flask.g.fas_user.username

    if is_admin():
        return True

    grps = flask.g.fas_user.groups
    ext_committer = pagure_config.get('EXTERNAL_COMMITTER', None)
    if ext_committer:
        overlap = set(ext_committer).intersection(grps)
        if overlap:
            for grp in overlap:
                restrict = ext_committer[grp].get('restrict', [])
                exclude = ext_committer[grp].get('exclude', [])
                if restrict and repo_obj.fullname not in restrict:
                    return False
                elif repo_obj.fullname in exclude:
                    return False
                else:
                    return True

    usergrps = [
        usr.user
        for grp in repo_obj.committer_groups
        for usr in grp.users]

    return user == repo_obj.user.user or (
        user in [usr.user for usr in repo_obj.committers]
    ) or (user in usergrps)


def is_repo_user(repo_obj):
    """ Return whether the user has some access in the provided repo. """
    if not authenticated():
        return False

    user = flask.g.fas_user.username

    if is_admin():
        return True

    usergrps = [
        usr.user
        for grp in repo_obj.groups
        for usr in grp.users]

    return user == repo_obj.user.user or (
        user in [usr.user for usr in repo_obj.users]
    ) or (user in usergrps)


def login_required(function):
    """ Flask decorator to retrict access to logged in user.
    If the auth system is ``fas`` it will also require that the user sign
    the FPCA.
    """
    auth_method = pagure_config.get('PAGURE_AUTH', None)

    @wraps(function)
    def decorated_function(*args, **kwargs):
        """ Decorated function, actually does the work. """
        if flask.session.get('_justloggedout', False):
            return flask.redirect(flask.url_for('ui_ns.index'))
        elif not authenticated():
            return flask.redirect(
                flask.url_for('auth_login', next=flask.request.url))
        elif auth_method == 'fas' and not flask.g.fas_user.cla_done:
            flask.flash(flask.Markup(
                'You must <a href="https://admin.fedoraproject'
                '.org/accounts/">sign the FPCA</a> (Fedora Project '
                'Contributor Agreement) to use pagure'), 'errors')
            return flask.redirect(flask.url_for('ui_ns.index'))
        return function(*args, **kwargs)
    return decorated_function


def __get_file_in_tree(repo_obj, tree, filepath, bail_on_tree=False):
    ''' Retrieve the entry corresponding to the provided filename in a
    given tree.
    '''

    filename = filepath[0]
    if isinstance(tree, pygit2.Blob):
        return
    for entry in tree:
        fname = entry.name.decode('utf-8')
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
                if entry.filemode == pygit2.GIT_FILEMODE_LINK \
                        and os.path.normpath(content) == content \
                        and not os.path.isabs(content):
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
                    repo_obj, nextitem, filepath[1:],
                    bail_on_tree=bail_on_tree)


ip_middle_octet = u"(?:\.(?:1?\d{1,2}|2[0-4]\d|25[0-5]))"
ip_last_octet = u"(?:\.(?:[1-9]\d?|1\d\d|2[0-4]\d|25[0-4]))"

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
    u"^"
    # protocol identifier
    u"(?:(?:https?|ftp)://)"
    # user:pass authentication
    u"(?:\S+(?::\S*)?@)?"
    u"(?:"
    u"(?P<private_ip>"
    # IP address exclusion
    # private & local networks
    u"(?:(?:10|127)" + ip_middle_octet + u"{2}" + ip_last_octet + u")|"
    u"(?:(?:169\.254|192\.168)" + ip_middle_octet + ip_last_octet + u")|"
    u"(?:172\.(?:1[6-9]|2\d|3[0-1])" + ip_middle_octet + ip_last_octet + u"))"
    u"|"
    # IP address dotted notation octets
    # excludes loopback network 0.0.0.0
    # excludes reserved space >= 224.0.0.0
    # excludes network & broadcast addresses
    # (first & last IP address of each class)
    u"(?P<public_ip>"
    u"(?:[1-9]\d?|1\d\d|2[01]\d|22[0-3])"
    u"" + ip_middle_octet + u"{2}"
    u"" + ip_last_octet + u")"
    u"|"
    # host name
    u"(?:(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)"
    # domain name
    u"(?:\.(?:[a-z\u00a1-\uffff0-9]-?)*[a-z\u00a1-\uffff0-9]+)*"
    # TLD identifier
    u"(?:\.(?:[a-z\u00a1-\uffff]{2,}))"
    u")"
    # port number
    u"(?::\d{2,5})?"
    # resource path
    u"(?:/\S*)?"
    u"$",
    re.UNICODE | re.IGNORECASE
)
urlpattern = re.compile(urlregex)


def get_repo_path(repo):
    """ Return the path of the git repository corresponding to the provided
    Repository object from the DB.
    """
    repopath = os.path.join(pagure_config['GIT_FOLDER'], repo.path)
    if not os.path.exists(repopath):
        flask.abort(404, 'No git repo found')

    return repopath


def get_remote_repo_path(remote_git, branch_from, ignore_non_exist=False):
    """ Return the path of the remote git repository corresponding to the
    provided information.
    """
    repopath = os.path.join(
        pagure_config['REMOTE_GIT_FOLDER'],
        werkzeug.secure_filename('%s_%s' % (remote_git, branch_from))
    )

    if not os.path.exists(repopath) and not ignore_non_exist:
        return None
    else:
        return repopath


def get_task_redirect_url(task, prev):
    if not task.ready():
        return flask.url_for(
            'ui_ns.wait_task',
            taskid=task.id,
            prev=prev)
    result = task.get(timeout=0, propagate=False)
    if task.failed():
        flask.flash('Your task failed: %s' % str(result))
        task.forget()
        return prev
    if isinstance(result, dict):
        endpoint = result.pop('endpoint')
        task.forget()
        return flask.url_for(endpoint, **result)
    else:
        task.forget()
        flask.abort(418)


def wait_for_task(task, prev=None):
    if prev is None:
        prev = flask.request.full_path
    elif not is_safe_url(prev):
        prev = flask.url_for('index')
    return flask.redirect(get_task_redirect_url(task, prev))


def wait_for_task_post(taskid, form, endpoint, initial=False, **kwargs):
    form_action = flask.url_for(endpoint, **kwargs)
    return flask.render_template(
        'waiting_post.html',
        taskid=taskid,
        form_action=form_action,
        form_data=form.data,
        csrf=form.csrf_token,
        initial=initial)


def split_project_fullname(project_name):
    """Returns the user, namespace and
    project name from a project fullname"""

    user = None
    namespace = None
    if '/' in project_name:
        project_items = project_name.split('/')

        if len(project_items) == 2:
            namespace, project_name = project_items
        elif len(project_items) == 3:
            _, user, project_name = project_items
        elif len(project_items) == 4:
            _, user, namespace, project_name = project_items

    return (user, namespace, project_name)


def get_parent_repo_path(repo):
    """ Return the path of the parent git repository corresponding to the
    provided Repository object from the DB.
    """
    if repo.parent:
        parentpath = os.path.join(
            pagure_config['GIT_FOLDER'], repo.parent.path)
    else:
        parentpath = os.path.join(pagure_config['GIT_FOLDER'], repo.path)

    return parentpath
