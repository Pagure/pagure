Upgrading Pagure
================

From 1.x to 2.0
---------------

As the version change indicates, 2.0 brings quite a number of changes,
including some that are not backward compatible.

When upgrading to 2.0 you will have to:

* Update the database schema using alembic: ``alembic upgrade head``

* Create the new DB tables so that the new plugins work using the
  ``createdb.py`` script

* Move the forks git repo

Forked git repos are now located under the same folder as the regular git
repos, just under a ``forks/`` subfolder.
So the structure changes from: ::

    repos/
    ├── foo.git
    └── bar.git

    forks/
    ├── patrick/
    │   ├── test.git
    │   └── ipsilon.git
    └── pingou/
        ├── foo.git
        └── bar.git

to: ::

    repos/
    ├── foo.git
    ├── bar.git
    └── forks/
        ├── patrick/
        │   ├── test.git
        │   └── ipsilon.git
        └── pingou/
            ├── foo.git
            └── bar.git

So the entire ``forks`` folder is moved under the ``repos`` folder where
the other repositories are, containing the sources of the projects.


Git repos for ``tickets`` and ``requests`` will be trickier to move as the
structure changes from: ::

    tickets/
    ├── foo.git
    ├── bar.git
    ├── patrick/
    │   ├── test.git
    │   └── ipsilon.git
    └── pingou/
        ├── foo.git
        └── bar.git

to: ::

    tickets/
    ├── foo.git
    ├── bar.git
    └── forks/
        ├── patrick/
        │   ├── test.git
        │   └── ipsilon.git
        └── pingou/
            ├── foo.git
            └── bar.git

Same for the ``requests`` git repos.

As you can see in the ``tickets`` and the ``requests`` folders there are two
types of folders, git repos which are folder with a name ending with ``.git``,
and folder corresponding to usernames. These last ones are the ones to be
moved into a subfolder ``forks/``.

* Re-generate the gitolite configuration.

This can be done via the ``Re-generate gitolite ACLs file`` button in the
admin page.
