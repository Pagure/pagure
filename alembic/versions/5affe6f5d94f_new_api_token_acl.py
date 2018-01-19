"""new_api_token_acl

Revision ID: 5affe6f5d94f
Revises: 46df6466b8fa
Create Date: 2018-01-19 15:27:20.332664

"""

# revision identifiers, used by Alembic.
revision = '5affe6f5d94f'
down_revision = '46df6466b8fa'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """ Insert the new ACL into the database. """
    op.execute(
        "INSERT INTO acls ('name', 'description') "
        "VALUES ('pull_request_create', 'Open a new pull-request');"
    )


def downgrade():
    """ Remove the added ACL from the database. """
    op.execute(
        "REMOVE FROM acls WHERE name = 'pull_request_create';"
    )
