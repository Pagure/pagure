"""Add repoSpanner region column

Revision ID: 19b67f4b9fe4
Revises: ef98dcb838e4
Create Date: 2018-09-08 13:27:31.978954

"""

# revision identifiers, used by Alembic.
revision = '19b67f4b9fe4'
down_revision = 'ef98dcb838e4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('projects', sa.Column('repospanner_region', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('projects', 'repospanner_region')
