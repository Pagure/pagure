# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


import pygit2

import pagure
import pagure.exceptions


class PagureRepo(pygit2.Repository):
    """ An utility class allowing to go around pygit2's inability to be
    stable.

    """

    @staticmethod
    def push(remote, refname):
        """ Push the given reference to the specified remote. """
        if pygit2.__version__.startswith('0.22'):
            remote.push([refname])
        else:
            remote.push(refname)

    def pull(self, remote_name='origin', branch='master'):
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
                    raise pagure.exceptions.PagureException(
                        'Pulling remote changes leads to a conflict')
                else:
                    pagure.LOG.debug(
                        'Un-expected merge result: %s' % (
                        pygit2.GIT_MERGE_ANALYSIS_NORMAL))
                    raise AssertionError('Unknown merge analysis result')
