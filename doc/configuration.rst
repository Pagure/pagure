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


GIT_FOLDER
~~~~~~~~~~

This configuration key points to the folder where are stored the git repos
of the projects.

Each project in pagure has 4 git repositories:

- the main repo for the code
- the doc repo showed in the doc server
- the ticket and request repos storing the metadata of the
  tickets/pull-requests

There are then another 2 folders specifying the locations of the forks and
remote git repo used for the remotes pull-requests (ie: pull-request coming
from a project not hosted on pagure).


FORK_FOLDER
~~~~~~~~~~~

This configuration key points to the folder where are stored the git repos
of forks of the projects.


DOCS_FOLDER
~~~~~~~~~~~

This configuration key points to the folder where are stored the git repos
for the documentation of the projects.


TICKETS_FOLDER
~~~~~~~~~~~~~~

This configuration key points to the folder where are stored the git repos
storing the metadata of the tickets opened against the project.


REQUESTS_FOLDER
~~~~~~~~~~~~~~~

This configuration key points to the folder where are stored the git repos
storing the metadata of the pull-requests opened against the project.


REMOTE_GIT_FOLDER
~~~~~~~~~~~~~~~~~

This configuration key points to the folder where are stored the remote git
repos (ie: not hosted on pagure) that someone used to open a pull-request
against a project hosted on pagure.


SESSION_COOKIE_SECURE
~~~~~~~~~~~~~~~~~~~~~

When this is set to True, the session cookie will only be returned to the
server via ssl (https). If you connect to the server via plain http, the
cookie will not be sent. This prevents sniffing of the cookie contents.
This may be set to False when testing your application but should always
be set to True in production.

Defaults to: ``False`` for development, must be ``True`` in production with
https.


FROM_EMAIL
~~~~~~~~~~

This setting allows to specify the email address used by this pagure instance
when sending emails (notifications).

Defaults to: ``pagure@pagure.org``


DOMAIN_EMAIL_NOTIFICATIONS
~~~~~~~~~~~~~~~~~~~~~~~~~~

This setting allows to specify the domain used by this pagure instance
when sending emails (notifications). More precisely, this setting is used
when building the ``msg-id`` header of the emails sent.

Defaults to: ``pagure.org``


Configure Gitolite
------------------

Pagure uses `gitolite <http://gitolite.com/>`_ as an authorization layer.
Gitolite relies on `SSH <https://en.wikipedia.org/wiki/Secure_Shell>`_ for
the authentication. In other words, SSH let you in and gitolite check if you
are allowed to do what you are trying to do once you are inside.


GITOLITE_HOME
~~~~~~~~~~~~~

This configuration key should point to the home of the user under which
gitolite is ran.


GITOLITE_VERSION
~~~~~~~~~~~~~~~~

This configuration key allows to specify which version of gitolite you are
using, it can be either ``2`` or ``3``.

Defaults to: ``3``.


GITOLITE_KEYDIR
~~~~~~~~~~~~~~~

This configuration key points to the folder where gitolite stores and accesses
the public SSH keys of all the user have access to the server.

Since pagure is the user interface, it is pagure that writes down the files
in this directory effectively setting up the users to be able to use gitolite.


GL_RC
~~~~~

This configuration key must point to the file ``gitolite.rc`` used by gitolite
to record who has access to what (ie: who has access to which repo/branch).


GL_BINDIR
~~~~~~~~~

This configuration key indicates the folder in which the gitolite tools can
be found. It can be as simple as ``/usr/bin/`` if the tools have been installed
using a package manager or something like ``/opt/bin/`` for a more custom
install.
