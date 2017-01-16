"""Add description for tags

Revision ID: 6addaed6008e
Revises: 208b0cd232ab
Create Date: 2017-01-14 23:38:15.631750

"""

# revision identifiers, used by Alembic.
revision = '6addaed6008e'
down_revision = '208b0cd232ab'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column notification to the table pull_request_comments.
    '''
    op.add_column(
        'tags_colored',
        sa.Column('tag_description', sa.String(255), default="")
    )

def downgrade():
    op.drop_column('tags_colored', 'tag_description')
