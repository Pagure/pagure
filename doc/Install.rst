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
