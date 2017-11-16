"""Migrate current flag

Revision ID: 6119fbbcc8e9
Revises: 2b626a16542e
Create Date: 2017-11-16 15:11:28.199971

"""

# revision identifiers, used by Alembic.
revision = '6119fbbcc8e9'
down_revision = '2b626a16542e'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """ Add the status column to pull_request_flags and migrate the data.
    """
    op.add_column(
        'pull_request_flags',
        sa.Column('status', sa.String(32), nullable=True)
    )
    op.execute(
        'UPDATE pull_request_flags SET status=\'success\' '
        'WHERE percent in (100, \'100\')')
    op.execute(
        'UPDATE pull_request_flags SET status=\'failure\' '
        'WHERE percent not in (100, \'100\')')
    op.alter_column(
        'pull_request_flags', 'status',
        nullable=False, existing_nullable=True)


def downgrade():
    """ Drop the status column in pull_request_flags.

    We can't undo the change to the status column since it may now
    contain empty rows.

    """
    op.drop_column('pull_request_flags', 'status')
