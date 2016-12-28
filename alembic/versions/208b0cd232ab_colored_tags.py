"""colored tags


Revision ID: 208b0cd232ab
Revises: 588eabcd394c
Create Date: 2016-12-27 11:52:53.355838

"""

# revision identifiers, used by Alembic.
revision = '208b0cd232ab'
down_revision = '588eabcd394c'

import collections
import datetime

from alembic import op
import sqlalchemy as sa


try:
    from pagure.lib import model
except ImportError:
    import sys
    sys.path.insert(0, '.')
    from pagure.lib import model


def upgrade():
    """ Alter the DB schema for the changes related to colored tags. """
    engine = op.get_bind()
    Session = sa.orm.scoped_session(sa.orm.sessionmaker())
    Session.configure(bind=engine)
    session = Session()

    projects = collections.defaultdict(list)
    for issue in session.query(model.Issue).all():
        for issuetag in issue.old_tags:
            tag = issuetag.tag
            # Add the tag to the project if it isn't already there
            if tag not in projects[issue.project.id]:
                tagobj = model.TagColored(
                    tag=tag,
                    project_id=issue.project.id)
                session.add(tagobj)
                session.flush()
                projects[issue.project.id].append(tag)
            else:
                tagobj = session.query(
                    model.TagColored
                ).filter(
                    model.TagColored.tag == tag
                ).filter(
                    model.TagColored.project_id == issue.project.id
                ).first()

            # Link the tag to the ticket as it was
            tagissueobj = model.TagIssueColored(
                tag_id=tagobj.id,
                issue_uid=issue.uid,
                date_created=tagobj.date_created,
            )
            session.add(tagissueobj)
            session.flush()
    session.commit()


def downgrade():
    raise ValueError("The colored tags feature can not be un-done")
