Pagure CI
=========

This is to setup Pagure CI for development. It is assumed that all the
dependencies are resolved.

 * Run::

        PAGURE_CONFIG=/path/to/config python pagure-ci/pagure_ci_server.py



Configuring Jenkins
===================

Jenkins configuration is the most important part of how the Pagure CI works,
after you login to your Jenkins Instance.


* Go to Manage Jenkins -> Configuire Global Security and under that select
  'Project-based Matrix Authorization Strategy'

* Add a user and give all the permission to that user.

* Download the following plugins:

::

      Build Authorization Root Plugin
      Git Plugins
      Notification Plugin


* Click on the New Item

* Select Freestyle Project

* Click OK and enter the name of the project, make sure the project name you
  filled in the Pagure CI form should match the name you entered here.

* Under 'Job Notification'  click 'Add Endpoint'

* Fields in Endpoint will be :

::

        FORMAT: JSON
        PROTOCOL: HTTP
        EVENT: Job Finalized
        URL: <The POST URL that Jenkins form returned>
        TIMEOUT: 3000
        LOG: 1

* Tick the build is parameterized

* From the Add Parameter drop down select String Parameter

* Two string parameters need to be created REPO and BRANCH

* Source Code Management select Git  and give the URL of the pagure project

* Under Build Trigger click on Trigger build remotely and give the same token
  that you gave in the Pagure CI form.

* Under Build -> Add build step -> Execute Shell

* In the box given  enter the shell steps you want for testing your project.


Example Script

::

        if [ -n "$REPO" -a -n "$BRANCH" ]; then
        git remote rm proposed || true
        git remote add proposed "$REPO"
        git fetch proposed
        git checkout origin/master
        git config --global user.email "you@example.com"
        git config --global user.name "Your Name"
        git merge --no-ff "proposed/$BRANCH" -m "Merge PR"
        fi

* After all the configuration done, go to the dev instance of pagure running
  and under project settings in `Plugin` select Pagure CI and fill the appropriate
  information. Which on submiting should give you a POST url.

* Copy and paste the URL in the Notification section under the Jenkins project
  you want the CI to work.
