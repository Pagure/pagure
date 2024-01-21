"""Drop repoSpanner region column

Revision ID: 5df8314dfc13
Revises: c0bffa4e8fbc
Create Date: 2024-01-21 23:07:25.610148

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5df8314dfc13'
down_revision = 'c0bffa4e8fbc'


def upgrade():
    op.drop_column('projects', 'repospanner_region')


def downgrade():
    op.add_column('projects', sa.Column('repospanner_region', sa.Text(), nullable=True))
