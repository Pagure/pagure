
.. _forks:

Forks
=====
A fork in Pagure is a copy of a repository. When contributing to a project on
Pagure, the first step is to fork it. This gives you a place to make changes
to the project and, if you so wish, contribute back to the original upstream
project. If you're not already familiar with Git's distributed workflow,
`the Pro Git book has an excellent introduction
<https://git-scm.com/book/en/v2/Distributed-Git-Distributed-Workflows>`_.

You can see a list of projects you've forked on your home page.


.. _create-fork:

Create a Fork on Pagure
-----------------------
To fork a project, simply navigate to the project on Pagure and click
the fork button. You will then be redirected to your new fork.


.. _configure-local-git:

Configure your Local Git Repository
-----------------------------------
Now that you have forked the project on Pagure, you're ready to configure a
local copy of the repository so you can get to work. First, clone the
repository. The URL for the repository is on the right-hand side of the
project overview page. For example::

    $ git clone ssh://git@pagure.io/forks/jcline/pagure.git
    $ cd pagure

After cloning your fork locally, it's a good idea to add the upstream
repository as a `git remote <https://git-scm.com/docs/git-remote>`_. For
example::

    $ git remote add -f upstream ssh://git@pagure.io/pagure.git

This lets you pull in changes that the upstream repository makes after you
forked. Consult Git's documentation for more details.


Pushing Changes
---------------
After you :ref:`configure-local-git` you're ready to make your changes and
contribute them upstream. First, start a new branch::

    $ git checkout -b my-feature-or-bugfix

It's a good idea to give the branch a descriptive name so you can find it later.
Next, make your changes. Once you're satisfied, add the changes to Git's staging
area and commit the changes::

    $ git add -A  # Adds everything
    $ git commit -s

Your text editor of choice will open and you can write your commit message.
Afterwords, you are ready to push your changes to your remote fork::

    $ git push -u origin my-feature-or-bugfix

You are now ready to :ref:`open-pull-request`
