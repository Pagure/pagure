"""Add the remote_git entry

Revision ID: 257a7ce22682
Revises: 36116bb7a69b
Create Date: 2015-07-21 14:26:23.989220

"""

# revision identifiers, used by Alembic.
revision = '257a7ce22682'
down_revision = '36116bb7a69b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column remote_git to the table pull_requests and make the
    project_id_from field nullable.
    '''
    op.add_column(
        'pull_requests',
        sa.Column('remote_git', sa.Text, nullable=True)
    )
    op.alter_column(
        'pull_requests',
        column_name='project_id_from',
        nullable=True,
        existing_nullable=False)


def downgrade():
    ''' Remove the column remote_git from the table pull_requests and make
    the project_id_from field not nullable.
    '''
    op.drop_column('pull_requests', 'remote_git')
    op.alter_column(
        'pull_requests',
        column_name='project_id_from',
        nullable=False,
        existing_nullable=True)
