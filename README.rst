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

There are several options when it comes to a development environment.
They are: Docker Compose, Vagrant, and manual. Choose an option below.

Docker Compose
^^^^^^^^^^^^^^
Docker Compose will provide you with a container which you can develop on.
Install it `with these instructions <https://docs.docker.com/compose/install/>`_.

For more information about docker-compose cli, see: https://docs.docker.com/compose/reference/.

To build and run the containers, use the following command::

    $ ./dev/docker-start.sh

Once all the containers have started, you can access pagure on http://localhost:5000.
To stop the containers, press Ctrl+C.

Once the containers are up and running, run this command to populate the
container with test data and create a new account ::

    $ docker-compose -f dev/docker-compose.yml exec web python3 dev-data.py --all

You can then login with any of the created users, by example:

- username: pingou
- password: testing123

Vagrant
^^^^^^^

For a more thorough introduction to Vagrant, see
https://fedoraproject.org/wiki/Vagrant.

An example Vagrantfile is provided as ``Vagrantfile.example``. To use it,
just copy it and install Vagrant. Instructions for Fedora::

    $ cp dev/Vagrantfile.example Vagrantfile
    $ sudo dnf install ansible libvirt vagrant-libvirt vagrant-sshfs vagrant-hostmanager
    $ vagrant up

On Ubuntu, install Vagrant directly `from the website <https://www.vagrantup.com/downloads.html>`_
then run these commands instead::

    $ cp dev/Vagrantfile.example Vagrantfile
    $ sudo add-apt-repository ppa:ansible/ansible
    $ sudo apt update
    $ sudo apt install ansible libvirt0 openssh-server qemu libvirt-bin ebtables dnsmasq libxslt-dev libxml2-dev libvirt-dev zlib1g-dev ruby-dev
    $ vagrant plugin install vagrant-libvirt vagrant-sshfs vagrant-hostmanager

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

When the vagrant VM is up and running, connect to it with::

    $ vagrant ssh

This will log you into the VM as the user ``vagrant`` which has a couple of aliases
preconfigured::

    $ pstart            # Starts pagure, the workers and other tasks
    $ pstop             # Stops all those tasks again
    $ pstatus           # Shows pagure status

The Vagrant pagure doesn't have its own log file, use ``journalctl -f`` to
show the pagure output. The verbosity can be configured in the pagure config file
with the ``LOGGING`` parameter.

Running the unit-tests in container
***********************************

To run the unit-tests, there are containers available with all the dependencies needed.

First you will need to have podman and git installed on your workstation. ::

    $ sudo dnf install podman git

Use the following command to run all tests on all container images, if the images not exist on your system, they will be build ::

    $ ./dev/run-tests-container.py

If you wish to execute the test suite on a centos based container run the following command ::

    $ ./dev/run-tests-container.py --centos

Container images are separated from the pagure source that will be tested.
Therefore they will only automatically build if they not exist.

A manual rebuild should be done from time to time to include new package versions.
Also if you work on any changes in the pagure spec file, the tox config or any requirements.txt file,
perform a rebuild to ensure your changed will taken into account. ::

    $ ./dev/run-tests-container.py --rebuild # all base and code container
    $ ./dev/run-tests-container.py --rebuild-code # code container only

You can also run a single test case ::

    $ ./dev/run-tests-container.py tests/test_pagure_flask_ui_priorities.py

Or a single test ::

    $ ./dev/run-tests-container.py tests/test_pagure_flask_ui_priorities.py:PagureFlaskPrioritiestests.test_ticket_with_no_priority

You can also get ``run-tests-container`` help ::

    $ ./dev/run-tests-container.py --help

By default, tests run against the git repo and the active branch in the current folder.
To override this behavior and run the tests on your remote development branch in your fork ::

    $ ./dev/run-tests-container.py --repo https://pagure.io/forks/<username>/pagure.git --branch <name of branch to test>

  .. note:: All build, test and shell activities executed via ``run-tests-container`` will automatically be logged.
            Every container has it's own ``dev/results_<test-container-name>`` folder, every run creates separate
            files with the current unix timestamp as prefix. You should cleanup this folder from time to time.

 
Running the unit-tests in tox
*****************************

You can run the tests using tox. This allows you to run the tests on local version of the code.

  .. note:: This way of running tests could help you test your local changes,
            but the output could be different then from the containerized tests.
            Always check your branch after push with containerized tests as well.

* Install the needed system libraries::

     sudo dnf install libgit2-devel redis gcc tox python-alembic


  .. note:: You can also install any missing python interpreter.
            For example `sudo dnf install python35`

* Run the whole test suite::

     tox

* Or just single environment::

     tox -e py39

* Or single module::

     tox tests/test_style.py

Manually
^^^^^^^^

* Install the needed system libraries::

    sudo dnf install git python3 python3-devel libgit2-devel redis \
                     libjpeg-devel gcc libffi-devel redhat-rpm-config

  .. note:: Do note the version of libgit2 that you install, for example
            in ``libgit2-0.26.8-1`` you need to keep in mind the ``0.26``

  .. note:: On RHEL and derivative (CentOS, Scientific Linux) there is no
            `python3` package. Just `python36` or `python34` available in
            EPEL 7 (EPEL 6 only has `python34`). Choose the one you prefer
            (3.6 is newer and generally a better choice).

* Retrieve the sources::

    git clone https://pagure.io/pagure.git
    cd pagure

* Install dependencies

  * create the virtual environment (use `python3.X` explicitly on EPEL)::

      python3 -m venv pagure_env
      source ./pagure_env/bin/activate

  * Install the correct version of pygit2::

      pip install pygit2==<version of libgit2 found>.*

    So in our example::

      pip install pygit2==0.26.*

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

    sudo systemctl enable redis
    sudo systemctl start redis

* Start a worker, in one terminal::

    ./runworker.py

* Run the application, in another terminal::

    ./runserver.py


* To get some profiling information you can also run it as::

    ./runserver.py --profile


This will launch the application at http://127.0.0.1:5000

* To run unit-tests on pagure

  * Install the dependencies::

      pip install -r requirements-testing.txt

  * Run it::

      pytest tests/

    .. note:: While testing for worker tasks, pagure uses celery in /usr/bin/
            Celery then looks for eventlet (which we use for testing only) at
            system level and not in virtual environment. You will need to
            install eventlet outside of your virtual environment if you are
            using one.

    .. note:: This will also work in vagrant.
