"""Add date_updated to commit flags

Revision ID: 9cb4580e269a
Revises: e3cc5aedb8bb
Create Date: 2018-11-14 11:48:47.436459

"""

import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9cb4580e269a'
down_revision = 'e3cc5aedb8bb'


def upgrade():
    """ Add date_updated column to commit_flags table """
    op.add_column(
        'commit_flags',
        sa.Column(
            'date_updated',
            sa.DateTime,
            nullable=True,
            default=datetime.datetime.utcnow,
        )
    )
    op.execute('UPDATE commit_flags SET date_updated=date_created')
    op.alter_column(
        'commit_flags', 'date_updated',
        nullable=False, existing_nullable=True)


def downgrade():
    """ Drop the date_updated column from the commit_flags table """
    op.drop_column('commit_flags', 'date_updated')
