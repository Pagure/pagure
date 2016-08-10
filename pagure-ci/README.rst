Pagure CI
=========

This is to setup Pagure CI for development. It is assumed that all the
dependencies are resolved.

 * Run::

    PAGURE_CONFIG=/path/to/config PYTHONPATH=. python pagure-ci/pagure_ci_server.py



Configure Jenkins
=================

Jenkins configuration is the most important part of how the Pagure CI works,
after you login to your Jenkins Instance.


* Go to Manage Jenkins -> Configuire Global Security and under that select
  'Project-based Matrix Authorization Strategy'

* Add a user and give all the permission to that user.

* Download the following plugins:

  * Build Authorization Root Plugin
  * `Git Plugin <https://wiki.jenkins-ci.org/display/JENKINS/Git+Plugin>`_
  * `Notification Plugin <https://wiki.jenkins-ci.org/display/JENKINS/Notification+Plugin>`_


Configure your project on Jenkins
=================================

* Start by enabling the `Pagure CI` hook in the settings of your project on
  pagure. This will provide you two values needed to configure your project
  on jenkins: a token and an URL that jenkins calls to return the results
  of a build.

* Go to the `Configure` page of your project

* Under `Job Notification`  click `Add Endpoint`

* Fields in Endpoint will be :

::

    FORMAT: JSON
    PROTOCOL: HTTP
    EVENT: Job Finalized
    URL: <The URL provided in the Pagure CI hook on pagure>
    TIMEOUT: 3000
    LOG: 1

* Tick the checkbox `This build is parameterized`

* Add two `String Parameters` named REPO and BRANCH

* Source Code Management select Git  and give the URL of the pagure project

* Under Build Trigger click on Trigger build remotely and specify the token
  given by pagure.

* Under Build -> Add build step -> Execute Shell

* In the box given  enter the shell steps you want for testing your project.


Example Script

::

    # Script specific for Pull-Request build
    if [ -n "$REPO" -a -n "$BRANCH" ]; then
    git remote rm proposed || true
    git remote add proposed "$REPO"
    git fetch proposed
    git checkout origin/master
    git config --global user.email "you@example.com"
    git config --global user.name "Your Name"
    git merge --no-ff "proposed/$BRANCH" -m "Merge PR"
    fi
    
    # Part of the script specific to how you run the tests on your project
