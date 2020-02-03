"""Add branch info to projects_groups

Revision ID: 2b39a728a38f
Revises: 318a4793b360
Create Date: 2020-03-26 21:50:45.899760

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b39a728a38f'
down_revision = '318a4793b360'


def upgrade():
    ''' Add the column branches to the table projects_groups.
    '''
    op.add_column(
        'projects_groups',
        sa.Column('branches', sa.Text, nullable=True)
    )


def downgrade():
    ''' Drop the column branches from the table projects_groups.
    '''
    op.drop_column('projects_groups', 'branches')
