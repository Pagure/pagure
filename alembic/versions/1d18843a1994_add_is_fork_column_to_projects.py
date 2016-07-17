"""Add is_fork column to projects

Revision ID: 1d18843a1994
Revises: 43df5e588a87
Create Date: 2016-07-17 22:02:14.495146

"""

# revision identifiers, used by Alembic.
revision = '1d18843a1994'
down_revision = '43df5e588a87'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add is_fork column to project table'''

    op.add_column(
        'projects',
        sa.Column(
            '__is_fork', sa.Boolean,
            default=False,
            nullable=True)
    )

    op.execute('''UPDATE "projects" '''
               '''SET __is_fork=TRUE WHERE parent_id IS NOT NULL;''')
    op.execute('''UPDATE "projects" '''
               '''SET __is_fork=FALSE WHERE parent_id IS NULL;''')


    op.alter_column(
        'projects',
        column_name='__is_fork', new_column_name='_is_fork',
        nullable=False, existing_nullable=True)

def downgrade():
    ''' Revert the _is_fork column added'''
    op.drop_column('projects', '_is_fork')
