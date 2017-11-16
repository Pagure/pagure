
.. _flags:

Flags
=====

Pagure offers the possibility to flag pull-requests and commits. A flag
is a way for a third-party tool to provide feedback on a pull-request or a
commit.

This feedback can be as simple as the outcome of running the tests, or some
lint tool, or test coverage evolution.


Add a flag
----------

Flags can be set via the API, see the ``/api/`` url in your pagure instance
or at `pagure.io/api/ <https://pagure.io/api/0/>`_ and look for the endpoints
with the titles: ``Flag a commit`` or ``Flag a pull-request``.


.. _example_flag_commit:

Example of two flags on a commit:
---------------------------------

.. image:: _static/pagure_commit_flag.png
        :target: ../_images/pagure_commit_flag.png


.. _example_flag_pr:

Example of two flags on a pull-request:
---------------------------------------

.. image:: _static/pagure_flag_pr.png
        :target: ../_images/pagure_flag_pr.png
