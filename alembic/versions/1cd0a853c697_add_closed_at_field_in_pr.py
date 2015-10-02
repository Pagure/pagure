"""Add closed_at field in PR


Revision ID: 1cd0a853c697
Revises: 6190226bed0
Create Date: 2015-10-02 09:32:15.370676

"""

# revision identifiers, used by Alembic.
revision = '1cd0a853c697'
down_revision = '6190226bed0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column closed_at to the table pull_requests.
    '''
    op.add_column(
        'pull_requests',
        sa.Column(
            'closed_at',
            sa.DateTime,
            nullable=True,
        )
    )

    op.execute('''UPDATE "pull_requests" SET closed_at=date_created '''
               '''WHERE STATUS != 'Open';''')


def downgrade():
    ''' Remove the column closed_at from the table pull_requests.
    '''
    op.drop_column('pull_requests', 'closed_at')
