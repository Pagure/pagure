Using web-hooks
===============

Web-hooks are a notification system that could be compared to a callback.
Basically, pagure will make a HTTP POST request to one or more third party
server/application with information about what is or just happened.

To set-up a web-hook, simply go to the settings page of your project and
enter the URL to the server that will receive the notifications.

In the settings page is also present a web-hook key which is used by the
server to sign the message sent and which you can use to ensure the
notifications received are coming from the right source.

Each POST request made contains two specific headers:

::

    X-Pagure-Topic
    X-Pagure-Signature


``X-Pagure-Topic`` is a global header giving a clue about the type of action
that just occured. For example ``issue.edit``.


``X-Pagure-Signature`` contains the signature of the message allowing to
check that the message comes from pagure.


Pagure relies on ``hmac`` to sign the content of its messages. If you want
to validate the message, in python you can simply do something like this:

::

    import hmac

    payload =  # content you received in the POST request
    headers =  # headers of the POST request
    project_web_hook_key =  # private web-hook key of the project

    hashhex = hmac.new(
        str(project_web_hook_key), payload, hashlib.sha1).hexdigest()

    if hashhex != headers.get('X-Pagure-Signature'):
        raise Exception('Message received with an invalid signature')
