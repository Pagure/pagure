"""Adding column to store edited_by and edited_on a commnet

Revision ID: 15ea3c2cf83d
Revises: 21f45b08d882
Create Date: 2015-11-09 16:18:47.192088

"""

# revision identifiers, used by Alembic.
revision = '15ea3c2cf83d'
down_revision = '21f45b08d882'

from alembic import op
import sqlalchemy as sa


def upgrade():

    op.add_column(
        'pull_request_comments',
        sa.Column(
            'editor_id',
            sa.Integer,
            sa.ForeignKey('users.id', onupdate='CASCADE'),
            nullable=True)
    )

    op.add_column(
        'pull_request_comments',
        sa.Column(
            'edited_on',
            sa.DATETIME,
            nullable=True)
    )


def downgrade():
    op.drop_column('pull_request_comments', 'editor_id')
    op.drop_column('pull_request_comments', 'edited_on')
