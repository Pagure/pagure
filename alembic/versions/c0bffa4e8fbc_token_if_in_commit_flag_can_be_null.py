"""token_if in commit flag can be null

Revision ID: c0bffa4e8fbc
Revises: 2b39a728a38f
Create Date: 2021-01-08 11:12:45.380762

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c0bffa4e8fbc'
down_revision = '2b39a728a38f'


def upgrade():
    op.alter_column(
        'commit_flags',
        column_name='token_id',
        nullable=False,
        existing_nullable=True
    )


def downgrade():
    op.alter_column(
        'commit_flags',
        column_name='token_id',
        nullable=True,
        existing_nullable=False
    )
