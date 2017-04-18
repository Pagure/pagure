Project settings
================

Each project have a number of options that can be tweaked in the settings
page of the project which is accessible to the person having full commits
to the project.

This page presents the different settings and there effect.


`Activate always merge`
------------------------

This boolean enables or disables always making a merge commit when merging
a pull-request.

When merging a pull-request in pagure there are three states:

* fast-forward: when the commits in the pull-request can be fast-forwarded
  pagure signals it and just fast-forward the commit, keeping the history linear.

* merge: when the commits in the pull-request cannot be merged without a merge
  commit, pagure signals it and performs this merge commit.

* conflicts: when the commits in the pull-request cannot be merged at all
  automatically due to one or more conflicts. Then pagure signals it and prevent
  merging.

If the `Activate always merge` option is on, then the `fast-forward` option
above is disabled in favor of the `merge` option.


`Activate comment editing`
--------------------------

This boolean enables or disables editing comments.

After commenting on a ticket or a pull-request, the admins of the project
and the author of the comment may be allowed to edit the comment.
This allows them to adjust the wording or the style as they wish.

.. note:: notification about a comment is only sent once with the original
          text, changes performed later will not trigger a new notification.

Some project may not want to allow editing comments after they were posted
and this setting allows turning it on or off.


`Activate Enforce signed-off commits in pull-request`
-----------------------------------------------------

This boolean enables or disables checking for a 'Signed-off-by' line (case
insensitive) in the commit messages of the pull-requests.

If this line is missing, pagure will display a message near the `Merge`
button, allowing project admin to request the PR to be updated.

.. note:: This setting does not prevent commits without this 'signed-off-by'
          line to be pushed directly, it only work at the pull-request level.


`Activate issue tracker`
------------------------

This boolean simply enables or disables the issue tracker for the project.
So if you are tracking your ticket on a different system, you can simply
disable reporting issue on pagure by un-checking this option.


`Activate Minimum score to merge pull-request`
----------------------------------------------

This option can be used for project wishing to enforce having a minimum
number of people reviewing a pull-request before it can be merged.

If this option is enabled, anyone can vote in favor or against a pull-request
and the sum of the votes in favor minus the sum of the votes against give
the pull-request a score that should be equal or greater than the value
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


`Activate Only assignee can merge pull-request`
-----------------------------------------------

This option can be used for project wishing to institute a strong review
workflow where pull-request are first assigned then merged.

If this option is enabled, only the person assigned to the pull-request
can merge it.


`Activate project documentation`
--------------------------------

Pagure offers the option to have a git repository specific for the
documentation of the project.

This repository is then accessible under the ``Docs`` tab in the menu of the
project.

If you prefer to store your documentation elsewhere or maybe even within
the sources of the project, you can disable the ``Docs`` tab by un-checking
this option.


`Activate pull requests`
------------------------

Pagure offers the option to fork a project, make changes to it and then ask
the developer to merge these changes into the project. This is similar to
the pull-request mechanism on GitHub or GitLab.

However, some projects may prefer receiving patches by email on their list
or via another hosting plateform or simply do not wish to use the
pull-request mechanism at all. Un-checking this option will therefore
prevent anyone from opening a pull-request against this project.

.. note:: disabling pull-requests does *not* disable forking the projects.


`Activate Web-hooks`
--------------------

Pagure offers the option of sending notification about event happening on a
project via [web-hooks|https://en.wikipedia.org/wiki/Webhook]. This option
is off by default and can be turned on for a pagure instance in its
configuration file.

The URL of the web-hooks can be entered in this field.

.. note:: See the ``notifications`` documentation to learn more about
          web-hooks in pagure and how to use them.

`Tags`
------

Pagure allows you to define "tags" that can be added to Issues.  Tags are
unique to each project, and they can only be defined in the project
settings page.  The Tag color can also be customized for a more robust
visual representation of the tag.

`Deploy keys`
-------------

Deploy keys are SSH keys that have access to pull/push only to a single
project.
Upon creation, admins can determine whether this particular key has read/write
access or read-only.
