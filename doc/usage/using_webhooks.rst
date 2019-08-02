Using web-hooks
===============

Web-hooks are a notification system that could be compared to a callback.
Basically, pagure will make a HTTP POST request to one or more third party
server/application with information about what is or just happened.

Activating web-hooks notifications
--------------------------------

To set-up a web-hook, simply go to the settings page of your project and
enter the URL to the server/endpoint that will receive the notifications.
If you wish to enter multiple URLs, enter one per line.
To stop all notifications, clear out that field.

Pagure will send a notification to this/these URL(s) for every action made
on this project: new issue, new pull-request, new comments, new commits...

.. note:: The notifications sent via web-hooks have the same payload as the
    notifications sent via `fedmsg <http://www.fedmsg.com/en/latest/>`_.
    Therefore, the list of pagure topics as well as example messages can be
    found in the `fedmsg documentation about pagure
    <https://fedora-fedmsg.readthedocs.io/en/latest/topics.html#id550>`_

Authenticating the notifications
--------------------------------

There is, in the settings page, a web-hook key which is used by the
server (here pagure) to sign the message sent and which you can use to
ensure the notifications received are coming from the right source.

Each POST request made contains some specific headers:

::

    X-Pagure
    X-Pagure-Project
    X-Pagure-Signature
    X-Pagure-Signature-256
    X-Pagure-Topic

``X-Pagure`` contains URL of the pagure instance sending this notification.

``X-Pagure-Project`` contains the name of the project on that pagure instance.

``X-Pagure-Signature`` contains the signature of the message allowing to
check that the message comes from pagure.

``X-Pagure-Signature-256`` contains the SHA-256 signature of the message
allowing to check that the message comes from pagure.

.. note:: These headers are present to allow you to verify that the webhook
        was actually sent by the correct Pagure instance. These are not
        included in the signed data.

``X-Pagure-Topic`` is a global header giving a clue about the type of action
that just occurred. For example ``issue.edit``.

.. warning:: The headers ``X-Pagure``, ``X-Pagure-Project`` and ``X-Pagure-Topic``
        are present for convenience only, they are not signed and therefore
        should not be trusted. Rely on the payload after checking the
        signature to make any decision.

Pagure relies on ``hmac`` to sign the content of its messages. If you want
to validate the message, in python, you can do something like the following:

::

    import hmac
    import hashlib

    payload =  # content you received in the POST request
    headers =  # headers of the POST request
    project_web_hook_key =  # private web-hook key of the project

    hashhex = hmac.new(
        str(project_web_hook_key), payload, hashlib.sha1).hexdigest()

    if hashhex != headers.get('X-Pagure-Signature'):
        raise Exception('Message received with an invalid signature')
