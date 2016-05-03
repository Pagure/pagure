"""Add the milestones column

Revision ID: 2aa7b3958bc5
Revises: 443e090da188
Create Date: 2016-05-03 15:59:04.992414

"""

# revision identifiers, used by Alembic.
revision = '2aa7b3958bc5'
down_revision = '443e090da188'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column _milestones to the table projects
    and the column milestone to the table issues.
    '''
    op.add_column(
        'projects',
        sa.Column('_milestones', sa.Text, nullable=True)
    )


def downgrade():
    ''' Drop the column _milestones from the table projects
    and the column milestone from the table issues.
    '''
    op.drop_column('projects', '_milestones')
