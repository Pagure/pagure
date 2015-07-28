Development
===========

Get the sources
---------------

Anonymous:

::

  git clone https://pagure.io/pagure.git

Contributors:

::

  git clone ssh://git@pagure.io:pagure.git


Dependencies
------------

The dependencies of pagure are listed in the file ``requirements.txt``
at the top level of the sources.


.. note:: working in a `virtualenv <http://www.virtualenv.org/en/latest/>`_
          is tricky due to the dependency on `pygit2 <http://www.pygit2.org/>`_
          and thus on `libgit2 <https://libgit2.github.com/>`_
          but the pygit2 `documentation has a solution for this
          <http://www.pygit2.org/install.html#libgit2-within-a-virtual-environment>`_.


Run pagure for development
-------------------------
Adjust the configuration file (secret key, database URL, admin group...)
See :doc:`configuration` for more detailed information about the
configuration.


Create the database scheme::

  ./createdb

Create the folder that will receive the different git repositories:

::

    mkdir {repos,docs,forks,tickets,requests,remotes}


Run the server:

::

    ./runserver

To get some profiling information you can also run it as:

::
    ./runserver.py --profile


You should be able to access the server at http://localhost:5000


Every time you save a file, the project will be automatically restarted
so you can see your change immediatly.



Coding standards
----------------

We are trying to make the code `PEP8-compliant
<http://www.python.org/dev/peps/pep-0008/>`_.  There is a `pep8 tool
<http://pypi.python.org/pypi/pep8>`_ that can automatically check
your source.


We are also inspecting the code using `pylint
<http://pypi.python.org/pypi/pylint>`_ and aim of course for a 10/10 code
(but it is an assymptotic goal).

.. note:: both pep8 and pylint are available in Fedora via yum:

          ::

            yum install python-pep8 pylint


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


Unit-tests
----------

Pagure has a number of unit-tests.


We aim at having a full (100%) coverage of the whole code (including the
Flask application) and of course a smart coverage as in we want to check
that the functions work the way we want but also that they fail when we
expect it and the way we expect it.


Tests checking that function are failing when/how we want are as important
as tests checking they work the way they are intended to.

``runtests.sh``, located at the top of the sources, helps to run the
unit-tests of the project with coverage information using `python-nose
<https://nose.readthedocs.org/>`_.


.. note:: You can specify additional arguments to the nose command used
          in this script by just passing arguments to the script.

          For example you can specify the ``-x`` / ``--stop`` argument:
          `Stop running tests after the first error or failure` by just doing

          ::

            ./runtests.sh --stop


Each unit-tests files (located under ``tests/``) can be called
by alone, allowing easier debugging of the tests. For example:

::

  python tests/test_pragure_lib.py


.. note:: In order to have coverage information you might have to install
          ``python-coverage``

          ::

            yum install python-coverage
