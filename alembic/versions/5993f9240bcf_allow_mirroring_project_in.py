"""Allow mirroring project in

Revision ID: 5993f9240bcf
Revises: 1f24c9c8efa5
Create Date: 2018-12-14 10:00:05.281979

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5993f9240bcf'
down_revision = '1f24c9c8efa5'


def upgrade():
    ''' Add the column mirrored_from to the table projects.
    '''
    op.add_column(
        'projects',
        sa.Column('mirrored_from', sa.Text, nullable=True)
    )
    op.add_column(
        'projects',
        sa.Column('mirrored_from_last_log', sa.Text, nullable=True)
    )


def downgrade():
    ''' Remove the column mirrored_from from the table projects.
    '''
    op.drop_column('projects', 'mirrored_from')
    op.drop_column('projects', 'mirrored_from_last_log')
