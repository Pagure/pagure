.. _pull-requests:

Pull Requests
=============
Pagure uses the concept of pull requests to contribute changes from your fork
of a project back to the upstream project. To contribute a change to a project
you first open a pull request with original project. The project maintainer
then merges the pull request if they are satisfied with the changes you have
proposed.


.. _open-pull-request:

Open a Pull Request
-------------------
Before you can open a pull request, you need to complete the :ref:`first-steps`
and :ref:`create-fork` of the project you would like to contribute to. Once
you have a fork and you have pushed a `git branch <https://git-scm.com/docs/git-branch>`_
containing one or more `commits <https://git-scm.com/docs/git-commit>`_, you are
ready to contribute to the project. Navigate to the project's Pull Request page
and click on the ``File Pull Request`` button.

A dropdown menu should appear containing the git branches in your fork. Select the
branch containing your changes. You will be taken to a page where you can customize
the title of your Pull Request and its description. By default, this is populated
using your commit message.

Once you are satisfied with your title and description, click ``Create``.

Congratulations! It is now up to the project maintainer to accept your changes by
merging them.


.. _update-pull-request:

Updating Your Pull Request
--------------------------
It is likely that project maintainers will request changes to your proposed code
by commenting on your pull request. Don't be discouraged! This is an opportunity
to improve your contribution and for both reviewer and reviewee to become better
programmers.

Adding to your pull request is as simple as pushing new commits to the branch you
used to create the pull request. These will automatically be displayed in the
commit list for the pull request.


Rebasing
^^^^^^^^
You may encounter a situation where you want to include changes from the master
branch that were made after you created your pull request. You can do this by
`rebasing <https://git-scm.com/docs/git-rebase>`_ your pull request branch and
pushing it to your remote fork.
