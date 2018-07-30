Installing pagure's EventSource server
======================================

Eventsource or Server Sent Events are messages sent from a server to a web
browser. It allows one to refresh a page "live", ie, without the need to reload
it entirely.


Configure your system
---------------------

The eventsource server is easy to set-up.

* Install the required dependencies

::

    python-redis
    python-trololio

.. note:: We ship a systemd unit file for pagure_milter but we welcome patches
        for scripts for other init systems.


* Install the files of the SSE server as follow:

+----------------------------------------+-----------------------------------------------------+
|              Source                    |                   Destination                       |
+========================================+=====================================================+
| ``pagure-ev/pagure_stream_server.py``  | ``/usr/libexec/pagure-ev/pagure_stream_server.py``  |
+----------------------------------------+-----------------------------------------------------+
| ``pagure-ev/pagure_ev.service``        | ``/etc/systemd/system/pagure_ev.service``           |
+----------------------------------------+-----------------------------------------------------+

The first file is the script of the SSE server itself.

The second file is the systemd service file.


* Finally, activate the service and ensure it's started upon boot:

::

    systemctl enable redis
    systemctl start redis
    systemctl enable pagure_ev
    systemctl start pagure_ev
