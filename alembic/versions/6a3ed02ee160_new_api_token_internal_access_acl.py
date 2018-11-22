"""empty message

Revision ID: 6a3ed02ee160
Revises: 9cb4580e269a
Create Date: 2018-11-22 14:36:59.024463

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6a3ed02ee160'
down_revision = '9cb4580e269a'


def upgrade():
    """ Insert the new ACL into the database. """
    op.execute(
        'INSERT INTO acls ("name", "description", "created") '
        "VALUES ('internal_access', 'Access Pagure''s internal APIs', NOW());"
    )


def downgrade():
    """ Remove the added ACL from the database. """
    op.execute(
        "REMOVE FROM acls WHERE name = 'internal_access';"
    )
