"""add notification bool to PR

Revision ID: 58e60d869326
Revises: 1b6d7dc5600a
Create Date: 2016-02-12 12:39:07.839530

"""

# revision identifiers, used by Alembic.
revision = '58e60d869326'
down_revision = '1b6d7dc5600a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column notification to the table pull_request_comments.
    '''
    op.add_column(
        'pull_request_comments',
        sa.Column('notification', sa.Boolean, default=False, nullable=True)
    )
    op.execute('''UPDATE "pull_request_comments" SET notification=False;''')
    op.alter_column(
        'pull_request_comments', 'notification',
        nullable=False, existing_nullable=True)


def downgrade():
    ''' Remove the column notification from the table pull_request_comments.
    '''
    op.drop_column('pull_request_comments', 'notification')
