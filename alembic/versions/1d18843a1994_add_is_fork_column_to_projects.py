"""Add is_fork column to projects

Revision ID: 1d18843a1994
Revises: 32d636cb5e00
Create Date: 2016-07-17 22:02:14.495146

"""

# revision identifiers, used by Alembic.
revision = '1d18843a1994'
down_revision = '32d636cb5e00'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add is_fork column to project table'''

    op.add_column(
        'projects',
        sa.Column(
            'is_fork', sa.Boolean,
            default=False,
            nullable=True)
    )

    op.execute('''UPDATE "projects" '''
               '''SET is_fork=TRUE WHERE parent_id IS NOT NULL;''')
    op.execute('''UPDATE "projects" '''
               '''SET is_fork=FALSE WHERE parent_id IS NULL;''')

    op.alter_column(
        'projects', 'is_fork',
        nullable=False, existing_nullable=True)

def downgrade():
    ''' Revert the _is_fork column added'''
    op.drop_column('projects', 'is_fork')
