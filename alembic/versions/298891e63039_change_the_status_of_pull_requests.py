"""Change the status of pull_requests


Revision ID: 298891e63039
Revises: 3c25e14b855b
Create Date: 2015-06-08 13:06:11.938966

"""

# revision identifiers, used by Alembic.
revision = '298891e63039'
down_revision = '3c25e14b855b'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Adjust the status column of the pull_requests table.
    '''
    op.add_column(
        'pull_requests',
        sa.Column(
            '_status', sa.Text,
            sa.ForeignKey(
                'status_pull_requests.status', onupdate='CASCADE'),
            default='Open',
            nullable=True)
    )

    op.execute('''UPDATE "pull_requests" '''
               '''SET _status='Open' WHERE status=TRUE;''')
    op.execute('''UPDATE "pull_requests" '''
               '''SET _status='Merged' WHERE status=FALSE;''')

    op.drop_column('pull_requests', 'status')
    op.alter_column(
        'pull_requests',
        column_name='_status', new_column_name='status',
        nullable=False, existing_nullable=True)


def downgrade():
    ''' Revert the status column of the pull_requests table.
    '''
    op.add_column(
        'pull_requests',
        sa.Column(
            '_status', sa.Boolean, default=True, nullable=True)
    )
    op.execute('''UPDATE "pull_requests" '''
               '''SET _status=TRUE WHERE status='Open';''')
    op.execute('''UPDATE "pull_requests" '''
               '''SET _status=FALSE WHERE status!='Open';''')

    op.drop_column('pull_requests', 'status')
    op.alter_column(
        'pull_requests',
        column_name='_status', new_column_name='status',
        nullable=False, existing_nullable=True)
