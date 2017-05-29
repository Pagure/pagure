"""Add lock types

Revision ID: 5179e99d35a5
Revises: d4d2c5aa8a0
Create Date: 2017-05-30 14:47:55.063908

"""

# revision identifiers, used by Alembic.
revision = '5179e99d35a5'
down_revision = 'd4d2c5aa8a0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.create_table(
        'project_locks',
        sa.Column('project_id',
                  sa.Integer,
                  sa.ForeignKey(
                    'projects.id', onupdate='CASCADE', ondelete='CASCADE'
                  ),
                  nullable=False,
                  primary_key=True
        ),
        sa.Column('lock_type',
                  sa.Enum(
                    'WORKER',
                    name='lock_type_enum'
                  ),
                  nullable=False,
                  primary_key=True
        )
    )

    # Add WORKER locks everywhere
    conn = op.get_bind()
    conn.execute("""INSERT INTO project_locks (project_id, lock_type)
                    SELECT id, 'WORKER' from projects""")


def downgrade():
    op.drop_table('project_locks')
