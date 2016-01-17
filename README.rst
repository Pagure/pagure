Pagure
======

:Author: Pierre-Yves Chibon <pingou@pingoured.fr>


Pagure is a light-weight git-centered forge based on pygit2.

Currently, Pagure offers a decent web-interface for git repositories, a
simplistic ticket system (that needs improvements) and possibilities to create
new projects, fork existing ones and create/merge pull-requests across or
within projects.


Homepage: https://pagure.io/pagure

See it at work: https://pagure.io

Playground version: https://stg.pagure.io



Get it running
==============

* Retrieve the sources::

    git clone https://pagure.io/pagure.git
    cd pagure


* Install dependencies

  * development virtualenv::

      dnf install libgit2-devel
      virtualenv devel
      devel/bin/pip install -r requirements.txt

  * Fedora RPMs::

      dnf install $(cat requirements-fedora.txt)


* Create the folder that will receive the projects, forks, docs and tickets'
  git repo::

    mkdir {repos,docs,forks,tickets}


* Create the inital database scheme::

    # development virtualenv only
    source devel/bin/activate

    python createdb.py


* Run it::

    # development virtualenv only
    source devel/bin/activate

    ./runserver.py


* To get some profiling information you can also run it as::

    # development virtualenv only
    source devel/bin/activate

    ./runserver.py --profile


This will launch the application at http://127.0.0.1:5000
