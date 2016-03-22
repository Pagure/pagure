Using the doc repository of your project
========================================

On the overview page of your project, on the menu on the right side, are
presented the `Source GIT URLs`. Next to this title is a little `more` button.
If you click on this, you can see three more sections appearing: `Docs
GIT URLs`, `Issues GIT URLs` and `Pull Requests GIT URLs`.

Each section correspond to one of the four git repositories created for each
project:

* 1 git repository containing the source code, displayed in the main section
  of the pagure project.
* 1 git repository for the documentation
* 1 git repository for the issues and their metadata
* 1 git repository for the metadata for pull-requests

In this section of the documentation, we are intersting in the doc repository.

The doc repository is a simple git repo, whose content will appear under the
`Docs` tab in pagure and in https://docs.pagure.org/<project>/.

There are few ways you can put your documentation in this repo:

* Simple text files

Pagure will display them as plain text. If one of these is named ``index``
it will be presented as the front page.

* rst or markdown files

Pagure will convert them to html on the fly and display them as such.

* html files

Pagure will simply show them as such.


Example
-------

Pagure's documentation is kept in pagure's sources, in the `doc` folder there.
You can see it at: `https://pagure.io/pagure/blob/master/f/doc
<https://pagure.io/pagure/blob/master/f/doc>`_. This doc can be built with
`sphinx <http://sphinx-doc.org/>`_ to make it html and prettier.

The output of this building is at: `https://docs.pagure.org/pagure/
<https://docs.pagure.org/pagure/>`_.

This is how it is built/updated.

* Clone pagure's sources::

    git clone https://pagure.io/docs/pagure.git

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
    pushd $1
    git commit -av
    git push
    popd

    rm -rfI _build
    rm -rfI $1

It can be used by running `update_doc.sh <project>` from within the folder
containing the doc.

So for pagure it would be something like:

::

    cd pagure/doc
    update_doc.sh pagure
