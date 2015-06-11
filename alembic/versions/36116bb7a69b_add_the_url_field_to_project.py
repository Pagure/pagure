"""Add the url field to project

Revision ID: 36116bb7a69b
Revises: abc71fd60fa
Create Date: 2015-06-11 12:36:33.544046

"""

# revision identifiers, used by Alembic.
revision = '36116bb7a69b'
down_revision = 'abc71fd60fa'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column url to the table projects.
    '''
    op.add_column(
        'projects',
        sa.Column('url', sa.Text, nullable=True)
    )


def downgrade():
    ''' Remove the column merge_status from the table projects.
    '''
    op.drop_column('projects', 'url')
