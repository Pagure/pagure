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
            default=sa.datetime.datetime.utcnow,
            onupdate=datetime.datetime.utcnow)
    )
    op.add_column(
        'pull_requests',
        sa.Column('last_updated', sa.DateTime, nullable=True,
            default=sa.datetime.datetime.utcnow,
            onupdate=datetime.datetime.utcnow)
    )


def downgrade():
    ''' Drop the column last_update from the table issues/pull-requests
    '''
    op.drop_column('issues', 'last_updated')
    op.drop_column('pull_requests', 'last_updated')
