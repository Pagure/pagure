Contributing
============

If you're submitting patches to pagure, please observe the following:

- Check that your python code is `PEP8-compliant
  <http://www.python.org/dev/peps/pep-0008/>`_.  There is a `flake8 tool
  <http://pypi.python.org/pypi/flake8>`_ that automatically checks the sources as
  part of the tests.

- We run the source code through `black <https://pypi.python.org/pypi/black>`_
  as part of the tests, so you may have to do some adjustments or run it
  yourself (which is simple: ``black /path/to/pagure``).

- Check that your code doesn't break the test suite.  The test suite can be
  run using ``tox`` at the top of the sources, you mayuse ``tox -e py38 ./test/``
  to run a single version of python. You can also run a single file by calling
  pytest directly: ``pytest-3 tests/test_style.py``.
  See :doc:`development` for more information about the test suite.

- If you are adding new code, please write tests for them in ``tests/``,
  ``tox .`` will run the tests and show you the coverage of the code by the
  unit-tests.

- If your change warrants a modification to the docs in ``doc/`` or any
  docstrings in ``pagure/`` please make that modification.

.. note:: You have a doubt, you don't know how to do something, you have an
   idea but don't know how to implement it, you just have something bugging
   you?

   Come to see us on Matrix: ``#pagure:fedora.im`` or directly on
   `the project <http://pagure.io>`_.
