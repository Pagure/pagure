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
