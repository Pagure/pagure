"""Read Only mode in projects

Revision ID: 3237fc64b306
Revises: c34f4b09ef18
Create Date: 2017-09-01 22:51:18.232541

"""

# revision identifiers, used by Alembic.
revision = '3237fc64b306'
down_revision = 'c34f4b09ef18'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add a column to mark a project read only '''
    op.add_column(
        'projects',
        sa.Column(
            'read_only',
            sa.Boolean,
            default=True,
            nullable=True,
        )
    )
    op.execute(''' UPDATE projects SET read_only=False ''')
    op.alter_column(
        'projects',
        'read_only',
        nullable=False,
        existing_nullable=True
    )


def downgrade():
    ''' Remove the read_only column from Projects '''
    op.drop_column('projects', 'read_only')
