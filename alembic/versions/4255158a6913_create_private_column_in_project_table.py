"""Create private column in project table

Revision ID: 4255158a6913
Revises: 208b0cd232ab
Create Date: 2016-06-06 14:33:47.039207

"""

# revision identifiers, used by Alembic.
revision = '4255158a6913'
down_revision = '208b0cd232ab'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add a private column in the project table
    '''
    op.add_column(
        'projects',
        sa.Column('_private', sa.Boolean, nullable=True, default=False)
    )
    op.execute('''UPDATE "projects" '''
               '''SET _private=False;''')

    op.alter_column(
        'projects',
        column_name='_private', new_column_name='private',
        nullable=False, existing_nullable=True)


def downgrade():
    ''' Remove the private column
    '''
    op.drop_column('projects', 'private')
