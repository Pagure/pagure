"""expand enum for lock types

Revision ID: 7f31a9fad89f
Revises: 369deb8c8b63
Create Date: 2018-04-16 15:01:00.280469

"""

# revision identifiers, used by Alembic.
revision = '7f31a9fad89f'
down_revision = '369deb8c8b63'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """
    Add new lock types to the lock_type_enum enum.

    With this there are three enums:
      - WORKER, used to lock action on the main git repo (sources)
      - WORKER_TICKET, used to lock actions on the ticket git repo
      - WORKER_REQUEST, used to lock actions on the request git repo
    """

    # Let's start with commit to close the current transaction
    # cf https://bitbucket.org/zzzeek/alembic/issue/123
    op.execute('COMMIT')
    op.execute(
        "ALTER TYPE lock_type_enum ADD VALUE 'WORKER_TICKET';")
    op.execute(
        "ALTER TYPE lock_type_enum ADD VALUE 'WORKER_REQUEST';")


def downgrade():
    """Raise an exception explaining that this migration cannot be reversed."""
    raise NotImplemented('This migration cannot be reversed.')
