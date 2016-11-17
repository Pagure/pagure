"""add quick_replies field to project

Revision ID: 588eabcd394c
Revises: 5083efccac7
Create Date: 2016-11-17 16:12:36.624079

"""

# revision identifiers, used by Alembic.
revision = '588eabcd394c'
down_revision = '349a3890596'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column _quick_replies to the table projects
    '''
    op.add_column(
        'projects',
        sa.Column('_quick_replies', sa.Text, nullable=True)
    )


def downgrade():
    ''' Drop the column _quick_replies from the table projects.
    '''
    op.drop_column('projects', '_quick_replies')
