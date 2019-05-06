"""Drop unique constraint on commit UID

Revision ID: 802047d28f89
Revises: 5a2327825b9a
Create Date: 2019-05-06 12:52:25.221300

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '802047d28f89'
down_revision = '5a2327825b9a'


def upgrade():
    """ Remove the constraint named: commit_flags_uid_key, pass otherwise. """
    try:
        op.drop_constraint('commit_flags_uid_key', 'commit_flags')
    except:
        pass


def downgrade():
    """ We do not want to go back in fact. """
    pass
