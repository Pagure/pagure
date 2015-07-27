Installing pagure's EventSource server
======================================

Eventsource or Server Sent Events are messages sent from a server to a web
browser. It allows to refresh a page "live", ie, without the need to reload
it entirely.


Configure your system
---------------------

The eventsource server is easy to set-up.

* Installed the required dependencies
::

    python-redis
    python-trollius
    python-trollius-redis
    systemd


..note: This last one is necessary if you want to use the service file provided.
        Otherwise, you will have to write your own.

* Install the files of the SSE server as follow:

+----------------------------------------+-----------------------------------------------------+
|              Source                    |                   Destination                       |
+========================================+=====================================================+
| ``ev-server/pagure-stream-server.py``  | ``/usr/libexec/pagure-ev/pagure-stream-server.py``  |
+----------------------------------------+-----------------------------------------------------+
| ``ev-server/pagure_ev.service``        | ``/usr/lib/systemd/system/pagure_ev.service``       |
+----------------------------------------+-----------------------------------------------------+

The first file is the script of the SSE server itself.

The second file is the systemd service file.


* Finally, activate the service and ensure it's started upon boot:
::

    systemctl enable pagure_ev
    systemctl start pagure_ev
