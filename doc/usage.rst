Usage
=====

Using pagure should come fairly easily, especially to people already used
to forges such as GitHub or GitLab. There are however some tips and tricks
which can be useful to know and that this section of the doc covers.


One of the major difference with GitHub and GitLab is that for each project
on pagure, four git repositories are made available to the admins of the
project:

* A git repository containing the source code, displayed in the main section
  of the pagure project.
* A git repository for the documentation
* A git repository for the issues and their metadata
* A git repository for the metadata for pull-requests


You can find the URLs to access or clone these git repositories on the
overview page of the project. On the menu on the right side, there is a menu
`Source GIT URLs`, next to it is a little `more` button, by clicking on it
you will be given the URLs to the other three git repos.

Each section correspond to one of the four git repositories created for each
project.



Contents:

.. toctree::
   :maxdepth: 2

   usage/first_steps
   usage/markdown
   usage/project_settings
   usage/roadmap
   usage/using_doc
   usage/using_webhooks
   usage/ticket_templates
   usage/pr_custom_page
   usage/theming
   usage/upgrade_db
   usage/pagure_ci
