Theme your pagure
=================

Pagure via `flask-multistatic <https://pagure.io/flask-multistatic>`_
offers the possibility to override the default theme allowing to customize
the style of your instance.

By default pagure looks for its templates and static files in the folders
``pagure/templates`` and ``pagure/static``, but you can ask pagure to look
for templates and static files in another folder.

By specifying the configuration keys ``THEME_TEMPLATE_FOLDER`` and
``THEME_STATIC_FOLDER`` in pagure's configuration file, you tell pagure to
look for templates and static files first in these folders, then in its
usual folders.
