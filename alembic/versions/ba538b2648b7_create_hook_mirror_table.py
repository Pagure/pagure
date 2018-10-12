"""create hook_mirror table

Revision ID: ba538b2648b7
Revises: 19b67f4b9fe4
Create Date: 2018-09-27 12:47:21.975843

"""

# revision identifiers, used by Alembic.
revision = 'ba538b2648b7'
down_revision = '19b67f4b9fe4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """ Create the hook_mirror to store the tags of pull-requests.
    """
    op.create_table(
        'hook_mirror',
        sa.Column(
            'id',
            sa.Integer,
            primary_key=True),
        sa.Column(
            'project_id',
              sa.Integer,
              sa.ForeignKey(
                'projects.id', onupdate='CASCADE', ondelete='CASCADE'
              ),
              nullable=False,
              primary_key=True
        ),
        sa.Column(
            'active',
            sa.Boolean,
            nullable=False,
            default=False
        ),
        sa.Column(
            'public_key',
            sa.Text,
            nullable=True
        ),
        sa.Column(
            'target',
            sa.Text,
            nullable=True
        ),
        sa.Column(
            'last_log',
            sa.Text,
            nullable=True
        )
    )


def downgrade():
    """ Delete the hook_mirror table. """
    op.drop_table('hook_mirror')
