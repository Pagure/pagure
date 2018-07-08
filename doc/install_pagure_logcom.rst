Installing pagure-logcom
========================

pagure-logcom is the service that updates the log table in the database
for every commit made to the main branch of a repository allowing to build
the calendar heatmap presented on every user's page.


Configure your system
---------------------

* Install the required dependencies

::

    python-redis
    python-trollius

.. note:: We ship a systemd unit file for pagure_logcom but we welcome patches
        for scripts for other init systems.


* Install the files of pagure-loadjon as follow:

+-----------------------------------------------+-------------------------------------------------------+
|              Source                           |                   Destination                         |
+===============================================+=======================================================+
| ``pagure-logcom/pagure_logcom_server.py``     | ``/usr/libexec/pagure-logcom/pagure_logcom_server.py``|
+--------------------------------------------------+----------------------------------------------------+
| ``pagure-logcom/pagure_logcom.service``       | ``/etc/systemd/system/pagure_logcom.service``         |
+-----------------------------------------------+-------------------------------------------------------+

The first file is the pagure-logcom service itself, triggered by the git
hook (shipped with pagure itself) and logging the commits into the database.

The second file is the systemd service file.


* Activate the service and ensure it's started upon boot:

::

    systemctl enable redis
    systemctl start redis
    systemctl enable pagure_logcom
    systemctl start pagure_logcom
