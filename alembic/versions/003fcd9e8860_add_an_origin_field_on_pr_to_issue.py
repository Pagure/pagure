"""Add an origin field on pr_to_issue

Revision ID: 003fcd9e8860
Revises: 2b1743f77436
Create Date: 2019-03-12 14:55:59.316861

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '003fcd9e8860'
down_revision = '2b1743f77436'


def upgrade():
    ''' Add a column to record if the custom field should trigger a email
    notification.
    '''
    op.add_column(
        'pr_to_issue',
        sa.Column(
            'origin', sa.String(32), index=True
        )
    )


def downgrade():
    ''' Remove the key_notify column.
    '''
    op.drop_column('pr_to_issue', 'origin')
