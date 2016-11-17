"""Increase length group name

Revision ID: 349a3890596
Revises: 5083efccac7
Create Date: 2016-11-30 14:30:15.681269

"""

# revision identifiers, used by Alembic.
revision = '349a3890596'
down_revision = '114d3a68c1fd'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Increase the length of group_name to 255 characters instead of 16.
    '''
    op.alter_column(
        'pagure_group', 'group_name',
        type_=sa.String(255),
        existing_type=sa.String(16)
    )


def downgrade():
    ''' Decrease the length of group_name to 16 characters instead of 255.
    '''
    op.alter_column(
        'pagure_group', 'group_name',
        type_=sa.String(16),
        existing_type=sa.String(255)
    )
