"""Add the initial_comment on the PR table

Revision ID: 4cae55a80a42
Revises: 1f3de3853a1a
Create Date: 2016-03-01 12:00:34.823097

"""

# revision identifiers, used by Alembic.
revision = '4cae55a80a42'
down_revision = '1f3de3853a1a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column initial_comment to the table pull_requests.
    '''
    op.add_column(
        'pull_requests',
        sa.Column('initial_comment', sa.Text, nullable=True)
    )


def downgrade():
    ''' Remove the column initial_comment from the table pull_requests.
    '''
    op.drop_column('pull_requests', 'initial_comment')
