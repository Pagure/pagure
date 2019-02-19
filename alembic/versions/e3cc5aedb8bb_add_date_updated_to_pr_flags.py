"""Add date_updated to PR flags

Revision ID: e3cc5aedb8bb
Revises: f16ab75e4d32
Create Date: 2018-11-14 11:45:48.519035

"""

import datetime

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'e3cc5aedb8bb'
down_revision = 'f16ab75e4d32'


def upgrade():
    """ Add date_updated column to pull_request_flags table """
    op.add_column(
        'pull_request_flags',
        sa.Column(
            'date_updated',
            sa.DateTime,
            nullable=True,
            default=datetime.datetime.utcnow,
        )
    )
    op.execute('UPDATE pull_request_flags SET date_updated=date_created')
    op.alter_column(
        'pull_request_flags', 'date_updated', existing_type=sa.DateTime,
        nullable=False, existing_nullable=True)


def downgrade():
    """ Drop the date_updated column from the pull_request_flags table """
    op.drop_column('pull_request_flags', 'date_updated')
