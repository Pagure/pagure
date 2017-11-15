"""commit flag

Revision ID: 2b626a16542e
Revises: 2fb229dac744
Create Date: 2017-11-15 10:06:55.088665

"""

import datetime

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2b626a16542e'
down_revision = '2fb229dac744'


def upgrade():
    ''' Create the commit_flags table. '''

    op.create_table(
        'commit_flags',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('uid', sa.String(32), unique=True, nullable=False),
        sa.Column('commit_hash', sa.String(40), index=True, nullable=False),
        sa.Column(
            'token_id', sa.String(64),
            sa.ForeignKey('tokens.id'), nullable=False),
        sa.Column(
            'project_id',
            sa.Integer,
            sa.ForeignKey(
                'projects.id', onupdate='CASCADE', ondelete='CASCADE',
            ),
            nullable=False, index=True),
        sa.Column(
            'user_id', sa.Integer,
            sa.ForeignKey('users.id', onupdate='CASCADE'),
            nullable=False, index=True),
        sa.Column('username', sa.Text(), nullable=False),
        sa.Column('percent', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=False),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column(
            'date_created', sa.DateTime, nullable=False,
            default=datetime.datetime.utcnow),
    )


def downgrade():
    ''' Drop the commit_flags table. '''

    op.drop_table('commit_flags')
