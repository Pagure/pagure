Using the doc repository of your project
========================================

In this section of the documentation, we are interested in the doc repository.

The doc repository is a simple Git repo, whose content will appear in 2 ways:

* inline under the `Docs` tab in Pagure:

  * either https://pagure.io/docs/<project>/

  * or https://pagure.io/docs/<namespace>/<project>/

* standalone:

  * either https://docs.pagure.org/<project>/

  * or https://docs.pagure.org/<namespace>.<project>/


By default the `Docs` tab in the project's menu is disabled, you
will have to visit the project's settings page and turn it on
in the ``Project options`` section.


The URL to the doc repository is:

* either https://pagure.io/<project>/docs/

* or https://pagure.io/<namespace>/docs/

Different file types can be used for your documentation in this repo:

* simple text files

  Pagure will display them as plain text. If one of these is named ``index``
  it will be presented as the front page.

* RST or markdown files

  Pagure will convert them to HTML on the fly and display them as such.
  The RST files must end with ``.rst`` and the markdown ones must end with
  ``.mk``, ``.md`` or simply ``.markdown``.

* HTML files

  Pagure will simply show them as such.

Updating documentation hosted in a dedicated repo is like
`using other repos <https://docs.pagure.org/pagure/usage/forks.html>`_.


Example
-------

Pagure's documentation is kept in pagure's sources, in the `doc` folder there.
You can see it at: `https://pagure.io/pagure/blob/master/f/doc
<https://pagure.io/pagure/blob/master/f/doc>`_. This doc can be built with
`Sphinx <http://sphinx-doc.org/>`_ to make it HTML and prettier.

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
