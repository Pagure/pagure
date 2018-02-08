Contributing
============

If you're submitting patches to pagure, please observe the following:

- Check that your python code is `PEP8-compliant
  <http://www.python.org/dev/peps/pep-0008/>`_.  There is a `pep8 tool
  <http://pypi.python.org/pypi/pep8>`_ that can automatically check
  your source.

- Check that your code doesn't break the test suite.  The test suite can be
  run using the ``runtests.sh`` shell script at the top of the sources.
  See :doc:`development` for more information about the test suite.

- If you are adding new code, please write tests for them in ``tests/``,
  the ``runtests.sh`` script will help you to see the coverage of your code
  in unit-tests.

- If your change warrants a modification to the docs in ``doc/`` or any
  docstrings in ``pagure/`` please make that modification.

.. note:: You have a doubt, you don't know how to do something, you have an
   idea but don't know how to implement it, you just have something bugging
   you?

   Come to see us on IRC: ``#pagure`` or ``#fedora-apps`` on
   irc.freenode.net or directly on `the project <http://pagure.io>`_.
