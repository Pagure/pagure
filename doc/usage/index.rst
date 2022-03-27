Usage
=====

Using Pagure should come fairly easily, especially to people already used
to forges such as GitHub or GitLab. There are however some tips and tricks
which can be useful to know and that this section of the doc covers.


One of the major difference with GitHub and GitLab is that for each project
on Pagure, four git repositories are made available:

* A git repository containing the source code, displayed in the main section
  of the Pagure project.
* A git repository for the documentation
* A git repository for the issues and their metadata
* A git repository for the metadata for pull-requests


Issues and pull-requests repositories contain the meta-data (comments,
notifications, assignee...) from the issues and pull-request. They are are
not public and only available to admins and committers of the project,
since they may contain private information.

You can use these repositories for offline access to your tickets or
pull-requests (the `pag-off <https://pagure.io/pag-off>`_ project for example
relies on a local copy of the issue git repository). They are designed to
allow you to have full access to all the data about your project.
One of the original idea was also to allow syncing a project between multiple
Pagure instances by syncing these git repositories between the instances.

You can find the URLs to access or clone these git repositories on the
overview page of the project. On the top right of the page, in the drop-down
menu entitled ``Clone``. Beware that if documentation, the issue tracker or
the pull-requests are disabled on the project, the corresponding URL will
not be shown.


Contents:

.. toctree::
   :maxdepth: 2

   first_steps
   forks
   read_only
   http_push
   pull_requests
   markdown
   project_settings
   project_acls
   roadmap
   flags
   magic_words
   using_doc
   using_webhooks
   ticket_templates
   pr_custom_page
   theming
   upgrade_db
   pagure_ci
   quick_replies
   board
   troubleshooting
   tips_tricks


Pagure API
----------

The API documentation can be found at `https://pagure.io/api/0/ <https://pagure.io/api/0/>`_
or in ``/api/0/`` of you local Pagure instance.
