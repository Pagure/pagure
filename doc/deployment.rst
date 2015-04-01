Deployment
==========

From sources
------------

Clone the source::

 git clone http://git.fedorahosted.org/git/pagure.git

Install the dependencies listed in the ``requirements.txt`` file.


Copy the configuration files::

  cp pagure.cfg.sample pagure.cfg

Adjust the configuration files (secret key, database URL, admin group...).
See :doc:`configuration` for detailed information about the configuration.


Create the database scheme::

   PAGURE_CONFIG=/path/to/pagure.cfg python createdb.py

Create the folder that will receive the different git repositories:

::

    mkdir {repos,docs,forks,tickets}


Set up the WSGI as described below.


From system-wide packages
-------------------------

Start by install pagure::

  yum install pagure

Adjust the configuration files: ``/etc/pagure/pagure.cfg``.
See :doc:`configuration` for detailed information about the configuration.

Find the file used to create the database::

  rpm -ql pagure |grep createdb.py

Create the database scheme::

   PAGURE_CONFIG=/etc/pagure/pagure.cfg python path/to/createdb.py

Set up the WSGI as described below.


Set-up WSGI
-----------

Start by installing ``mod_wsgi``::

  yum install mod_wsgi


Then configure apache::

 sudo vim /etc/httd/conf.d/pagure.conf

uncomment the content of the file and adjust as desired.


Then edit the file ``/usr/share/pagure/pagure.wsgi`` and
adjust as needed.


Then restart apache and you should be able to access the website on
http://localhost/pkgdb


.. note:: `Flask <http://flask.pocoo.org/>`_ provides also  some documentation
          on how to `deploy Flask application with WSGI and apache
          <http://flask.pocoo.org/docs/deploying/mod_wsgi/>`_.


For testing
-----------

See :doc:`development` if you want to run pagure just to test it.

