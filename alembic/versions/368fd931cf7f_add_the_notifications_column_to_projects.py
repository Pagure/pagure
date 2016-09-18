"""Add the notifications column to projects

Revision ID: 368fd931cf7f
Revises: 36386a60b3fd
Create Date: 2016-09-18 18:51:09.625322

"""

# revision identifiers, used by Alembic.
revision = '368fd931cf7f'
down_revision = '36386a60b3fd'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column notifications to the table projects.
    '''
    op.add_column(
        'projects',
        sa.Column('_notifications', sa.String(255), nullable=True)
    )


def downgrade():
    ''' Add the column notifications to the table projects.
    '''
    op.drop_column('projects', '_notifications')
