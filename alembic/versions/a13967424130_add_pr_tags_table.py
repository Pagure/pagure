"""Add PR tags table

Revision ID: a13967424130
Revises: 01e58ee9eccb
Create Date: 2017-11-05 16:56:01.164976

"""

import datetime

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'a13967424130'
down_revision = '01e58ee9eccb'


def upgrade():
    """ Create the tags_pull_requests to store the tags of pull-requests.
    """
    op.create_table(
        'tags_pull_requests',
        sa.Column(
            'tag_id',
            sa.Integer,
            sa.ForeignKey(
                'tags_colored.id', ondelete='CASCADE', onupdate='CASCADE',
            ),
            primary_key=True),
        sa.Column(
            'request_uid',
            sa.String(32),
            sa.ForeignKey(
                'pull_requests.uid', ondelete='CASCADE', onupdate='CASCADE',
            ),
            primary_key=True),
        sa.Column(
            'date_created',
            sa.DateTime,
            nullable=False,
            default=datetime.datetime.utcnow),
    )


def downgrade():
    """ Delete the tags_pull_requests table. """
    op.drop_table('tags_pull_requests')
