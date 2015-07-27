Installing pagure's milter
==========================

A milter is a script that is ran by a MTA upon receiving an email via either
a network or an unix socket.

If you want more information feel free to check out the corresponding page
on wikipedia `https://en.wikipedia.org/wiki/Milter <https://en.wikipedia.org/wiki/Milter>`_.

Configure your system
---------------------

* Create an alias ``reply``

This can be done in ``/etc/aliases``, for example:
::

    reply:      /dev/null


* Activate the ability of you MTA, to split users based on the character ``+``.
  This way all the emails sent to ``reply+...@example.com`` will be forwarded
  to your alias for ``reply``.


In postfix this is done via:
::

    recipient_delimiter = +

* Hook the milter in the MTA

In postfix this is done via:
::

    non_smtpd_milters = unix:/var/run/pagure/paguresock
    smtpd_milters = unix:/var/run/pagure/paguresock


* Install the files of the milter as follow:

+--------------------------------------+---------------------------------------------------+
|              Source                  |                   Destination                     |
+======================================+===================================================+
| ``milters/comment_email_milter.py``  | ``/usr/share//pagure/comment_email_milter.py``    |
+----------------------------------------+-------------------------------------------------+
| ``milters/milter_tempfile.conf``     | ``/usr/lib/tmpfiles.d/pagure-milter.conf``        |
+----------------------------------------+-------------------------------------------------+
| ``milters/pagure_milter.service``    | ``/usr/lib/systemd/system/pagure_milter.service`` |
+--------------------------------------+---------------------------------------------------+

The first file is the script of the milter itself.

The second file is a file specific for systemd and ensuring the temporary
folders needed by the milter are re-created if needed at each boot.

The third file is the systemd service file.


* Activate the service and ensure it's started upon boot:
::

    systemctl enable pagure_milter
    systemctl start pagure_milter
