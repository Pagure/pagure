"""Store the user who closed an issue in the db

Revision ID: 1f24c9c8efa5
Revises: 6a3ed02ee160
Create Date: 2018-12-04 13:02:57.101095

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1f24c9c8efa5"
down_revision = "6a3ed02ee160"


def upgrade():

    op.add_column(
        "issues",
        sa.Column(
            "closed_by_id",
            sa.Integer,
            sa.ForeignKey("users.id", onupdate="CASCADE"),
        ),
    )


def downgrade():
    op.drop_column("issues", "closed_by_id")
