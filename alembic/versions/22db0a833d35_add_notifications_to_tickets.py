"""Add notifications to tickets

Revision ID: 22db0a833d35
Revises: 317a285e04a8
Create Date: 2016-06-27 16:10:33.395495

"""

# revision identifiers, used by Alembic.
revision = '22db0a833d35'
down_revision = '317a285e04a8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column notification to the table issue_comments.
    '''
    op.add_column(
        'issue_comments',
        sa.Column('notification', sa.Boolean, default=False, nullable=True)
    )
    op.execute('''UPDATE "issue_comments" SET notification=False;''')
    op.alter_column(
        'issue_comments', 'notification',
        nullable=False, existing_nullable=True)


def downgrade():
    ''' Remove the column notification from the table issue_comments.
    '''
    op.drop_column('issue_comments', 'notification')
