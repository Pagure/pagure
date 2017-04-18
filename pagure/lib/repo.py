# -*- coding: utf-8 -*-

"""
 (c) 2015-2017 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""

import logging
import os
import subprocess

import pygit2

import pagure
import pagure.exceptions


_log = logging.getLogger(__name__)


def get_pygit2_version():
    ''' Return pygit2 version as a tuple of integers.
    This is needed for correct version comparison.
    '''
    return tuple([int(i) for i in pygit2.__version__.split('.')])


class PagureRepo(pygit2.Repository):
    """ An utility class allowing to go around pygit2's inability to be
    stable.

    """

    @staticmethod
    def push(remote, refname):
        """ Push the given reference to the specified remote. """
        pygit2_version = get_pygit2_version()
        if pygit2_version >= (0, 22):
            remote.push([refname])
        else:
            remote.push(refname)

    def pull(self, remote_name='origin', branch='master', force=False):
        ''' pull changes for the specified remote (defaults to origin).

        Code from MichaelBoselowitz at:
        https://github.com/MichaelBoselowitz/pygit2-examples/blob/
            68e889e50a592d30ab4105a2e7b9f28fac7324c8/examples.py#L58
        licensed under the MIT license.
        '''

        for remote in self.remotes:
            if remote.name == remote_name:
                remote.fetch()
                remote_master_id = self.lookup_reference(
                    'refs/remotes/origin/%s' % branch).target

                if force:
                    repo_branch = self.lookup_reference(
                        'refs/heads/%s' % branch)
                    repo_branch.set_target(remote_master_id)

                merge_result, _ = self.merge_analysis(remote_master_id)
                # Up to date, do nothing
                if merge_result & pygit2.GIT_MERGE_ANALYSIS_UP_TO_DATE:
                    return
                # We can just fastforward
                elif merge_result & pygit2.GIT_MERGE_ANALYSIS_FASTFORWARD:
                    self.checkout_tree(self.get(remote_master_id))
                    master_ref = self.lookup_reference(
                        'refs/heads/%s' % branch)
                    master_ref.set_target(remote_master_id)
                    self.head.set_target(remote_master_id)
                elif merge_result & pygit2.GIT_MERGE_ANALYSIS_NORMAL:
                    raise pagure.exceptions.GitConflictsException(
                        'Pulling remote changes leads to a conflict')
                else:
                    _log.debug(
                        'Un-expected merge result: %s' % (
                        'Unexpected merge result: %s' % (
                            pygit2.GIT_MERGE_ANALYSIS_NORMAL))
                    raise AssertionError('Unknown merge analysis result')

    def run_hook(self, old, new, ref, username):
        ''' Runs the post-update hook on the repo. '''
        line = '%s %s %s\n' % (old, new, ref)
        cmd = ['./hooks/post-receive']
        env = os.environ.copy()
        env['GIT_DIR'] = self.path
        env['GL_USER'] = username

        hookfile = os.path.join(self.path, 'hooks', 'post-receive')
        if not os.path.exists(hookfile):
            return

        procs = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=self.path,
            env=env,
        )
        (out, err) = procs.communicate(line)
        retcode = procs.wait()
        if retcode:
            print 'ERROR: %s =-- %s' % (cmd, retcode)
            print out
            print err
            out = out.rstrip('\n\r')
