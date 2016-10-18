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

* Install the needed system libraries::

    sudo dnf install git python2-virtualenv libgit2-devel \
                     libjpeg-devel gcc libffi-devel redhat-rpm-config

  .. note:: Do note the version of libgit2 that you install, for example
            in ``libgit2-0.23.4-1`` you need to keep in mind the ``0.23``

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

    mkdir {repos,docs,forks,tickets,requests}


* Create the inital database scheme::

    python createdb.py


* Run it::

    ./runserver.py


* To get some profiling information you can also run it as::

    ./runserver.py --profile


This will launch the application at http://127.0.0.1:5000
