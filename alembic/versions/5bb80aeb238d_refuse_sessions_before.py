"""refuse_sessions_before

Revision ID: 5bb80aeb238d
Revises: 7f31a9fad89f
Create Date: 2018-05-03 16:39:34.974914

"""

# revision identifiers, used by Alembic.
revision = '5bb80aeb238d'
down_revision = '7f31a9fad89f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column _reports to the table projects
    '''
    op.add_column(
        'users',
        sa.Column(
            'refuse_sessions_before', sa.DateTime, nullable=True,
            server_default=None)
    )


def downgrade():
    ''' Drop the column _reports from the table projects.
    '''
    op.drop_column('users', 'refuse_sessions_before')
