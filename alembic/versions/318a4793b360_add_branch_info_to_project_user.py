"""Add branch info to user_projects

Revision ID: 318a4793b360
Revises: 060b20d6d6e6
Create Date: 2020-03-26 21:49:17.632967

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '318a4793b360'
down_revision = '060b20d6d6e6'


def upgrade():
    ''' Add the column branches to the table user_projects.
    '''
    op.add_column(
        'user_projects',
        sa.Column('branches', sa.Text, nullable=True)
    )


def downgrade():
    ''' Drop the column branches from the table user_projects.
    '''
    op.drop_column('user_projects', 'branches')
