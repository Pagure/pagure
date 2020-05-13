.. _plugins:

Plugins
=======

Pagure provides a mechanism for loading 3rd party plugins in the form of Flask
Blueprints. The plugins are loaded from a separate configuration file that is
specified using the PAGURE_PLUGINS_CONFIG option. There are at least two
reasons for keeping plugins initialization outside the main pagure
configuration file:

#. avoid circular dependencies errors. For example if the pagure configuration
   imports a plugin, which in turn imports the pagure configuration, the plugin
   could try to read a configuration option that has not been imported yet and
   thus raise an error
#. the pagure configuration is also loaded by other processes such as Celery
   workers. The Celery tasks might only be interested in reading the
   configuration settings without having to load any external plugin


Loading the configuration
-------------------------

The configuration file can be loaded by setting the variable
``PAGURE_PLUGINS_CONFIG`` inside the pagure main configuration file, for
example inside ``/etc/pagure/pagure.cfg``. Alternatively, it is also possible
to set the environment variable ``PAGURE_PLUGINS_CONFIG`` before starting the
pagure server. If both variables are set, the environment variable takes
precedence over the configuration file.


The configuration file
----------------------

After Pagure has imported the configuration file defined in
PAGURE_PLUGINS_CONFIG it will look for Flask Blueprints in a variable called
``PLUGINS`` defined in the same file, for example
``PLUGINS = [ plugin1.blueprint, plugin2.blueprint, ... ]``. Pagure will then
proceed to register any Blueprint into the main Flask app, in the same order as
they are listed in ``PLUGINS``.

An example configuration can be seen in ``files/plugins.cfg.sample`` inside
the Pagure repository.
