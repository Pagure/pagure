HTTP PUSH
=========

When using git push over http against a pagure instance, there are two
situations to distinguish.

Git push over http with API token
---------------------------------

This is going to be the most supported approach. Any user can generate API
tokens with the ``commit`` ACL which reads in the UI as: `Commit to a git
repository via http(s)`.
These API tokens can be specific to a project if generated in the settings
page of the project, or generic to all projects if generated in the
user's settings page.
In either case, they will no work if the user does not have at commit access
to the project.

Once the API token has been generate, the user needs to enter it with git
prompts for a password (instead of their actual password).

For example:

::

    $ git push
    username: pingou
    password: ABC123...


Git push over http with Username & Password
-------------------------------------------

This is only supported on pagure instance that are using the ``local``
authentication system (ie: where pagure manages the registration of the
user accounts, email confirmation, etc).

For these pagure instances and for these only, when being prompted by git
for an username and password the user can choose to enter either their
username and actual password or their username and an API token.


Storing the password/token
--------------------------

If you interact with git regularly, typing you password or API token will
quickly become tiring.
Thanksfully, git has a built-in mechanism named `git credential store
<https://git-scm.com/docs/git-credential-store>`_ which can take care of this
for you.

You can use two modes for the store, either ``cache`` or ``store``.
- `cache` will cache your credential in memory for 15 minutes (by default)
- `store` will actually store your credentials in **plain text** on disk

You can set this using either:
::

    $ git config credential.helper store
    $ git config credential.helper cache

The timeout of the cache can be configured using:
::

    $ git config credential.helper 'cache --timeout=3600'

Where the timeout value is a number of seconds (so here the cache is extended
to one hour).

Finally, if you wish to use this configuration on multiple project, you can
add the ``--global`` argument to these commands which will make the
configuration work for all your git repo instead of just the one in which
you run the command.
