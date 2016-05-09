Using the roadmap feature
=========================

Pagure allows building the roadmap of the project using the tickets and
their tags.

The principal is as follow:

* All the ticket with the tag ``roadmap`` will show up on the roadmap page.
* For each milestones defined in the settings of the project, the roadmap
will group tickets with the corresponding tag.
* Tickets with the tag ``roadmap`` that are not associated with any of the
milestones defined in the settings are group in an ``unplanned`` section.


Example
-------

For a project named ``test`` on ``pagure.io``.



* First, go to the settings page of the project, create the milestones you
like, for example: ``v1.0`` and ``v2.0``.

* For the tickets you want to be on these milestones, go through each of them
and add them the tags: ``roadmap`` in combination with the milestone you want
``v1.0`` or ``v2.0``, or none of them if the ticket is on the roadmap but
not assigned to any milestones.


* And this is how it will look like

.. image:: _static/pagure_roadmap2.png
        :target: _static/pagure_roadmap2.png
