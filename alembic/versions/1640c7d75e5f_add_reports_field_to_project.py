"""Add reports field to project

Revision ID: 1640c7d75e5f
Revises: 1d18843a1994
Create Date: 2016-09-09 16:11:28.099423

"""

# revision identifiers, used by Alembic.
revision = '1640c7d75e5f'
down_revision = '1d18843a1994'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column _reports to the table projects
    '''
    op.add_column(
        'projects',
        sa.Column('_reports', sa.Text, nullable=True)
    )


def downgrade():
    ''' Drop the column _reports from the table projects.
    '''
    op.drop_column('projects', '_reports')
