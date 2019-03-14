"""Add the _block_users field

Revision ID: 1a510f2216c0
Revises: 003fcd9e8860
Create Date: 2019-03-14 12:24:32.139377

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a510f2216c0'
down_revision = '003fcd9e8860'


def upgrade():
    ''' Add the column _block_users to the table projects.
    '''
    op.add_column(
        'projects',
        sa.Column('_block_users', sa.Text, nullable=True)
    )


def downgrade():
    ''' Drop the column _block_users from the table projects.
    '''
    op.drop_column('projects', '_block_users')
