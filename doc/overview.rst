Overview
========

Pagure is split over multiple components, each having their purpose and all
but one (the core application) being optional.

These components are:

.. contents::


Pagure core application
-----------------------

The core application is the flask application interacting with gitolite to
provide a web UI to the git repositories as well as tickets and pull-requests.
This is the main application for the forge.


Pagure doc server
-----------------

While integrated into the main application at first, it has been split out
for security concern, displaying information directly provided by the user
without a clear/safe way of filtering for un-safe script or hacks is a
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
