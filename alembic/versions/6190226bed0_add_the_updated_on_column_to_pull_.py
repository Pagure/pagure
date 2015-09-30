"""Add the updated_on column to pull-requests

Revision ID: 6190226bed0
Revises: 257a7ce22682
Create Date: 2015-09-29 15:32:58.229183

"""

# revision identifiers, used by Alembic.
revision = '6190226bed0'
down_revision = '257a7ce22682'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column updated_on to the table pull_requests.
    '''
    op.add_column(
        'pull_requests',
        sa.Column(
            'updated_on',
            sa.DateTime,
            nullable=True,
            default=sa.func.now(),
            onupdate=sa.func.now()
        )
    )

    op.execute('''UPDATE "pull_requests" SET updated_on=date_created;''')

    op.alter_column(
        'pull_requests',
        column_name='updated_on',
        nullable=False,
        existing_nullable=True)


def downgrade():
    ''' Remove the column updated_on from the table pull_requests.
    '''
    op.drop_column('pull_requests', 'updated_on')
