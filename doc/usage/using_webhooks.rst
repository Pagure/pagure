Using web-hooks
===============

Web-hooks are a notification system that could be compared to a callback.
Basically, pagure will make a HTTP POST request to one or more third party
server/application with information about what is or just happened.

To set-up a web-hook, simply go to the settings page of your project and
enter the URL to the server/endpoint that will receive the notifications.

There is, in the settings page, a web-hook key which is used by the
server (here pagure) to sign the message sent and which you can use to
ensure the notifications received are coming from the right source.

Each POST request made contains two specific headers:

::

    X-Pagure-Topic
    X-Pagure-Signature
    X-Pagure-Signature-256


``X-Pagure-Topic`` is a global header giving a clue about the type of action
that just occurred. For example ``issue.edit``.

.. warning:: This header is present for convenience only, it is not
        signed and therefore should not be trusted. Rely on the payload
        after checking the signature to make any decision.


``X-Pagure-Signature`` contains the signature of the message allowing to
check that the message comes from pagure.

``X-Pagure-Signature-256`` contains the SHA-256 signature of the message
allowing to check that the message comes from pagure.

.. note:: These headers are present to allow you to verify that the webhook
        was actually sent by the correct Pagure instance. These are not
        included in the signed data.

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


The notifications sent via web-hooks have the same payload as what is sent
via `fedmsg <http://www.fedmsg.com/en/latest/>`_. Therefore, the list of
pagure topics as well as example messages can be found in the
`fedmsg documentation about pagure
<https://fedora-fedmsg.readthedocs.org/en/latest/topics.html#id532>`_
