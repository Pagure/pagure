Pagure loadjson
===============

This is the service loads into the database the JSON files representing
issues or pull-requests.

This service is triggered by a git hook, sending a notification that a push
happened. This service receive the notification and find the list of file
that changed and load them into the database.

 * Run::

    PAGURE_CONFIG=/path/to/config PYTHONPATH=. python pagure-loadjson/pagure_loadjson_server.py
