"""Add an index on ssh_search_key

Revision ID: 0a8f99c161e2
Revises: ba538b2648b7
Create Date: 2018-10-04 10:49:44.739141

"""

# revision identifiers, used by Alembic.
revision = '0a8f99c161e2'
down_revision = 'ba538b2648b7'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """ Creates an index on ssh_search_key in the deploykeys table.
    """
    op.create_index(
        op.f("ix_deploykeys_deploykeys_ssh_search_key"),
        "deploykeys",
        ["ssh_search_key"],
        unique=True,
    )


def downgrade():
    """ Drop index on ssh_search_key in the deploykeys table.
    """
    op.drop_index(
        op.f("ix_deploykeys_deploykeys_ssh_search_key"),
        table_name="deploykeys"
    )
