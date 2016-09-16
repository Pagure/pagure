Using the doc repository of your project
========================================

In this section of the documentation, we are interested in the doc repository.

The doc repository is a simple git repo, whose content will appear under the
`Docs` tab in pagure and on https://docs.pagure.org/<project>/.

There are a few ways you can put your documentation in this repo:

* Simple text files

Pagure will display them as plain text. If one of these is named ``index``
it will be presented as the front page.

* rst or markdown files

Pagure will convert them to html on the fly and display them as such.
The rst files must end with `.rst` and the markdown ones must end with
``.mk``, ``.md`` or simply ``.markdown``.

* html files

Pagure will simply show them as such.


.. note: By default the `Docs` tab in the project's menu is disabled, you
         will have to visit the project's settings page and turn it on
         in the ``Project options`` section.


Example
-------

Pagure's documentation is kept in pagure's sources, in the `doc` folder there.
You can see it at: `https://pagure.io/pagure/blob/master/f/doc
<https://pagure.io/pagure/blob/master/f/doc>`_. This doc can be built with
`sphinx <http://sphinx-doc.org/>`_ to make it html and prettier.

The built documentation is available at: `https://docs.pagure.org/pagure/
<https://docs.pagure.org/pagure/>`_.

This is how it is built/updated:

* Clone pagure's sources::

    git clone https://pagure.io/pagure.git

* Move into its doc folder::

    cd pagure/doc

* Build the doc::

    make html

* Clone pagure's doc repository::

    git clone ssh://git@pagure.io/docs/pagure.git

* Copy the result of sphinx's build to the doc repo::

    cp -r _build/html/* pagure/

* Go into the doc repo and update it::

    cd pagure
    git add .
    git commit -am "Update documentation"
    git push

* Clean the sources::

    cd ..
    rm -rf pagure  # remove the doc repo
    rm -rf _build  # remove the output from the sphinx's build


To make things simpler, the following script (name `update_doc.sh`) can be
used:

::

    #!/bin/bash

    make html

    git clone "ssh://git@pagure.io/docs/$1.git"
    cp -r _build/html/* $1/
    (
        cd $1
        git add .
        git commit -av
        git push
    )

    rm -rfI _build
    rm -rfI $1

It can be used by running `update_doc.sh <project>` from within the folder
containing the doc.

So for pagure it would be something like:

::

    cd pagure/doc
    update_doc.sh pagure
