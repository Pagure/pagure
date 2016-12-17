Pagure LogCom
=============

This is the service logging in the user's commits to be displayed in the
database.
This service is triggered by a git hook, sending a notification that a push
happened. This service receive the notification and goes over all the commit
that got pushed and logs the activity corresponding to that user.

 * Run::

    PAGURE_CONFIG=/path/to/config PYTHONPATH=. python pagure-logcom/pagure_logcom_server.py
