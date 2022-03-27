Pagure CI
=========

Pagure CI is a service integrating the results of Continuous Integration (CI)
services, such as jenkins or travis-ci, into pull-requests opened against
your project on Pagure.


.. note:: By default pagure-ci is off, an admin of your Pagure instance will
    need to configure it to support one or more CI services. Check the
    configuration section on how to do that.


Contents:

.. toctree::
   :maxdepth: 2

   pagure_ci_jenkins


Tips and tricks
---------------

* How to re-trigger a run of pagure-ci on a pull-request?

To manually trigger a run of pagure-ci on a given pull-request, simply add
a comment saying: ``pretty please pagure-ci rebuild``.

.. note:: To always have this handy, you can save it in the ``Quick Replies``!

.. note:: This trigger can also be configured per Pagure instance via the
          configuration file.
