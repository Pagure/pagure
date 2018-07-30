Installing pagure-ci
====================

A CI stands for `Continuous Integration
<https://en.wikipedia.org/wiki/Continuous_integration>`_. Pagure can be
configured to integrate results coming from CI services, such as `Jenkins
<https://en.wikipedia.org/wiki/Jenkins_(software)>`_ on pull-request opened
against the project.


.. note: Currently, pagure only supports `Jenkins` but we welcome help to
  integrate pagure with other services such as `travis-ci
  <https://en.wikipedia.org/wiki/Travis_CI>`_.


Configure your system
---------------------

* Install the required dependencies

::

    python-jenkins
    python-redis
    python-trololio

.. note:: We ship a systemd unit file for pagure_ci but we welcome patches
        for scripts for other init systems.


* Install the files of pagure-ci as follow:

+--------------------------------------+---------------------------------------------------+
|              Source                  |                   Destination                     |
+======================================+===================================================+
| ``pagure-ci/pagure_ci_server.py``    | ``/usr/libexec/pagure-ci/pagure_ci_server.py``    |
+--------------------------------------+---------------------------------------------------+
| ``pagure-ci/pagure_ci.service``      | ``/etc/systemd/system/pagure_ci.service``         |
+--------------------------------------+---------------------------------------------------+

The first file is the pagure-ci service itself, triggering the build on the
CI service when there is a new pull-request or a change to an existing one.

The second file is the systemd service file.

* Configure your pagure instance to support CI, add the following to your
  configuration file

::

    PAGURE_CI_SERVICES = ['jenkins']

* Activate the service and ensure it's started upon boot:

::

    systemctl enable redis
    systemctl start redis
    systemctl enable pagure_ci
    systemctl start pagure_ci
