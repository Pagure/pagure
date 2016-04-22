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
    ├── user/foo.git
    └── user/bar.git

to: ::

    repos/
    ├── foo.git
    ├── forks/user/foo.git
    ├── forks/user/bar.git
    └── bar.git

So the entire ``forks`` folder is moved under the ``repos`` folder where are
the other repositories containing the sources of the projects.


Git repos for ``tickets`` and ``requests`` will be trickier to move as the
structure changes from: ::

    tickets/
    ├── foo.git
    ├── user/foo.git
    ├── user/bar.git
    └── bar.git

to: ::

    tickets/
    ├── foo.git
    ├── forks/user/foo.git
    ├── forks/user/bar.git
    └── bar.git

Same for the ``requests`` git repos.

For these, the folders are moved into a subfolder ``forks/`` while the folder
containing the git repositories (ie: folders ending with ``.git``) remains
un-touched.

* Re-generate the gitolite configuration.

This can be done via the ``Re-generate gitolite ACLs file`` button in the
admin page.
