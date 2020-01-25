# -*- coding: utf-8 -*-

"""
 (c) 2015-2019 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""
from __future__ import print_function, unicode_literals, absolute_import

import logging
import subprocess

import pygit2

import pagure
import pagure.exceptions


_log = logging.getLogger(__name__)


def get_pygit2_version():
    """ Return pygit2 version as a tuple of integers.
    This is needed for correct version comparison.
    """
    return tuple([int(i) for i in pygit2.__version__.split(".")])


def run_command(command, cwd=None):
    _log.info("Running command: %s", command)
    try:
        out = subprocess.check_output(
            command, stderr=subprocess.STDOUT, cwd=cwd
        ).decode("utf-8")
        _log.info("   command ran successfully")
        _log.debug("Output: %s" % out)
    except subprocess.CalledProcessError as err:
        _log.debug(
            "Command FAILED: {cmd} returned code {code} with the "
            "following output: {output}".format(
                cmd=err.cmd, code=err.returncode, output=err.output
            )
        )
        raise pagure.exceptions.PagureException(
            "Did not manage to rebase this pull-request"
        )
    return out


class PagureRepo(pygit2.Repository):
    """ An utility class allowing to go around pygit2's inability to be
    stable.

    """

    @staticmethod
    def clone(path_from, path_to, checkout_branch=None, bare=False):
        """ Clone the git repo at the specified path to the specified location.

        This method is meant to replace pygit2.clone_repository which for us
        leaks file descriptors on large project leading to "Too many open files
        error" which then prevent some tasks from completing.

        :arg path_from: the path or url of the git repository to clone
        :type path_from: str
        :arg path_to: the path where the git repository should be cloned
        :type path_to: str
        :
        """
        cmd = ["git", "clone", path_from, path_to]
        if checkout_branch:
            cmd.extend(["-b", checkout_branch])
        if bare:
            cmd.append("--bare")

        run_command(cmd)

    @staticmethod
    def push(remote, refname):
        """ Push the given reference to the specified remote. """
        pygit2_version = get_pygit2_version()
        if pygit2_version >= (0, 22):
            remote.push([refname])
        else:
            remote.push(refname)

    def pull(self, remote_name="origin", branch="master", force=False):
        """ pull changes for the specified remote (defaults to origin).

        Code from MichaelBoselowitz at:
        https://github.com/MichaelBoselowitz/pygit2-examples/blob/
            68e889e50a592d30ab4105a2e7b9f28fac7324c8/examples.py#L58
        licensed under the MIT license.
        """

        for remote in self.remotes:
            if remote.name == remote_name:
                remote.fetch()
                remote_master_id = self.lookup_reference(
                    "refs/remotes/origin/%s" % branch
                ).target

                if force:
                    repo_branch = self.lookup_reference(
                        "refs/heads/%s" % branch
                    )
                    repo_branch.set_target(remote_master_id)

                merge_result, _ = self.merge_analysis(remote_master_id)
                # Up to date, do nothing
                if merge_result & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
                    return
                # We can just fastforward
                elif merge_result & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
                    self.checkout_tree(self.get(remote_master_id))
                    master_ref = self.lookup_reference(
                        "refs/heads/%s" % branch
                    )
                    master_ref.set_target(remote_master_id)
                    self.head.set_target(remote_master_id)
                elif merge_result & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
                    raise pagure.exceptions.GitConflictsException(
                        "Pulling remote changes leads to a conflict"
                    )
                else:
                    _log.debug(
                        "Unexpected merge result: %s"
                        % (pygit2.GIT_MERGE_ANALYSIS_NORMAL)
                    )
                    raise AssertionError("Unknown merge analysis result")

    @staticmethod
    def log(path, log_options=None, target=None, fromref=None):
        """ Run git log with the specified options at the specified target.

        This method runs the system's `git log` command since pygit2 doesn't
        offer us the possibility to do this via them.

        :kwarg log_options: options to pass to git log
        :type log_options: list or None
        :kwarg target: the target of the git log command, can be a ref, a
            file or nothing
        :type path_to: str or None
        :kwarg fromref: a reference/commit to use when generating the log
        :type path_to: str or None
        :
        """
        cmd = ["git", "log"]
        if log_options:
            cmd.extend(log_options)
        if fromref:
            cmd.append(fromref)
        if target:
            cmd.extend(["--", target])

        return run_command(cmd, cwd=path)

    @staticmethod
    def get_active_branches(path, nbranch=8, catch_exception=False):
        """ Returns the active branches in the git repo at the specified
        location.

        :arg path: the location of the git repo
        :type path: str
        :kwarg nbranch: the number of active branches to consider, defaults to
            6
        :type nbranch: int
        :kwarg catch_exception: Whether or not this method should silently
            ignore all exception raised when running the git command and return
            an empty list in those situations. Defaults to False.
        :type catch_exception: boolean
        """
        cmd = [
            "git",
            "for-each-ref",
            "--count=%s" % nbranch,
            "--sort=-committerdate",
            "refs/heads/",
        ]
        output = []
        try:
            cmd_output = run_command(cmd, path)
            for row in cmd_output.split("\n"):
                output.append(
                    row.replace("\t", " ")
                    .rsplit(" ", 1)[-1]
                    .replace("refs/heads/", "")
                )
        except Exception:
            if not catch_exception:
                raise
        return output
