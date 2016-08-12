Installing pagure
=================

There are two ways to install pagure:

* via the RPM package (recommended if you are using a RPM-based linux distribution)
* via the setup.py



Installing pagure via RPM
-------------------------

Here as well there are two ways of obtaining the RPM:

* From the main repositories

Pagure is packaged for Fedora since Fedora 21 and is available for RHEL and
its derivative via the `EPEL repository <https://fedoraproject.org/wiki/EPEL>`.
So installing it is as easy as:
::

    dnf install pagure pagure-milters pagure-ev pagure-webhook

or

::

    yum install pagure pagure-milters pagure-ev pagure-webhook

The ``pagure`` package contains the core of the application and the doc server.
(See the ``Overview`` page for a global overview of the structure of the
project).

The ``pagure-milters`` package contains, as the name says, the milter (a
mail filter to hook into a MTA).

The ``pagure-ev`` package contains the eventsource server.

The ``pagure-webhook`` package contains the web-hook server.


.. note:: The last three packages are optional, pagure would work fine without
        them but the live-update, the webhook and the comment by email
        services will not work.

* From the sources

If you wish to run a newer version of pagure than what is in the repositories
you can easily rebuild it as RPM.

Simply follow these steps:
# Clone the sources::

    git clone https://pagure.io/pagure.git

# Go to the folder::

    cd pagure

# Build a tarball of the latest version of pagure::

    python setup.py sdist

# Build the RPM::

    rpmbuild -ta dist/pagure*.tar.gz

This will build pagure from the version present in your clone.


Once, the RPM is installed the services ``pagure_milter`` and ``pagure_ev``
are ready to be used but the database and the web-application parts still
need to be configured.



Installing pagure via setup.py
------------------------------

Pagure includes in its sources a ``setup.py`` automating the installation
of the web applications of pagure (ie: the core + the doc server).


To install pagure via this mechanism simply follow these steps:
# Clone the sources::

    git clone https://pagure.io/pagure.git

# Go to the folder::

    cd pagure

# Install the latest version of pagure::

    python setup.py build
    sudo python setup.py install

.. note:: To install the eventsource server or the milter, refer to their
        respective documentations.

# Install the additional files as follow:

+------------------------------+------------------------------------------+
|         Source               |             Destination                  |
+=============================+===========================================+
| ``files/pagure.cfg.sample``  | ``/etc/pagure/pagure.cfg``               |
+------------------------------+------------------------------------------+
| ``files/alembic.ini``        | ``/etc/pagure/alembic.ini``              |
+------------------------------+------------------------------------------+
| ``files/pagure.conf``        | ``/etc/httpd/conf.d/pagure.conf``        |
+------------------------------+------------------------------------------+
| ``files/pagure.wsgi``        | ``/usr/share/pagure/pagure.wsgi``        |
+------------------------------+------------------------------------------+
| ``createdb.py``              | ``/usr/share/pagure/pagure_createdb.py`` |
+------------------------------+------------------------------------------+



Set-up pagure
-------------

Once pagure's files are installed, you still need to set up some things.


* Create the folder release

This folder is used by project maintainers to upload the tarball of the
releases of their project.

This folder must be accessible by the user under which the application is
running (in our case: ``git``).
::

    mkdir -p /var/www/releases
    chown git:git /var/www/releases


* Create the folders where the repos, forks and checkouts will be stored

Pagure stores the sources of a project in a git repo, offers a place to
store the project's documentation in another repo, stores a JSON dump of all
issues and of all pull-requests in another two repos, and keeps a local
checkout of remote projects when asked to do remote pull-requests.
All these repositories are stored in different folders that must be
created manually.

For example you can place them under ``/srv/git/repositories/`` which would
make ``/srv/git`` the home of your gitolite user.

You would then create the folders with:
::

    mkdir /srv/git/repositories/{docs,forks,tickets,requests,remotes}


* Configure apache

If installed by RPM, you will find an example apache configuration file
at: ``/etc/httpd/conf.d/pagure.conf``.

If not installed by RPM, the example file is present in the sources at:
``files/pagure.conf``.

Adjust it for your needs.


* Configure the WSGI file

If you installed by RPM, you will find example WSGI files at:
``/usr/share/pagure/pagure.wsgi`` for the core server and ``/usr/share/pagure/docs_pagure.wsgi``
for the doc server.

If you did not install by RPM, these files are present in the sources at:
``files/pagure.wsgi`` and ``files/doc_pagure.wsgi``.

Adjust them for your needs


* Give apache permission to read the repositories owned by the ``git`` user.

For the sake of this document, we assume that the web application runs under
the ``git`` user, the same user as your gitolite user, but apache itself
runs under the ``httpd`` (or ``apache2``) user. So by default, apache
will not be allowed to read git repositories created and managed by gitolite.

To give apache this permission (required to make git clone via http work),
we use file access control lists (aka FACL):
::

    setfacl -m user:apache:rx --default
    setfacl -Rdm user:apache:rx /srv/git
    setfacl -Rm user:apache:rx /srv/git

Where ``/srv/git`` is the home of your gitolite user (which will thus need
to be adjusted for your configuration).


* Set up the configuration file of pagure

This is an important step which concerns the file ``/etc/pagure/pagure.cfg``.
If you have installed pagure by RPM, this file is already there, otherwise
you can find an example one in the sources at: ``files/pagure.cfg.sample``
that you will have to copy to the right location.

Confer the ``Configuration`` section of this documentation for a full
explanation of all the options of pagure.

* Create the database

You first need to create the database itself. For this, since pagure can
work with: `PostgreSQL <http://www.postgresql.org/>`_,
`MySQL <http://www.mysql.com/>`_ or `MariaDB <http://mariadb.org/>`_, we
would like to invite you to consult the documentation of your database system
for this operation.

Once you have specified in the configuration file the to url used to connect
to the database, and create the database itself, you can now create the
tables, the database scheme.

To create the database tables, you need to run the script
``/usr/share/pagure/pagure_createdb.py`` and specify the configuration
file to use via an environment variable.

For example:
::

    PAGURE_CONFIG=/etc/pagure/pagure.cfg python /usr/share/pagure/pagure_createdb.py

This will tell ``/usr/share/pagure/pagure_createdb.py`` to use the database
information specified in the file ``/etc/pagure/pagure.cfg``.

.. warning:: Pagure's default configuration is using sqlite. This is fine
        for development purpose but not for production use as sqlite does
        not support all the operations needed when updating the database
        schema. Do use PostgreSQL, MySQL or MariaDB in production.

* Stamp the alembic revision

For changes to existing tables, we rely on `Alembic <http://alembic.readthedocs.org/>`_.
It uses `revisions` to perform the upgrades, but to know which upgrades are
needed and which are already done, the current revision needs to be saved
in the database. This will allow alembic to know apply the new revision when
running it.

You can save the current revision in the database using the following command:
::

    cd /etc/pagure
    alembic stamp $(alembic heads |awk '{ print $1 }')

The ``cd /etc/pagure`` is needed as the command must be run in the folder
where the file ``alembic.ini`` is. This file contains two important pieces
of information:

* ``sqlalchemy.url`` which is the URL used to connect to the database, likely
  the same URL as the one in ``pagure.cfg``.

* ``script_location`` which is the path to the ``versions`` folder containing
  all the alembic migration files.

The ``alembic stamp`` command is the one actually saving the current revision
into the database. This current revision is found using ``alembic heads``
which returns the most recent revision found by alembic, and since the
database was just created, it is at the latest revision.


Set up virus scannining
-----------------------
Pagure can automatically scan uploaded attachments for viruses using Clam.
To set this up, first install clamav-data-empty, clamav-server,
clamav-server-systemd and clamav-update.

Then edit /etc/freshclam.conf, removing the Example line and run freshclam once
to get an up to date database.

Copy /usr/share/doc/clamav-server/clamd.conf to /etc/clamd.conf and edit that
too, again making sure to remove the Example line. Make sure to set LocalSocket
to a file in a directory that exists, and set User to an existing system user.

Then start the clamd service and set VIRUS_SCAN_ATTACHMENTS = True in the
Pagure configuration.
