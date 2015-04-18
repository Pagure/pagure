Project settings
================

Each project have a number of options that can be tweaked in the settings
page of the project which is accessible to the person having full commits
to the project.

This page presents the different settings and there effect.


Issue tracker
-------------

This boolean simply enables or disables the issue tracker for the project.
So if you are tracking your ticket on a different system, you can simply
disable reporting issue on pagure by un-checking this option.


Project documentation
---------------------

Pagure offers the option to have a git repository specific for the
documentation of the project.

This repository is then accessible under the ``Docs`` tab in the menu of the
project.

If you prefer to store your documentation elsewhere or maybe even within
the sources of the project, you can disable the ``Docs`` tab by un-checking
this option.


Pull-request
------------

Pagure offers the option to fork a project, make changes to it and then ask
the developer to merge these changes into the project. This is similar to
the pull-request mechanism on GitHub or GitLab.

However, some projects may prefer receiving patches by email on their list
or via another hosting plateform or simply do not wish to use the
pull-request mechanism at all. Un-checking this option will therefore
prevent anyone from opening a pull-request against this project.

.. note:: disabling pull-requests does *not* disable forking the projects.


Only assignee can merge pull-request
------------------------------------

This option can be used for project wishing to institute a strong review
workflow where pull-request are first assigned then merged.

If this option is enabled, only the person assigned to the pull-request
can merge it.


Minimum score to merge pull-request
-----------------------------------

This option can be used for project wishing to enforce having a minimum
number of people reviewing a pull-request before it can be merged.

If this option is enabled, anyone can vote in favor or against a pull-request
and the sum of the votes in favor minus the sum of the votes againsts give
the pull-request a score that should be equal or great to the value
entered in this option for the pull-request to be allowed to be merged.

.. note:: Only the main comments (ie: not in-line) are taken into account
          to calculate the score of the pull-request.

To vote in favor of a pull-request, use either:
* ``+1``
* ``:thumbsup:``

To vote against a pull-request, use either:
* ``-1``
* ``:thumbsdown:``

.. note:: Pull-Request reaching the minimum score are not automatically merged

.. note:: Anyone can vote on the pull-request, not only the contributors.


Web-hooks
---------

Pagure supports sending notification about event happening on a project
via [web-hooks|].

The URL of the web-hooks can be entered in this field.

.. note:: See the ``notifications`` documentation to learn more about
          web-hooks in pagure and how to use them.
