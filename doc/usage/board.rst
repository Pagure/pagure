Using Boards
============

Pagure provides basic `kanban board <https://en.wikipedia.org/wiki/Kanban_(development)>`_ functionality.
This allows the state of issues to be represented visually.
The feature requires a specific, admin-defined tag to appear on a board.
A repository may contain multiple boards, each with a different tag.


Creating a Board
----------------

#. From the ``Settings`` tab, select ``Boards``
#. Click the ``Add a new board`` button
#. Enter a descriptive name in the ``Board name`` text box
#. Select the tag to use in the ``Tag`` drop down
#. Ensure the ``Active`` checkbox is checked
#. Click the ``Update`` button to create the board

After the board is created, add the status columns.

#. While still on the ``Boards`` settings, click the wrench icon button
#. If you want to use the default statuses (``Backlog``, ``Triaged``, ``In Progress``, ``In Review``, ``Done``, ``Blocked``), click the ``Populate with defaults`` button.
#. If you wish to add non-default statuses, click the ``Add new status`` button
    #. Enter a name for the status in the ``Status name`` text box
    #. If you want this status to be the default for issues added to the board, select the ``Default`` radio button.
    #. If you want this status to close the issue, check the ``Close`` check box
    #. Select the ``Color`` for the status on the board. This is for visual distinctness; you do not have to change it.
    #. Repeat until all of the desired statuses are added
#. Click and drag the arrows to reorder the statuses, if desired.
#. Click the ``Update`` button when finished.

Using Boards
------------

To add an issue to a board, add the board's label to the issue.
Alternatively, you can add an existing issue to the board by clicking the plus sign on the desired status column and adding the issue number.

To change the status of an issue. go to the ``Boards`` tab and drag the card on the board into the desired status column.
The status appears on the issue under the ``Boards`` information, but it cannot be changed from the issue.

If you drag an issue to a column that has the ``Close`` boolean set, Pagure will automatically close the issue.

.. note:: If you close an issue directly, Pagure will remove the board's label.
