.. _custom-gitolite:

Customize the gitolite configuration
====================================

Pagure provides a mechanism to allow customizing the creation and
compilation of the configuration file of gitolite.

To customize the gitolite configuration file, we invite you to look at the
`sources of the module pagure.lib.git_auth
<https://pagure.io/pagure/blob/master/f/pagure/lib/git_auth.py>`_.

As you can see it defines the following class::

    class GitAuthHelper(object):

        __metaclass__ = abc.ABCMeta

        @staticmethod
        @abc.abstractmethod
        def generate_acls():
            pass

This will be the class you will have to inherit from in order to inject your
own code.
You will then declare an entry point in your `setup.py` following this
template::

    entry_points="""
    [pagure.git_auth.helpers]
    my_git_auth = my_pagure.my_module:MyGitAuthTestHelper
    """

Then you can adjust pagure's configuration file to say::

    GITOLITE_BACKEND = 'my_git_auth'
