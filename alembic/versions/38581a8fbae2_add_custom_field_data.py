"""Add custom field data

Revision ID: 38581a8fbae2
Revises: 208b0cd232ab
Create Date: 2017-01-16 13:03:36.683188

"""

# revision identifiers, used by Alembic.
revision = '38581a8fbae2'
down_revision = '208b0cd232ab'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add a new drop-down list type to the custom fields.  The list options
    need to be stored in the issue_keys table. '''
    op.add_column('issue_keys', sa.Column('key_data', sa.Text()))


def downgrade():
    ''' Remove the key_data column '''
    op.drop_column('issue_keys', 'key_data')
