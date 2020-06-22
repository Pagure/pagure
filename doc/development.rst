Development
===========

Get the sources
---------------

Anonymous:

::

  git clone https://pagure.io/pagure.git

Contributors:

::

  git clone ssh://git@pagure.io/pagure.git


Dependencies
------------

Install the build dependencies of pagure:

::

  sudo dnf install git python-virtualenv libgit2-devel \
                   libjpeg-devel gcc libffi-devel redhat-rpm-config


The python dependencies of pagure are listed in the file ``requirements.txt``
at the top level of the sources.

::

  virtualenv pagure_env
  source ./pagure_env/bin/activate
  pip install pygit2==<version of libgit2 found>.* # e.g. 0.23.*
  pip install -r requirements.txt


.. note:: working in a `virtualenv <http://www.virtualenv.org/en/latest/>`_
          is tricky due to the dependency on `pygit2 <http://www.pygit2.org/>`_
          and thus on `libgit2 <https://libgit2.github.com/>`_
          but the pygit2 `documentation has a solution for this
          <http://www.pygit2.org/install.html#libgit2-within-a-virtual-environment>`_.

How to run pagure
-----------------

There are several options when it comes to a development environment. Vagrant
will provide you with a virtual machine which you can develop on, you can use
a container to run pagure or you can install it directly on your host machine.
The README has detailed instructions for the different options.


Run pagure for development
--------------------------
Adjust the configuration file (secret key, database URL, admin group...)
See :doc:`configuration` for more detailed information about the
configuration.


Create the database scheme::

  ./createdb.py

Create the folder that will receive the different git repositories:

::

    mkdir {repos,docs,forks,tickets,requests,remotes}


Run the server:

::

    ./runserver.py

If you want to change some configuration key you can create a file, place
the configuration change in it and use it with

::

    ./runserver.py -c <config_file>

For example, create the file ``config`` with in it:

::

    from datetime import timedelta
    # Makes the admin session longer
    ADMIN_SESSION_LIFETIME = timedelta(minutes=20000000)

    # Use a postgresql database instead of sqlite
    DB_URL = 'postgresql://user:pass@localhost/pagure'
    # Change the OpenID endpoint
    FAS_OPENID_ENDPOINT = 'https://id.stg.fedoraproject.org'

    APP_URL = '*'
    EVENTSOURCE_SOURCE = 'http://localhost:8080'
    EVENTSOURCE_PORT = '8080'
    DOC_APP_URL = '*'

    # Avoid sending email when developing
    EMAIL_SEND = False

and run the server with:

::

    ./runserver.py -c config

To get some profiling information you can also run it as:

::

    ./runserver.py --profile


You should be able to access the server at http://localhost:5000


Every time you save a file, the project will be automatically restarted
so you can see your change immediately.



Create a pull-request for testing
----------------------------------

When working on pagure, it is pretty often that one wanted to work on a
feature or a bug related to pull-requests needs to create one.

Making a pull-request for development purposes isn't hard, if you remember
that since you're running a local instance, the git repos created in your
pagure instance are also local.

So here are in a few steps that one could perform to create a pull-request in a
local pagure instance.

* Create a project on your pagure instance, let's say it will be called ``test``

* Create a folder ``clones`` somewhere in your system (you probably do not
  want it in the ``repos`` folder created above, next to it is fine though)::

    mkdir clones

* Clone the repo of the ``test`` project into this ``clones`` folder and move into it::

    cd clones
    git clone ~/path/to/pagure/repos/test.git
    cd test

* Add and commit some files::

    echo "*~" > .gitignore
    git add .gitignore
    git commit -m "Add a .gitignore file"
    echo "BSD" > LICENSE
    git add LICENSE
    git commit -m "Add a LICENSE file"

* Push these changes::

    git push -u origin master

* Create a new branch and add a commit in it::

    git branch new_branch
    git checkout new_branch
    touch test
    git add test
    git commit -m "Add file: test"

* Push this new branch::

    git push -u origin new_branch


Then go back to your pagure instance running in your web-browser, check the
``test`` project. You should see two branches: ``master`` and ``new_branch``.
From there you should be able to open a new pull-request, either from the
front page or via the ``File Pull Request`` button in the ``Pull Requests``
page.



Coding standards
----------------

We are trying to make the code `PEP8-compliant
<http://www.python.org/dev/peps/pep-0008/>`_.  There is a `flake8 tool
<http://pypi.python.org/pypi/flake8>`_ that can automatically check
your source.

We run the source code through `black <https://pypi.python.org/pypi/black>`_
as part of the tests, so you may have to do some adjustments or run it
yourself (which is simple: ``black /path/to/pagure``).

.. note:: flake8 and black are available in Fedora:

          ::

            dnf install python3-flake8 python3-black

          or

          ::

            yum install python3-flake8 python3-black


Send patch
----------

The easiest way to work on pagure is to make your own branch in git, make
your changes to this branch, commit whenever you want, rebase on master,
whenever you need and when you are done, send the patch either by email,
via the trac or a pull-request (using git or github).


The workflow would therefore be something like:

::

   git branch <my_shiny_feature>
   git checkout <my_shiny_feature>
   <work>
   git commit file1 file2
   <more work>
   git commit file3 file4
   git checkout master
   git pull
   git checkout <my_shiny_feature>
   git rebase master
   git format-patch -2

This will create two patch files that you can send by email to submit in a ticket
on pagure, by email or after forking the project on pagure by submitting a
pull-request (in which case the last step above ``git format-patch -2`` is not
needed.

.. note:: Though not required, it’s a good idea to begin the commit message 
          with a single short (less than 50 character) line summarizing the 
          change, followed by a blank line and then a more thorough description. 
          The text up to the first blank line in a commit message is treated 
          as the commit title, and that title is used throughout Git. 
          For example, git-format-patch turns a commit into email, and it 
          uses the title on the Subject line and the rest of the commit in 
          the body.
          Pagure uses lines that contain only 'Fixes #number' as references
          to issues. If for example a commit message of a pagure patch has 
          a line 'Fixes #3547' and a pullrequest (PR) gets created in pagure, 
          this PR will be linked to from ``https://pagure.io/pagure/issue/3547``


Unit-tests
----------

Pagure has a number of unit-tests.


We aim at having a full (100%) coverage of the whole code (including the
Flask application) and of course a smart coverage as in we want to check
that the functions work the way we want but also that they fail when we
expect it and the way we expect it.


Tests checking that function are failing when/how we want are as important
as tests checking they work the way they are intended to.


So here are a few steps that one could perform to run unit-tests in a
local pagure instance. 

* Install the dependencies::

     pip install -r requirements-testing.txt

* Run it::

     tox ./test/

If you want to run a single interpreter, cou can use::

     tox -e py38 ./test/


Each unit-tests files (located under ``tests/``) can be called
by alone, allowing easier debugging of the tests. For example:

::

   pytest-3 tests/test_pagure_lib.py


.. note:: In order to have coverage information you might have to install
          ``python-coverage``

          ::

            dnf install python3-pytest-cov


To run the unit-tests, there is also a container available with all the dependencies needed.
Use the following command to run the tests ::

    $ ./dev/run-tests-container.py

This command will build a fedora based container and execute the test suite.
You can also limit the tests to unit-test files or single tests similar to the 
options described above. You need set the environment variables REPO and BRANCH
if the tests are not yet available in the upstream pagure master branch.

