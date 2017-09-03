Understanding Read Only Mode of projects
=========================================

If a project is in Read Only Mode, the users of the project may not be
able to modify the git repository of the project. Let's say you forked
a project, then the forked project goes into a read only mode. You won't
be able to modify the git repository of the forked project in that mode.
After the read only mode is gone, you can begin to use the git repository
again. Let's say you decide to add another user to your fork, this time
the project will go in read only mode again but, you still will be able
to use the git repository while the new user will have to wait for read
only mode to get over. This is also true when you remove a user from your
project. The removed user can still access the project's git repository,
given that he had at least commit access, until the read only mode is over.

In Pagure, we use gitolite for Access Control Lists when using SSH.
Modifying gitolite may be a time taking task (depending on number of projects
hosted on the pagure instance) that's why Pagure does it outside of HTTP
Request-Response Cycle.

Whenever you fork a project or add/remove a new user/group to project,
gitolite needs to be refreshed in order to put those changes in effect
for ssh based git usage.


Actions that put the project in read only mode
==============================================

All the actions that needs gitolite to be compiled, will bring the
project in read only mode.

* Creating/Forking a project. (only the fork will be in read only mode)
* Adding/Removing a user/group from a project.
