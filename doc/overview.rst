Overview
========

Pagure is split over multiple components, each having their purpose and all
but one (the core application) being optional.

These components are:

.. contents::


Before going into the overall picture, one should realize that most of the
components listed above are optional.

Here is a diagram representing pagure without all the optional components:

.. image:: _static/overview_simple.png
        :target: _static/overview_simple.png


And here is a diagram of all the components together:

.. image:: _static/overview.png
        :target: _static/overview.png

Pagure core application
-----------------------

The core application is the flask application interacting with gitolite to
provide a web UI to the git repositories as well as tickets and pull-requests.
This is the main application for the forge.


Gitolite
--------

Currently pagure uses `gitolite <http://gitolite.com/gitolite/index.html>`_
to grant or deny `ssh <https://en.wikipedia.org/wiki/Secure_Shell>`_ access
to the git repositories, in other words to grant or deny read and/or write
access to the git repositories.

Pagure supports cloning over both ssh and http, but writing can only be done
via ssh, through gitolite.


Pagure doc server
-----------------

While integrated into the main application at first, it has been split out
for security concern, displaying information directly provided by the user
without a clear/safe way of filtering for unsafe script or hacks is a
security hole.
For this reason we also strongly encourage anyone wanting to deploy their
own instance of pagure with the doc server, to run this application on a
completely different domain name (not just a sub-domain) in order to reduce
the cross-site forgery risks.

Pagure can be run just fine without the doc server, all you need to do is to
**not** define the variable ``DOC_APP_URL`` in the configuration file.


Pagure milter
-------------

The milter is a script, receiving an email as input and performing an action
with it.

In the case of pagure, the milter is used to allow replying on a comment
of a ticket or a pull-request by directly replying to the notification sent.
No need to go to the page anymore to reply to a comment someone made.

The milter integrates with a MTA such as postfix or sendmail that you will
have running and have access to in order to change its configuration.


Pagure EventSource Server
-------------------------

Eventsource or Server Sent Events are messages sent from a server to a browser.

For pagure this technology is used to allow live-refreshing of a page when
someone is viewing it. For example, while you are reading a ticket if someone
comments on it, the comment will automatically show up on the page without
the need for you to reload the entire page.

The flow is: the main pagure server does an action, sends a message over
redis, the eventsource server picks it up and send it to the browsers waiting
for it, then javascript code is executed to refresh the page based on the
information received.


Pagure web-hook Server
-------------------------

Sends notifications to third party services using POST http requests.

This is the second notifications system in pagure with `fedmsg <http://fedmsg.com/>`_.
These notifications are running on their own service to prevent blocking the
main web application in case the third part service is timing-out or just
being slow.

The flow is: the main pagure server does an action, sends a message over
redis, the web-hook server picks it up, build the query and performs the
POST request to the specified URLs.
