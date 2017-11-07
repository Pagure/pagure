Tips and tricks
===============

This page contains some tips and tricks on how to use pagure. These do not
fit in their own page but are worth mentioning.


Pre-fill issue template using the URL
-------------------------------------

When Creating Issues for a project , Pagure supports pre-filling the title
and description input text using url parameters

Example:
~~~~~~~~
https://pagure.io/pagure/new_issue/?title=<Issue>&content=<Issue Content>

The above URL will autofill the text boxes for Title and Description field
with Title set to <Issue> and Description set to <Issue Content>.


Filter for issues *not* having a certain tag
--------------------------------------------

Very much in the same way pagure allows you to filter for issues having a
certain tag, pagure allows to filter for issues *not* having a certain tag.
To do this, simply prepend a ``!`` in front of the tag.

Example:
~~~~~~~~
https://pagure.io/pagure/issues?tags=!easyfix


Local user creation without email verification
----------------------------------------------

If you set ``EMAIL_SEND`` to ```False``` from the configuration file, you
will get the emails printed to the console instead of being sent. The admin
of the instance can then access the URL to manually validate the account from
there. This is generally used for development where we don't need to send
any emails.


Filter an user's projects by their access
-----------------------------------------

When watching an user's page, the list of all the project that user is
involved in is presented regardless of whether the user has ticket, commit,
admin access or is the main admin of the project.

You can specify an ``acl=`` argument to the url to filter the list of
project by access.


.. note:: This also works for your home page when you are logged in


Examples:
~~~~~~~~~
https://pagure.io/user/pingou?acl=main admin
https://pagure.io/user/pingou?acl=admin
https://pagure.io/user/pingou?acl=commit
