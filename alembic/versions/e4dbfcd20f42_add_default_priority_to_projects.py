"""Add default_priority to projects

Revision ID: e4dbfcd20f42
Revises: 21292448a775
Create Date: 2017-10-20 13:34:01.323657

"""

# revision identifiers, used by Alembic.
revision = 'e4dbfcd20f42'
down_revision = '21292448a775'


from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add default_priority column to projects table'''

    op.add_column(
        'projects',
        sa.Column('default_priority', sa.Text, nullable=True)
    )

def downgrade():
    ''' Revert the default_priority column added'''
    op.drop_column('projects', 'default_priority')
