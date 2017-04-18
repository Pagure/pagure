Upgrade a database
==================


Database schema migration are handled in two ways:

* New tables

For this we simply rely on the ``createdb`` script used when creating the
database the first time.

* Changes to existing tables

For changes to existing tables, we rely on `Alembic <http://alembic.readthedocs.org/>`_.
This allows us to do upgrade and downgrade of schema migration, kind of like
one would do commits in a system like git.

To upgrade the database to the latest version simply run:
::

    alembic upgrade head

This may fail for different reasons:

* The change was already made in the database

This can be because the version of the database schema saved is incorrect.
It can be debugged using the following commands:

  * Find the current revision: ``alembic current``
  * See the entire history: ``alembic history``

Once the revision at which your database should be is found (in the history)
you can declare that your database is at this given revision using:
``alembic stamp <revision id>``.

Eventually, if you do not know where your database is or should be, you can
do an iterative process stamping the database for every revision, one by one
trying every time to ``alembic upgrade`` until it works.

* The database used does not support some of the changes

SQLite is handy for development but does not support all the features of a
real database server. Upgrading a SQLite database might therefore not work,
depending on the changes done.

In some cases, if you are using a SQLite database, you will have to destroy
it and create a new one.
