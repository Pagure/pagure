Installing pagure
=================

There are two ways to install pagure:

* via the RPM package (recommanded if you are using a RPM-based linux distribution)
* via the setup.py



Installing pagure via RPM
-------------------------

Here as well there are two ways of obtaining the RPM:

* From the main repositories

Pagure is packaged for Fedora since Fedora 21 and is available for RHEL and
its derivative via the `EPEL repository <>`. So installing it is as easy as:
::

    dnf install pagure pagure-milters pagure-ev

or
::
    yum install pagure pagure-milters pagure-ev

The ``pagure`` package contains the core of the application and the doc server.
(See the ``Overview`` page for a global overview of the structure of the
project).

The ``pagure-milters`` package contains, as the name says, the milter.

The ``pagure-ev`` package contains the eventsource server.

..note: The last two packages are optional, pagure would work fine without
        them.

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


Once, the RPM is installed, the services ``pagure_milter`` and ``pagure_ev``
are ready to be used but the database and the web-application parts still
need to be configured.



Installing pagure via setup.py
------------------------------

Pagure includes in its sources a ``setup.py`` automatint the installation
of the web applications of pagure (ie: the core + the doc server).


To install pagure via this mechanism simply follow these steps:
# Clone the sources::
    git clone https://pagure.io/pagure.git

# Go to the folder::
    cd pagure

# Install the latest version of pagure::
    python setup.py build
    sudo python setup.py install

..note: To install the eventsource server or the milter, refer to their
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

Once pagure's files are installed, you still need to set-up some things.


* Create the folder release

This folder is used by project maintainers to upload the tarball of the
releases of their project.

This folder must be accessible by the user under which the application is
running (in our case: ``git``).
::

    mkdir -p /var/www/releases
    chown git:git /var/www/releases


* Configure apache

If installed by RPM, you will find an example apache configuration file
at: ``/etc/httpd/conf.d/pagure.conf``.

If not installed by RPM, the example files is present in the sources at:
``files/pagure.conf``.

Adjust it for your needs.


* Configure the WSGI file

If install by RPM, you will find an example WSGI file at:
``/usr/share/pagure/pagure.wsgi`` and ``/usr/share/pagure/docs_pagure.wsgi``
for the doc server.

If not install by RPM, these files are present in the sources at:
``files/pagure.wsgi`` and ``files/doc_pagure.wsgi``.

Adjust them for your needs


* Give apache permission to read the repositories owned by the ``git`` user.

The web application run under the ``git`` user name, the same username as
your gitolite user, but apache itself runs under the ``apache`` (or
``httpd2``) user. So apache by default, apache will not be allowed to read
git repositories created and managed by gitolite.

To give apache this permission (required to make git clone via http work),
we use facl
::
    ...
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
