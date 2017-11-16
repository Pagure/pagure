"""Adjust constraints on pull_request_flags

Revision ID: 01e58ee9eccb
Revises: 6119fbbcc8e9
Create Date: 2017-11-16 16:50:47.278252

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '01e58ee9eccb'
down_revision = '6119fbbcc8e9'


def upgrade():
    """ Remove the unique constraints on UID in pull_request_flags and make
    it a composite unique constraint on UID + pull_request_uid.
    """
    # alter the constraints
    op.drop_constraint('pull_request_flags_uid_key', 'pull_request_flags')
    op.create_unique_constraint(
            "pull_request_flags_uid_pull_request_uid_key",
            'pull_request_flags',
            ["uid", "pull_request_uid"]
    )


def downgrade():
    """ Remove the composite unique constraints on UID + pull_request_uid
    in pull_request_flags and make it an unique constraint on UID .
    """
    op.drop_constraint(
        'pull_request_flags_uid_pull_request_uid_key',
        'pull_request_flags')
    op.create_unique_constraint(
            "pull_request_flags_uid_key",
            'pull_request_flags',
            ["uid"]
    )
