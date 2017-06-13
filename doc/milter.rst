Pagure's Milter
===============

`Milter <http://www.postfix.org/MILTER_README.html>`_ are script executed by
postfix upon sending or receiving an email.

We use this system to allow pagure's users to comment on a ticket (or a
pull-request) by directly replying to the email sent as a notification.

Pagure's milter is designed to be run on the same machine as the mail server
(postfix by default). Postfix connecting to the milter via a unix socket.

The milter itself is a service managed by systemd.
You can find all the relevant files for the milter under the
``pagure-milters`` folder in the sources.


Install the milter
------------------

The first step to enable the milter on a pagure instance is thus to install the
``.service`` file for systemd and place the corresponding script that, by
default, should go to ``/usr/share/pagure/comment_email_milter.py``.

If you are using the RPM, install ``pagure-milters`` should provide and install
all the files correctly.


Activate the milter
-------------------

Make sure the milter is running and will be automaticall started at boot by
running the commands:

To start the milter:

::

    systemctl start pagure_milter

To ensure the milter is always started at boot time:

::

    systemctl enable pagure_milter


Activate the milter in postfix
------------------------------

To actually activate the milter in postfix is in fact really easy, all it takes
is two lines in the ``main.cf`` file of postfix:

::

    non_smtpd_milters = unix:/var/run/pagure/paguresock
    smtpd_milters = unix:/var/run/pagure/paguresock

These two lines are pointing to the unix socket used by postfix to communicate
with the milter. This socket is defined in the milter file itself, in the
sources: ``pagure-milters/comment_email_milter.py``.

