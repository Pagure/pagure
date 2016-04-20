"""up to 255 characters for project.name

Revision ID: 443e090da188
Revises: 496f7a700f2e
Create Date: 2016-04-20 17:57:36.385103

"""

# revision identifiers, used by Alembic.
revision = '443e090da188'
down_revision = '496f7a700f2e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.alter_column(
        table_name='projects',
        column_name='name',
        type_=sa.String(255),
        existing_type=sa.String(32)
    )


def downgrade():
     op.alter_column(
        table_name='projects',
        column_name='name',
        type_=sa.String(32),
        existing_type=sa.String(255)
    )
