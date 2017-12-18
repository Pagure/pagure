"""drop pull_request_check

Revision ID: 46df6466b8fa
Revises: 61ac23e35f86
Create Date: 2017-12-18 12:37:44.833468

"""

# revision identifiers, used by Alembic.
revision = '46df6466b8fa'
down_revision = '61ac23e35f86'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """ Drop the pull_request_check constraint. """
    connection = op.get_bind()
    connection.begin_nested()
    try:
        op.drop_constraint("pull_requests_check", "pull_requests")
    except sa.exc.ProgrammingError:
        connection.connection.connection.rollback()
        print(
            'Ignoring the pull_requests_check '
            'constraint if it does not exist')


def downgrade():
    """ Bring back the pull_request_check constraint. """
    op.create_check_constraint(
        "pull_requests_check",
        "pull_requests",
        'NOT(project_id_from IS NULL AND remote_git IS NULL)'
    )
