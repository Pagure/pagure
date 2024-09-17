# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""
from __future__ import absolute_import, print_function, unicode_literals

import abc
import json
import logging
import os
from io import open

import pkg_resources
from six import with_metaclass

from pagure.config import config as pagure_config
from pagure.utils import is_repo_collaborator, lookup_deploykey

# logging.config.dictConfig(pagure_config.get('LOGGING') or {'version': 1})
_log = logging.getLogger(__name__)

GIT_AUTH_BACKEND_NAME = None
GIT_AUTH_BACKEND_INSTANCE = None


def get_git_auth_helper(backend=None):
    """Instantiate and return the appropriate git auth helper backend.

    :arg backend: The name of the backend to find on the system (declared via
        the entry_points in setup.py).
        Pagure comes by default with the following backends:
            test_auth, pagure_authorized_keys
    :type backend: str

    """
    global GIT_AUTH_BACKEND_NAME
    global GIT_AUTH_BACKEND_INSTANCE

    if backend is None:
        backend = pagure_config["GIT_AUTH_BACKEND"]

    if (
        GIT_AUTH_BACKEND_NAME
        and GIT_AUTH_BACKEND_INSTANCE
        and backend == GIT_AUTH_BACKEND_NAME
    ):
        # This got previously instantiated, return that instance to avoid
        # having to instantiate it multiple times as long as the same backend
        # is used.
        return GIT_AUTH_BACKEND_INSTANCE

    _log.info("Looking for backend: %s", backend)
    points = pkg_resources.iter_entry_points("pagure.git_auth.helpers")
    classes = dict([(point.name, point) for point in points])
    _log.debug("Found the following installed helpers %r" % classes)
    if len(classes) == 0:
        _log.debug("Was unable to find any helpers, registering built-in")
        cls = {
            "test_auth": GitAuthTestHelper,
            "pagure": PagureGitAuth,
            "pagure_authorized_keys": PagureGitAuth,
        }[backend]
    else:
        cls = classes[backend].load(False)
    _log.debug("Returning helper %r from backend key %r" % (cls, backend))

    GIT_AUTH_BACKEND_NAME = backend
    GIT_AUTH_BACKEND_INSTANCE = cls()
    return GIT_AUTH_BACKEND_INSTANCE


class GitAuthHelper(with_metaclass(abc.ABCMeta, object)):
    """The class to inherit from when creating your own git authentication
    helper.
    """

    is_dynamic = False

    @classmethod
    # This method can't be marked as abstract, since it's new and that would
    # break backwards compatibility
    def check_acl(cls, session, project, username, refname, **info):
        """This method is used in Dynamic Git Auth helpers to check acls.

        It is acceptable for implementations to print things, which will be
        returned to the user.

        Please make sure to add a **kwarg in any implementation, even if
        specific keyword arguments are added for the known fields, to make
        sure your implementation remains working if new items are added.

        Args:
            session (sqlalchemy.Session): Database session
            project (model.Project): Project instance push is for
            username (string): The name of the user trying to push
            refname (string): The name of the ref being pushed to
        Kwargs:
            Extra arguments to help in deciding whether to approve or deny a
            push. This may get additional possible values later on, but will
            have at least:
            - is_update (bool): Whether this is being run at the "update" hook
                moment. See the return type notes to see the differences.
            - revfrom (string): The commit hash the update is happening from.
            - revto (string): The commit hash the update is happening to.
            - pull_request (model.PullRequest or None): The PR that is trying
                to be merged.
            - repotype (string): The pagure.lib.query.get_repotypes() value
                for the repo being pushed to.
            - repodir (string): A directory containing the current
                repository, including the new objects to be approved.
                Note that this might or might not be directly writable, and any
                writes might or might not be accepted. ACL checks MUST not make
                any changes in this repository. (added after 5.0.1)
        Returns (bool): Whether to allow this push.
            If is_update is False and the ACL returns False, the entire push
                is aborted. If is_update is True and the ACL returns True, only
                a single ref update is blocked. So if you want to block just a
                single ref from being updated, only return False if is_update
                is True.
        """
        raise NotImplementedError(
            "check_acl on static Git Auth Backend called"
        )


def _read_file(filename):
    """Reads the specified file and return its content.
    Returns None if it could not read the file for any reason.
    """
    if not os.path.exists(filename):
        _log.info("Could not find file: %s", filename)
    else:
        with open(filename) as stream:
            return stream.read()


class PagureGitAuth(GitAuthHelper):
    """Standard Pagure git auth implementation."""

    is_dynamic = True

    def info(self, msg):
        """Function that prints info about decisions to clients.

        This is a function to make it possible to override for test suite."""
        print(msg)

    def check_acl(
        self,
        session,
        project,
        username,
        refname,
        pull_request,
        repotype,
        is_internal,
        **info,
    ):
        if is_internal:
            self.info("Internal push allowed")
            return True

        # Check whether a PR is required for this repo or in general
        global_pr_only = pagure_config.get("PR_ONLY", False)
        pr_only = project.settings.get("pull_request_access_only", False)
        if repotype == "main":
            if (
                pr_only or (global_pr_only and not project.is_fork)
            ) and not pull_request:
                self.info("Pull request required")
                return False

        if username is None:
            return False

        # Determine whether the current user is allowed to push
        is_committer = is_repo_collaborator(
            project, refname, username, session
        )
        deploykey = lookup_deploykey(project, username)
        if deploykey is not None:
            self.info("Deploykey used. Push access: %s" % deploykey.pushaccess)
            is_committer = deploykey.pushaccess
        self.info("Has commit access: %s" % is_committer)

        return is_committer


class GitAuthTestHelper(GitAuthHelper):
    """Simple test auth module to check the auth customization system."""

    is_dynamic = True

    @classmethod
    def check_acl(
        cls, session, project, username, refname, pull_request, **info
    ):
        testfile = pagure_config.get("TEST_AUTH_STATUS", None)
        if not testfile or not os.path.exists(testfile):
            # If we are not configured, we will assume allowed
            return True

        with open(testfile, "r") as statusfile:
            status = json.loads(statusfile.read())

        if status is True or status is False:
            return status

        # Other option would be a dict with ref->allow
        # (with allow True, pronly), missing means False)
        if refname not in status:
            print("ref '%s' not in status" % refname)
            return False
        elif status[refname] is True:
            return True
        elif status[refname] == "pronly":
            return pull_request is not None
