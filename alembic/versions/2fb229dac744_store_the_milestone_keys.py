"""Store the milestone keys

Revision ID: 2fb229dac744
Revises: e4dbfcd20f42
Create Date: 2017-10-31 13:03:10.767348

"""

# revision identifiers, used by Alembic.
revision = '2fb229dac744'
down_revision = 'e4dbfcd20f42'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column _milestones_keys to the table projects.
    '''
    op.add_column(
        'projects',
        sa.Column('_milestones_keys', sa.Text, nullable=True)
    )


def downgrade():
    ''' Drop the column _milestones_keys from the table projects.
    '''
    op.drop_column('projects', '_milestones_keys')
