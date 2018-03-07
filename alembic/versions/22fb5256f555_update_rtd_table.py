"""Update RTD table

Revision ID: 22fb5256f555
Revises: 5affe6f5d94f
Create Date: 2018-03-07 15:46:26.478238

"""

# revision identifiers, used by Alembic.
revision = '22fb5256f555'
down_revision = '5affe6f5d94f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Update the hook_rtd table for the new data structure it should use.
    '''
    op.add_column(
        'hook_rtd',
        sa.Column('api_url', sa.Text, nullable=True)
    )
    op.add_column(
        'hook_rtd',
        sa.Column('api_token', sa.Text, nullable=True)
    )
    op.drop_column('hook_rtd', 'project_name')


def downgrade():
    ''' Downgrade the structure of the hook_rtd table.
    '''
    op.drop_column('hook_rtd', 'api_url')
    op.drop_column('hook_rtd', 'api_token')
    op.add_column(
        'hook_rtd',
        sa.Column('project_name', sa.Text, nullable=True)
    )
