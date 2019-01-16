"""Cascade deleting flags when tokens are deleted

Revision ID: 2b1743f77436
Revises: 5993f9240bcf
Create Date: 2019-01-16 13:38:34.954904

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2b1743f77436'
down_revision = '5993f9240bcf'


def upgrade():
    """ Remove the existing foreign key in pull_request_flags.token_id and
    re-create it with CASCADE on delete and update.
    """
    # alter the constraints
    op.drop_constraint('pull_request_flags_token_id_fkey', 'pull_request_flags')
    op.create_foreign_key(
        u'pull_request_flags_token_id_fkey',
        'pull_request_flags',
        'tokens',
        ['token_id'],
        ['id'],
        ondelete="CASCADE",
        onupdate="CASCADE",
    )


def downgrade():
    """ Remove the existing foreign key in pull_request_flags.token_id and
    re-create it with without specifying the behavior on delete and update.
    """
    op.drop_constraint('pull_request_flags_token_id_fkey', 'pull_request_flags')
    op.create_foreign_key(
        u'pull_request_flags_token_id_fkey',
        'pull_request_flags',
        'tokens',
        ['token_id'],
        ['id'],
    )
