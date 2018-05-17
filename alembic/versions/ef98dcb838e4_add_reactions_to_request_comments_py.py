"""add_reactions_to_request_comments.py

Revision ID: ef98dcb838e4
Revises: e34e799e4182
Create Date: 2018-06-02 19:47:52.975503

"""

# revision identifiers, used by Alembic.
revision = 'ef98dcb838e4'
down_revision = 'e34e799e4182'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the _reactions column to table pull_request_comments.
    '''
    op.add_column(
        'pull_request_comments',
        sa.Column('_reactions', sa.Text, nullable=True)
    )


def downgrade():
    ''' Remove the column _reactions from table pull_request_comments.
    '''
    op.drop_column('pull_request_comments', '_reactions')
