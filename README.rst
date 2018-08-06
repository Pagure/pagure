Pagure
======

:Author:  Pierre-Yves Chibon <pingou@pingoured.fr>


Pagure is a git-centered forge, python based using pygit2.

With pagure you can host your project with its documentation, let your users
report issues or request enhancements using the ticketing system and build your
community of contributors by allowing them to fork your projects and contribute
to it via the now-popular pull-request mechanism.


Homepage: https://pagure.io/pagure

See it at work: https://pagure.io


Playground version: https://stg.pagure.io

If you have any questions or just would like to discuss about pagure,
feel free to drop by on IRC in the channel ``#pagure`` of the freenode server


About its name
==============

The name Pagure is taken from the French word 'pagure'. Pagure in French is used as the
common name for the crustaceans from the `Paguroidea <https://en.wikipedia.org/wiki/Hermit_crab>`_
superfamily, which is basically the family of the Hermit crabs.

Originating from French it is pronounced with a strong 'g' as you can hear
on `this recording <https://pagure.io/how-do-you-pronounce-pagure/raw/master/f/pingou.ogg>`_.


Get it running
==============

There are several options when it comes to a development environment. Vagrant
will provide you with a virtual machine which you can develop on, or you can
install it directly on your host machine.

Vagrant
^^^^^^^

For a more thorough introduction to Vagrant, see
https://fedoraproject.org/wiki/Vagrant.

An example Vagrantfile is provided as ``Vagrantfile.example``. To use it,
just copy it and install Vagrant::

    $ cp dev/Vagrantfile.example Vagrantfile
    $ sudo dnf install ansible libvirt vagrant-libvirt vagrant-sshfs vagrant-hostmanager
    $ vagrant up

If you get this error ``Block in synced_folders: Internal error. Invalid: sshfs``,
when you run ``vagrant up`` , you need to install vagrant sshfs plugin, which can be done by::

    $ vagrant plugin install vagrant--sshfs

and then::

    $ vagrant up

The default ``Vagrantfile`` forwards ports from the host to the guest,
so you can interact with the application as if it were running on your
host machine.

.. note::
    ``vagrant-hostmanager`` will automatically maintain /etc/hosts for you so you
    can access the development environment from the host using its hostname, which
    by default is ``pagure-dev.example.com``. You can choose not to use this
    functionality by simply not installing the ``vagrant-hostmanager`` plugin, but
    if you want Pagure to provide valid URLs in the UI for git repositories, you
    will need to adjust Pagure's configuration found in ~/pagure.cfg on the guest.

Docker Compose
^^^^^^^^^^^^^^
Create the folder that will receive the projects, forks, docs, requests and
tickets' git repo::

    mkdir -p lcl/{repos,remotes,attachments,releases}

A docker compose environment is available to run pagure. First use the following
command to build the containers. ::

    $ docker-compose -f dev/docker-compose.yml build

Once all the containers are built, run the following command to start the containers. ::

    $ docker-compose -f dev/docker-compose.yml up -d

Once all the containers have started, you can access pagure on http://localhost:5000

To stop the containers, run the following ::

    $ docker-compose -f dev/docker-compose.yml stop

More information about docker-compose cli see https://docs.docker.com/compose/reference/.

Running the unit-tests
**********************

To run the unit-tests, there is container available with all the dependencies needed.

Use the following command to run the tests ::

    $ ./dev/run-tests-docker.py

This command will build a fedora based container and execute the test suite.

If you wish to execute the test suite on a centos based container run the following command ::

    $ ./dev/run-tests-docker.py --centos

When the test container image has been built you can skip the building step to save time
and run directly the test suite. ::

    $ ./dev/run-tests-docker.py --skip-build
    $ ./dev/run-tests-docker.py --centos --skip-build

You can also run a single test case ::

    $ ./dev/run-tests-docker.py tests/test_pagure_flask_ui_priorities.py

Or a single test ::

    $ ./dev/run-tests-docker.py tests/test_pagure_flask_ui_priorities.py:PagureFlaskPrioritiestests.test_ticket_with_no_priority

You can also get `run-tests-docker` help ::

    $ ./dev/run-tests-docker.py --help

Manually
^^^^^^^^

* Install the needed system libraries::

    sudo dnf install git python2-virtualenv libgit2-devel redis \
                     libjpeg-devel gcc libffi-devel redhat-rpm-config

  .. note:: Do note the version of libgit2 that you install, for example
            in ``libgit2-0.23.4-1`` you need to keep in mind the ``0.23``


  .. note:: On Fedora 23 and earlier or on RHEL and derivative (CentOS,
            Scientific Linux) the package `python2-virtualenv` is named
            `python-virtualenv`

* Retrieve the sources::

    git clone https://pagure.io/pagure.git
    cd pagure

* Install dependencies

  * create the virtualenv::

      virtualenv pagure_env
      source ./pagure_env/bin/activate

  * Install the correct version of pygit2::

      pip install pygit2==<version of libgit2 found>.*

    So in our example::

      pip install pygit2==0.23.*

  * Install the rest of the dependencies::

      pip install -r requirements.txt


* Create the folder that will receive the projects, forks, docs, requests and
  tickets' git repo::

    mkdir -p lcl/{repos,remotes,attachments,releases}

* Copy and edit the alembic.ini file (especially the ``script_location`` key)::

    cp files/alembic.ini .
    vim alembic.ini

* Set the ``script_location`` to ``alembic``, ie: the folder where the revisions
  are stored, relative to the location of the ``alembic.ini`` file.

* Create the inital database scheme::

    python createdb.py --initial alembic.ini

* Enable and start redis server::

    systemctl enable redis
    systemctl start redis

* Start a worker, in one terminal::

    ./runworker.py

* Run the application, in another terminal::

    ./runserver.py


* To get some profiling information you can also run it as::

    ./runserver.py --profile


This will launch the application at http://127.0.0.1:5000


* To run unit-tests on pagure

  * Install the dependencies::

      pip install -r tests_requirements.txt

  * Run it::

      ./runtests.sh

    .. note:: While testing for worker tasks, pagure uses celery in /usr/bin/
            Celery then looks for eventlet (which we use for testing only) at
            system level and not in virtualenv. You will need to install eventlet
            outside of your virtualenv if you are using one.
