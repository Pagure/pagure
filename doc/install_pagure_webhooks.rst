Installing pagure's web-hooks notification system
=================================================

Web-hooks are a notification system upon which a system makes a http POST
request with some data upon doing an action. This allows notifying a system
that an action has occurred.

If you want more information feel free to check out the corresponding page
on wikipedia: `https://en.wikipedia.org/wiki/Webhook
<https://en.wikipedia.org/wiki/Webhook>`_.

Configure your system
---------------------

* Install the required dependencies

::

    python-redis

.. note:: We ship a systemd unit file for pagure_webhook but we welcome patches
        for scripts for other init systems.


* Install the files of the web-hook server as follow:

+----------------------------------------------+----------------------------------------------------------+
|              Source                          |                       Destination                        |
+==============================================+==========================================================+
| ``pagure-webhook/pagure-webhook-server.py``  | ``/usr/libexec/pagure-webhook/pagure-webhook-server.py`` |
+----------------------------------------------+----------------------------------------------------------+
| ``pagure-webhook/pagure_webhook.service``    | ``/etc/systemd/system/pagure_webhook.service``           |
+----------------------------------------------+----------------------------------------------------------+

The first file is the script of the web-hook server itself.

The second file is the systemd service file.


* Activate the service and ensure it's started upon boot:

::

    systemctl enable redis
    systemctl start redis
    systemctl enable pagure_webhook
    systemctl start pagure_webhook
