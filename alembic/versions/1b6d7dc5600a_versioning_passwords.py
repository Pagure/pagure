"""versioning_passwords

Revision ID: 1b6d7dc5600a
Revises: 3b441ef4e928
Create Date: 2016-01-13 07:57:23.465676

"""

# revision identifiers, used by Alembic.
revision = '1b6d7dc5600a'
down_revision = '3b441ef4e928'

from alembic import op
import sqlalchemy as sa


def upgrade():
        op.execute('''UPDATE "users" SET password = '$1$' || password;''')



def downgrade():
        raise ValueError("Password can not be downgraded")
