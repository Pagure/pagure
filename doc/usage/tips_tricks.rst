Tips and tricks
===============

This page contains some tips and tricks on how to use Pagure. These do not
fit in their own page but are worth mentioning.

Place image onto your overview page
-----------------------------------

You can only use images that come from the Pagure host itself.

Example
~~~~~~~

::

    ![See Copr workflow](/copr/copr/raw/master/f/doc/img/copr-workflow.png)

Text in the square brackets will be used as an alt description.

Pre-fill issue using the URL
----------------------------

When creating issues for a project Pagure supports pre-filling the title
and description input text using URL parameters.

Example:
~~~~~~~~
https://pagure.io/pagure/new_issue/?title=<Issue>&content=<Issue Content>

The above URL will autofill the text boxes for Title and Description field
with Title set to <Issue> and Description set to <Issue Content>.


Pre-fill issue template using the URL
-------------------------------------

When creating issues for a project Pagure supports pre-filling the title
and description input text using URL parameters.

Example:
~~~~~~~~
https://pagure.io/pagure/new_issue/?template=<TemplateName>

The above URL will autofill the ticket with the specified template. The
TemplateName should be the name of the template file on disk (in the
``templates`` directory of the ticket git repository).


Filter for issues *not* having a certain tag
--------------------------------------------

Very much in the same way Pagure allows you to filter for issues having a
certain tag, Pagure allows one to filter for issues *not* having a certain tag.
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

When watching a user's page, the list of all the project that user is
involved in is presented regardless of whether the user has ticket, commit,
admin access or is the main admin of the project.

You can specify an ``acl=`` argument to the URL to filter the list of
projects by access.


.. note:: This also works for your home page when you are logged in.


Examples:
~~~~~~~~~
https://pagure.io/user/pingou?acl=main admin
https://pagure.io/user/pingou?acl=admin
https://pagure.io/user/pingou?acl=commit


Filter issues by (custom) fields
--------------------------------

Via the project's settings page, admins can set custom keys to be used in
issues. You can search them using the URL via the arguments ``ckeys`` and
``cvalue`` or simpler, using the search field at the top of the issue page.

This also works for the following regular fields: ``tags``, ``milestones``,
``author``, ``assignee``, ``status``, ``priority`` (but tags and milestones
despite their name only support a single value).

Examples:
~~~~~~~~~
https://pagure.io/SSSD/sssd/issues?status=Open&search_pattern=review%3ATrue
https://pagure.io/pagure/issues?status=Open&search_pattern=tags%3Aeasyfix


Search the comments of issues
-----------------------------

One can search all the comments made on an issue tracker using
``content:<keyword>`` in the search field. This is going to search all the
comments (including the descriptions) of all the tickets and thus can be quite
slow on large project. This is why this feature isn't being pushed much forward.

Examples:
~~~~~~~~~
https://pagure.io/pagure/issues?status=Open&search_pattern=content%3Aeasyfix
