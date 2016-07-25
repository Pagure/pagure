=========
Pagure CI
=========

Pagure CI is a continuous integration tool using which the PR on the projects
can be tested and flaged with the status of the build.

How to enable Pagure CI
=======================

* Enable the Fedmsg plugin in pagure project setting . This will emit the message
  to for consumer to consume it.

* Fill in the Pagure CI form with the required details. 

::

		Pagure Project Name
		Jenkins Project Name
		Jenkins Token
		Jenkins Url
	
        All of which are required field.

* The jenkins token is any string that you give here. The only thing that should
  be kept in mind that this token should be same through out.
		
* This will give a POST URL which will be used for Job Notification in Jenkins

* The POST url will only appear only after you successfully submitted the form.


Configuring Jenkins
===================

Jenkins configuration is the most important part of how the Pagure CI works,
after you login to your Jenkins Instance.

* Go to Manage Jenkins -> Configuire Global Security and under that select
  `Project-based Matrix Authorization Strategy`

* Add your username here and make sure to give that username all the permissions.
  You should give all the permissions possible so that you save your self from
  getting locked in Jenkins.

* Download the following plugins:

::

      Build Authorization Root Plugin
      Git Plugins
      Notification Plugin


* Click on the New Item

* Select Freestyle Project

* Click OK and enter the name of the project, make sure the project name
  you filled in the Pagure CI form should match the name you entered here.

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

* Source Code Management select Git and give the URL of the pagure project

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

How to install Pagure CI
========================

Pagure CI requires `fedmsg` to run since it uses a consumer to get messages
and take appropriate actions. The dependency that is required is `fedmdg-hubs`.
For that the steps are given.

To install the dependencies required:

	 `dnf install fedmsg-hub`

`fedmsg` apart from the consumer require a file that tells to which cosumer
it should listen to. This file basically enable the consumer in PagureCI/.
For doing that, we need to place this file in appropriate directory.

	 `sudo cp pagure/fedmsg.d/pagure_ci.py /etc/fedmsg.d/`

Since the deployment is done using rpm, the next step is covered using  `setup.py`
which binds the consumer with the environment, this is done while building the rpm
so if rpm is already built this is not explicitly required.

	`python setup.py install`

Run the service:

    `sudo systemctl enable fedmsg-hub.service`

    `sudo systemctl start fedmsg-hub.service`



