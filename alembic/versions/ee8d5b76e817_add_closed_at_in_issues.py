"""add_closed_at_in_issues

Revision ID: ee8d5b76e817
Revises: 317a285e04a8
Create Date: 2016-06-28 18:04:05.539319

"""

# revision identifiers, used by Alembic.
revision = 'ee8d5b76e817'
down_revision = '317a285e04a8'

from alembic import op
import sqlalchemy as sa

def upgrade():
    ''' Add closed_at column in issues table '''
    op.add_column(
            'issues',
            sa.Column('closed_at', sa.DateTime, nullable=True)
    )


def downgrade():
    ''' Remove the closed_at column in issues table '''
    op.drop_column('issues', 'closed_at')
