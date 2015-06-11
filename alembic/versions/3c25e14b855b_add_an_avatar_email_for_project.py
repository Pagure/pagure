"""add an avatar email for project

Revision ID: 3c25e14b855b
Revises: b5efae6bb23
Create Date: 2015-06-08 12:05:13.832348

"""

# revision identifiers, used by Alembic.
revision = '3c25e14b855b'
down_revision = 'b5efae6bb23'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column merge_status to the table projects.
    '''
    op.add_column(
        'projects',
        sa.Column('avatar_email', sa.Text, nullable=True)
    )


def downgrade():
    ''' Remove the column merge_status from the table projects.
    '''
    op.drop_column('projects', 'avatar_email')
