"""Add support for allow_rebase

Revision ID: d7589827abbb
Revises: 802047d28f89
Create Date: 2019-05-09 16:25:58.971712

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd7589827abbb'
down_revision = '802047d28f89'


def upgrade():
    ''' Add the column allow_rebase to the table pull_requests.
    '''
    op.add_column(
        'pull_requests',
        sa.Column('allow_rebase', sa.Boolean, default=False, nullable=True)
    )
    op.execute('''UPDATE "pull_requests" SET allow_rebase=False;''')
    op.alter_column(
        'pull_requests', 'allow_rebase',
        nullable=False, existing_nullable=True)


def downgrade():
    ''' Remove the column allow_rebase from the table pull_requests.
    '''
    op.drop_column('pull_requests', 'allow_rebase')
