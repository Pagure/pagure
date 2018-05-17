"""add_reactions_to_comments

Revision ID: e34e799e4182
Revises: 131ad2dc5bbd
Create Date: 2018-05-17 18:44:32.189208

"""

# revision identifiers, used by Alembic.
revision = 'e34e799e4182'
down_revision = '131ad2dc5bbd'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the _reactions column to table issue_comments.
    '''
    op.add_column(
        'issue_comments',
        sa.Column('_reactions', sa.Text, nullable=True)
    )


def downgrade():
    ''' Remove the column _reactions from table issue_comments.
    '''
    op.drop_column('issue_comments', '_reactions')
