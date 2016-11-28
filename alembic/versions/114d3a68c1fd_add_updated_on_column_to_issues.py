"""add last_update to issues and pull-requests

Revision ID: 114d3a68c1fd
Revises: 5083efccac7
Create Date: 2016-11-15 11:02:30.652540

"""

# revision identifiers, used by Alembic.
revision = '114d3a68c1fd'
down_revision = '5083efccac7'

from alembic import op
import sqlalchemy as sa
import datetime


def upgrade():
    ''' Add the column last_updated to the table issues/pull-requests
    '''
    op.add_column(
        'issues',
        sa.Column('last_updated', sa.DateTime, nullable=True,
            default=datetime.datetime.utcnow,
            onupdate=datetime.datetime.utcnow)
    )
    # Update all the tickets having comments
    op.execute('''
UPDATE "issues" SET last_updated=o_date
FROM (
    SELECT issue_uid, GREATEST(date_created, edited_on) AS o_date
    FROM issue_comments
    ORDER BY o_date DESC
) AS subq
WHERE "issues".uid = issue_uid;''')
    # Update all the tickets without comments
    op.execute('''UPDATE "issues" SET last_updated=date_created '''
               '''WHERE last_updated IS NULL;''')
    # Require `last_updated` no NULL at the DB level
    op.alter_column(
        'issues', 'last_updated',
        nullable=False, existing_nullable=True)

    op.add_column(
        'pull_requests',
        sa.Column('last_updated', sa.DateTime, nullable=True,
            default=datetime.datetime.utcnow,
            onupdate=datetime.datetime.utcnow)
    )
    # Update all the PRs having comments
    op.execute('''
UPDATE "pull_requests" SET last_updated=o_date
FROM (
    SELECT pull_request_uid, GREATEST(date_created, edited_on) AS o_date
    FROM pull_request_comments
    ORDER BY o_date DESC
) AS subq
WHERE "pull_requests".uid = pull_request_uid;''')
    # Update all the PRs without comments
    op.execute('''UPDATE "pull_requests" SET last_updated=date_created '''
               '''WHERE last_updated IS NULL;''')
    # Require `last_updated` no NULL at the DB level
    op.alter_column(
        'pull_requests', 'last_updated',
        nullable=False, existing_nullable=True)


def downgrade():
    ''' Drop the column last_update from the table issues/pull-requests
    '''
    op.drop_column('issues', 'last_updated')
    op.drop_column('pull_requests', 'last_updated')
