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

    $ cp Vagrantfile.example Vagrantfile
    $ sudo dnf install ansible libvirt vagrant-libvirt vagrant-sshfs vagrant-hostmanager
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


Manually
^^^^^^^^

* Install the needed system libraries::

    sudo dnf install git python2-virtualenv libgit2-devel \
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

    mkdir -p lcl/{repos,docs,forks,tickets,requests,remotes,attachments}


* Create the inital database scheme::

    python createdb.py

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
