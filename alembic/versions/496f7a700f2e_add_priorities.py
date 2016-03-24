"""Add priorities

Revision ID: 496f7a700f2e
Revises: 4cae55a80a42
Create Date: 2016-03-24 12:19:34.298752

"""

# revision identifiers, used by Alembic.
revision = '496f7a700f2e'
down_revision = '4cae55a80a42'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column _priorities to the table projects
    and the column priority to the table issues.
    '''
    op.add_column(
        'projects',
        sa.Column('_priorities', sa.Text, nullable=True)
    )

    op.add_column(
        'issues',
        sa.Column('priority', sa.Integer, nullable=True, default=None)
    )


def downgrade():
    ''' Drop the column _priorities from the table projects
    and the column priority from the table issues.
    '''
    op.drop_column('projects', '_priorities')
    op.drop_column('issues', 'priority')
