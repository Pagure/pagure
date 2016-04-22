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


Git repos for ``tickets``, ``requests`` and ``docs`` will be trickier to
move as the structure changes from: ::

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

Same for the ``requests`` and the ``docs`` git repos.

As you can see in the ``tickets``, ``requests`` and ``docs`` folders there
are two types of folders, git repos which are folder with a name ending
with ``.git``, and folder corresponding to usernames. These last ones are
the ones to be moved into a subfolder ``forks/``.

This can be done using something like: ::

    mkdir forks
    for i in `ls -1 |grep -v '\.git'`; do mv $i forks/; done

* Re-generate the gitolite configuration.

This can be done via the ``Re-generate gitolite ACLs file`` button in the
admin page.

* Keep URLs backward compatible

The support of pseudo-namespace in pagure 2.0 has required some changes made
to the URL schema:
https://pagure.io/pagure/053d8cc95fcd50c23a8b0a7f70e55f8d1cc7aebb
became:
https://pagure.io/pagure/c/053d8cc95fcd50c23a8b0a7f70e55f8d1cc7aebb
(Note the added /c/ in it)

We introduced a backward compatibility fix for this.

This fix is however *disabled* by default so if you wish to keep the URLs
valid, you will need to adjust you configuration file to include: ::

    OLD_VIEW_COMMIT_ENABLED = True
