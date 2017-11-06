"""private pull-request

Revision ID: 47f5fab6f46a
Revises: a13967424130
Create Date: 2017-11-06 11:37:57.460886

"""


from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '47f5fab6f46a'
down_revision = 'a13967424130'

def upgrade():
    ''' Add a private column in the pull_requests table
    '''
    op.add_column(
        'pull_requests',
        sa.Column('private', sa.Boolean, nullable=True, default=False)
    )
    op.execute('''UPDATE "pull_requests" '''
               '''SET private=False;''')

    op.alter_column(
        'pull_requests',
        column_name='private',
        nullable=False, existing_nullable=True)


def downgrade():
    ''' Remove the private column
    '''
    op.drop_column('pull_requests', 'private')
