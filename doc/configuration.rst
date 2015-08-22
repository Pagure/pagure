Configuration
=============

Pagure offers a wide-varieties of options that must or can be used to
adjust its behavior.

Must options
------------

Here are listed the options you must set-up in order to get pagure running.


SECRET_KEY
~~~~~~~~~~

This key is used by flask to create the session. It should be kept secret
and set as a long and random string.


DB_URL
~~~~~~

This key indicates to the framework how and where to connect to the database
server. Pagure using `SQLAchemy <http://www.sqlalchemy.org/>`_ it can connect
to a wide range of database server including MySQL, PostgreSQL and SQLite.

Examples values:

::

    DB_URL=mysql://user:pass@host/db_name
    DB_URL=postgres://user:pass@host/db_name
    DB_URL = 'sqlite:////var/tmp/pagure_dev.sqlite'

Defaults to ``sqlite:////var/tmp/pagure_dev.sqlite``


APP_URL
~~~~~~~

This key indicates the URL at which this pagure instance will be made available.

Defaults to: ``https://pagure.org/``


EMAIL_ERROR
~~~~~~~~~~~

Pagure sends email when it caches an un-expected error (which saves you from
having to monitor the logs regularly but if you like, the error is still
present in the logs).
This setting allows you to specify to which email address to send these error
reports.


GIT_URL_SSH
~~~~~~~~~~~

This configuration key provides the information to the user on how to clone
the git repos hosted on pagure via `SSH <>`_.

The URL should end with a slash ``/``.

Defaults to: ``'ssh://git@pagure.org/'``


GIT_URL_GIT
~~~~~~~~~~~
This configuration key provides the information to the user on how to clone
the git repos hosted on pagure anonymously. These access can be granted via
the ``git://`` or ``http(s)://`` protocols.

The URL should end with a slash ``/``.

Defaults to: ``'git://pagure.org/'``
