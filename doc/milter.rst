Pagure's Milter
===============

`Milter<http://www.postfix.org/MILTER_README.html>`_ are script executed by
postfix upon sending or receiving an email.

We use this system to allow pagure's users to comment on a ticket (or a
pull-request) by directly replying to the email sent as a notification.

Pagure's milter is designed to be run on the same machine as the mail server
(postfix by default). Postfix connecting to the milter via a unix socket.

The milter itself is a service managed by systemd.
You can find all the relevant files for the milter under the ``milters`` folder
in the sources.


Install the milter
------------------

The first step to enable the milter on a pagure instance is thus to install the
``.service`` file for systemd and place the corresponding script that, by
default, should go to ``/usr/share/pagure/comment_email_milter.py``.

If you are using the RPM, install ``pagure-milters`` should provide and install
all the files correctly.

