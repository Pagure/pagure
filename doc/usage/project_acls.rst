Project Level Access Control
============================

Till release 2.12, pagure had a very simple user model. If we added a new
user or a new group to a project, the user/group would be an admin of the project.
The user/group  could do everything from changing the status of an issue to adding
or removing any user on the project. With project ACL feature, we allow a more fine
grained control over what a new user/group has access to, what things it can add or
what actions it can take.

With Project ACL feature, We can now have three levels of access:

* Ticket: A user or a group with this level of access can only edit metadata
  of an issue. This includes changing the status of an issue, adding/removing
  tags from them, adding/removing assignees and every other option which can
  be accessed when you click "Edit Metadata" button in an issue page. However,
  this user can not "create" a new tag or "delete" an existing tag because,
  that would involve access to settings page of the project which this user
  won't have. It also won't be able to "delete" the issue because, it falls
  outside of "Edit Metadata".

* Commit: A user or a group with this level of access can do everything what
  a user/group with ticket access can do + it can do everything on the project
  which doesn't include access to settings page. It can "Edit Metadata" of an issue
  just like a user with ticket access would do, can merge a pull request, can push
  to the main repository directly, delete an issue, cancel a pull request etc.

* Admin: The user/group with this access has access to everything on the project.
  All the "users" of the project that have been added till now are having this access.
  They can change the settings of the project, add/remove users/groups on the project.

Add/Update Access
=================

* Everytime you add a new user or a new group to the project, you will be asked to
  provide the level of access you want to give to that user or group. It's a required
  field in the form.

* To add a user or a group to a project, go to settings page of the project. There are
  buttons with text: *Add User* and *Add Group*. It will take you to a different page where
  you will have to select the user or group (depending on whether you clicked Add User
  or Add Group) and the access you want the user/group to have.

* If you want to update a user or a group's access, go to settings page of the project.
  There is a section which lists users associated with the project with the buttons to edit their
  access and a different button to remove them from the project. If you click the edit
  button, you will be taken to a different page where you can change the access and then
  click on Update button.

Points to be noted
==================

* The creator of a project in pagure holds a more unique position than a normal user
  with admin access. The creator can not be removed by an admin. His access level
  can not be changed. But, an admin's access can be updated by a fellow admin
  or the creator himself.

* All the members of a group will have same access over the project except for the case
  mentioned in the next point.

* In cases when, a user is added to a project with an access level of "A" and a group
  is also added to the same project with access level "B" and that user is also present
  in the group then, the user will enjoy the access of higher of "A" and "B". Meaning,
  if the user earlier had access of ticket and the group had access of commit, the user
  will enjoy the access of a committer. And, if the user earlier had access of commit and
  the group had access of ticket, the user will still be a committer.
