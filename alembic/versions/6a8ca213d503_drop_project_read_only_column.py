"""Drop project read_only column

Revision ID: 6a8ca213d503
Revises: 5df8314dfc13
Create Date: 2024-04-24 21:49:11.394451

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '6a8ca213d503'
down_revision = '5df8314dfc13'


def upgrade():
    op.drop_column('projects', 'read_only')


def downgrade():
    op.add_column('projects', sa.Column('read_only', sa.Boolean(), default=True, nullable=False))
