"""Create deploy keys table

Revision ID: 8a3b10926153
Revises: 38581a8fbae2
Create Date: 2017-02-09 12:45:59.553111

"""

# revision identifiers, used by Alembic.
revision = '8a3b10926153'
down_revision = '38581a8fbae2'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table('deploykeys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('pushaccess', sa.Boolean(), nullable=False),
        sa.Column('public_ssh_key', sa.Text(), nullable=False),
        sa.Column('ssh_short_key', sa.Text(), nullable=False),
        sa.Column('ssh_search_key', sa.Text(), nullable=False),
        sa.Column('creator_user_id', sa.Integer(), nullable=False),
        sa.Column('date_created', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['creator_user_id'], ['users.id'], name=op.f('deploykeys_creator_user_id_fkey'), onupdate='CASCADE'),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('deploykeys_project_id_fkey'), onupdate='CASCADE', ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id', name=op.f('deploykeys_pkey'))
    )
    op.create_index(op.f('ix_deploykeys_deploykeys_creator_user_id'), 'deploykeys', ['creator_user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_deploykeys_deploykeys_creator_user_id'), table_name='deploykeys')
    op.drop_table('deploykeys')
