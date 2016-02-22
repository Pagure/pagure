"""Add the tree_id column to PR inline comments

Revision ID: 1f3de3853a1a
Revises: 58e60d869326
Create Date: 2016-02-22 16:13:59.943083

"""

# revision identifiers, used by Alembic.
revision = '1f3de3853a1a'
down_revision = '58e60d869326'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column tree_id to the table pull_request_comments.
    '''
    op.add_column(
        'pull_request_comments',
        sa.Column('tree_id', sa.String(40), nullable=True)
    )


def downgrade():
    ''' Remove the column tree_id from the table pull_request_comments.
    '''
    op.drop_column('pull_request_comments', 'tree_id')
