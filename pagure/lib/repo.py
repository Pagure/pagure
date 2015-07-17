# -*- coding: utf-8 -*-

"""
 (c) 2015 - Copyright Red Hat Inc

 Authors:
   Pierre-Yves Chibon <pingou@pingoured.fr>

"""


import pygit2


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
