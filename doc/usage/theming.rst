Theming Guide
=============

Pagure is built on Flask, and uses Jinja2 for templates. Pagure also
includes the ability to apply different themes that control the look
and feel of your Pagure instance, or add or remove elements from the
interface.

Setting a theme
---------------
The theme is set in the Pagure configuration file. The theme name is defined by
the name of the directory in the /themes/ folder that contains the theme. For
example to enable the theme that is used on Pagure.io, add the following line
to your Pagure configuration:

::

    THEME = "pagureio"


Theme contents
--------------
A theme requires two directories (`templates` and `static`) in the directory
that contains the theme. The only other required file is theme.html which
is placed in the templates directory

templates/
~~~~~~~~~~
The `templates` directory is where Pagure will look for the `theme.html`
template. Additionally, if you wish to override any template in Pagure,
place it in the theme templates/ directory, and Pagure will use that
template rather than the standard one.

.. warning:: Take care when overriding templates, as any changes to Pagure
            upstream will need to be backported to your theme template override.

static/
~~~~~~~
The `static` directory contains all the static elements for the theme,
including additional a favicon, images, Javascript, and CSS files. To
reference a file in the theme static directory use the jinja2 tag
`{{ url_for('theme.static', filename='filename')}}`. For example:

::

    <link href="{{ url_for('theme.static', filename='theme.css') }}"
          rel="stylesheet" type="text/css" />


templates/theme.html
~~~~~~~~~~~~~~~~~~~~
The theme.html file defines a subset of items in the Pagure interface that
are commonly changed when creating a new theme. Theming is a new feature in
Pagure, so this set is currently small, but please file issues or PRs against
Pagure with ideas of new items to include.

The current items configurable in theme.html are:


`masthead_class` variable
#########################

A string of additional CSS class(es) to be added to the navbar element.
This navbar element is the topbar in Pagure. For example:

::

    {% set masthead_class = "navbar-dark bg-dark" %}


`masthead_navbar_items()` macro
###############################

A Jinja macro that allows themes to inject custom items in the Pagure navigation
bar. Example:

::

    {% macro masthead_navbar_items() %}
        <li class="nav-item ml-3">
            <a class="nav-link font-weight-bold" href="...">
                Foobar
            </a>
        </li>
    {% endmacro %}


`site_title` variable
#####################

A string containing the text to append at the end of the html title
on every page on the site. Usage:

::

    {% set site_title = "Pagure" %}


`projectstring(Bool:plural)` macro
##################################

A macro that returns a string used to refer to Projects in Pagure
The plural parameter informs if the string to be returned is the
plural form.
This macro is optional.
Usage:

::

    {% macro projectstring(plural=False) -%}
        {% if plural %}
            Repositories
        {% else %}
            Repository
        {% endif %}
    {% endmacro -%}


`projecticon` variable
######################

A string containing the name of the fontawesome icon to use for
Projects. This variable is optional. Usage:

::

    {% set projecticon = "Package" %}


`head_imports()` macro
######################

A Jinja macro that defines the additional items in the html head to
be imported. The base templates do not include the bootstrap CSS, so
this needs to be included in this macro in your theme. Additionally,
include your favicon here, and a link to any additional CSS files your
theme uses. Example:

::

    {% macro head_imports() %}
        <link rel="shortcut icon" type="image/vnd.microsoft.icon"
              href="{{ url_for('theme.static', filename='favicon.ico')}}"/>
        <link rel="stylesheet" href="{{ url_for('theme.static', filename='bootstrap/bootstrap.min.css')}}" />
        <link href="{{ url_for('theme.static', filename='theme.css') }}" rel="stylesheet" type="text/css" />
    {% endmacro %}


`js_imports()` macro
####################

A Jinja macro that defines the additional javascript files to
be imported. The base templates do not include the bootstrap JS, so
this needs to be included in this macro in your theme. Example:

::

    {% macro js_imports() %}
        <script src="{{ url_for('theme.static', filename='bootstrap/bootstrap.bundle.min.js')}}"></script>
    {% endmacro %}


`browseheader_message(select)` macro
####################################

An optional Jinja macro that defines the welcome message that is shown
above the tabs on the Browse Pages (Projects, Users, and Groups). The
select parameter is a string with the name of the page being shown
Example:

::

    {% macro browseheader_message(select) %}
        {% if select == 'projects' %}
        <div class="row justify-content-around">
        <div class="col-md-8">
            <div class="jumbotron bg-transparent m-0 py-4 text-center">
                <h1 class="display-5">Welcome to my Pagure</h1>
                <p class="lead">Pagure is an Open Source software code hosting system.</p>
            </div>
        </div>
        </div>
        {% endif %}
    {% endmacro %}


`footer()` macro
################

A Jinja macro that defines the footer of the Pagure site. Example:

::

    {% macro footer() %}
        <div class="footer py-3 bg-light border-top text-center">
            <div class="container">
                <p class="text-muted credit">
            Powered by
            <a href="https://pagure.io/pagure">Pagure</a>
            {{ g.version }}
                </p>
                <p><a href="{{ url_for('ui_ns.ssh_hostkey') }}">SSH Hostkey/Fingerprint</a> | <a href="https://docs.pagure.org/pagure/usage/index.html">Documentation</a></p>
            </div>
        </div>
    {% endmacro %}


`about_page()` macro
######################

A Jinja macro that defines the content of the About page (available at /about). You may want to replace the links to contact links for your own instance. Example:

::

    {% macro about_page() %}
        <div class="container mt-5">
            <h1>About</h1>
            <p>This is an instance of Pagure, a git forge.</p>
            <p>If you experience a bug or security concern, please <a href="https://pagure.io/pagure/issues">submit an issue</a>.</p>
            <p>You may also post questions to the Pagure Development list by emailing: <a href="mailto:pagure-devel@lists.pagure.io">pagure-devel@lists.pagure.io</a> or <a href="https://lists.pagure.io/admin/lists/pagure-devel.lists.pagure.io/">subscribe to the list</a>.</p>
            <p><a href="https://lists.pagure.io/admin/lists/pagure-announce.lists.pagure.io/">Subscribe to announcements</a> about Pagure.</p>
        </div>
    {% endmacro %}
