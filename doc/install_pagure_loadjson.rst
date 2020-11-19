Installing pagure-loadjson
==========================

pagure-loadjson is the service that updates the database based on the content
of the JSON blob pushed into the ticket git repository (and in the future
for pull-requests as well).


Configure your system
---------------------

* Install the required dependencies

::

    python-redis

.. note:: We ship a systemd unit file for pagure_loadjson but we welcome patches
        for scripts for other init systems.


* Install the files of pagure-loadjon as follow:

+--------------------------------------------------+----------------------------------------------------+
|              Source                              |                   Destination                      |
+==================================================+====================================================+
| ``pagure-loadjson/pagure_loadjson_server.py``    | ``/usr/libexec/pagure-loadjson/pagure_loadjson.py``|
+--------------------------------------------------+----------------------------------------------------+
| ``pagure-loadjson/pagure_loadjson.service``      | ``/etc/systemd/system/pagure_loadjson.service``    |
+--------------------------------------------------+----------------------------------------------------+

The first file is the pagure-loadjson service itself, triggered by the git
hook (shipped with pagure itself) and loading the JSON files into the database.

The second file is the systemd service file.


* Activate the service and ensure it's started upon boot:

::

    systemctl enable redis
    systemctl start redis
    systemctl enable pagure_loadjson
    systemctl start pagure_loadjson
