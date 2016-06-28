"""add_closed_at_attribute_in_issues

Revision ID: 43df5e588a87
Revises: 22db0a833d35
Create Date: 2016-06-28 22:59:36.653905

"""

# revision identifiers, used by Alembic.
revision = '43df5e588a87'
down_revision = '22db0a833d35'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add closed_at column in issues table '''
    op.add_column(
            'issues',
            sa.Column('closed_at', sa.DateTime, nullable=True)
    )


def downgrade():
    ''' Remove the closed_at column in issues table '''
    op.drop_column('issues', 'closed_at')
