"""Add milestone to issues

Revision ID: 36386a60b3fd
Revises: 350efb3f6baf
Create Date: 2016-09-14 11:03:45.673932

"""

# revision identifiers, used by Alembic.
revision = '36386a60b3fd'
down_revision = '350efb3f6baf'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column milestone to the table issues.
    '''
    op.add_column(
        'issues',
        sa.Column('milestone', sa.String(255), nullable=True)
    )


def downgrade():
    ''' Add the column milestone to the table issues.
    '''
    op.add_column(
        'issues',
        sa.Column('milestone', sa.String(255), nullable=True)
    )
