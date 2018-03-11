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


.. note: The principal is that pagure will look in the folder specified in
         the configuration file first and then in its usual folder, so the
         **file names must be identical**.

Example
-------

Let's take an example, you wish to replace the pagure logo at the top right
of all the pages.

This logo is part of the ``master.html`` template which all pages inherit
from. So what you want to do is replace this ``master.html`` by your own.

* First, create the folder where your templates and static files will be stored:

::

    mkdir /var/www/mypaguretheme/templates
    mkdir /var/www/mypaguretheme/static

* Place your own logo in the static folder

::

    cp /path/to/your/my-logo.png /var/www/mypaguretheme/static

* Place in there the original ``master.html``

::

    cp /path/to/original/pagure/templates/master.html /var/www/mypaguretheme/templates

* Edit it and replace the URL pointing to the pagure logo (around line 27)

::

    - <img height=40px src="{{ url_for('static', filename='pagure-logo.png') }}"
    + <img height=40px src="{{ url_for('static', filename='my-logo.png') }}"

* Adjust pagure's configuration file:

::

    + THEME_TEMPLATE_FOLDER='/var/www/mypaguretheme/templates'
    + THEME_STATIC_FOLDER='/var/www/mypaguretheme/static'

* Restart pagure


.. note: you could just have replaced the `pagure-logo.png` file with your
         own logo which would have avoided overriding the template.


In production
-------------

Serving static files via flask is fine for development but in production
you will probably want to have Apache serve them. This will allow caching
either on the server side or on the client side.

You can ask Apache to behave in a similar way as does flask-multistatic with
flask here, i.e.: search in one folder and if you don't find the file look
in another one.

`An example Apache configuration <https://pagure.io/flask-multistatic/blob/master/f/example.conf>`_
is provided as part of the sources of `flask-multistatic`_.
