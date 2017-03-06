"""Add key_notify to the issues_keys table

Revision ID: 11470abae0d6
Revises: 987edda096f5
Create Date: 2017-03-04 10:19:14.842910

"""

# revision identifiers, used by Alembic.
revision = '11470abae0d6'
down_revision = '987edda096f5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add a column to record if the custom field should trigger a email
    notification.
    '''
    op.add_column(
        'issue_keys',
        sa.Column(
            'key_notify', sa.Boolean, default=False, nullable=True
        )
    )
    op.execute('UPDATE issue_keys SET key_notify=False')
    op.alter_column(
        'issue_keys', 'key_notify',
        nullable=False, existing_nullable=True)


def downgrade():
    ''' Remove the key_notify column.
    '''
    op.drop_column('issue_keys', 'key_notify')
