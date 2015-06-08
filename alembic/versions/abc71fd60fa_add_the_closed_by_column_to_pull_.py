"""Add the closed_by column to pull_requests


Revision ID: abc71fd60fa
Revises: 298891e63039
Create Date: 2015-06-08 16:06:18.017110

"""

# revision identifiers, used by Alembic.
revision = 'abc71fd60fa'
down_revision = '298891e63039'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column merge_status to the table pull_requests.
    '''
    op.add_column(
        'pull_requests',
        sa.Column(
            'closed_by_id',
            sa.Integer,
            sa.ForeignKey('users.id', onupdate='CASCADE'),
        )
    )


def downgrade():
    ''' Remove the column merge_status from the table pull_requests.
    '''
    op.drop_column('pull_requests', 'closed_by_id')
