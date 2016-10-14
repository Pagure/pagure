"""Create the _settings fields for user

Revision ID: 5083efccac7
Revises: 26af5c3602a0
Create Date: 2016-10-13 16:21:08.716951

"""

# revision identifiers, used by Alembic.
revision = '5083efccac7'
down_revision = '26af5c3602a0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column _settings to the table users.
    '''
    op.add_column(
        'users',
        sa.Column('_settings', sa.Text, nullable=True)
    )


def downgrade():
    ''' Add the column _settings to the table users.
    '''
    op.drop_column('users', '_settings')
