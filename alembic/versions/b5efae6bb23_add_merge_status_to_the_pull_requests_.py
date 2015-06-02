"""Add merge status to the pull_requests table

Revision ID: b5efae6bb23
Revises: None
Create Date: 2015-06-02 16:30:06.199128

"""

# revision identifiers, used by Alembic.
revision = 'b5efae6bb23'
down_revision = None

from alembic import op
from sqlalchemy.dialects.postgresql import ENUM
import sqlalchemy as sa


# Sources for the code: https://bitbucket.org/zzzeek/alembic/issue/67

def upgrade():
    ''' Add the column merge_status to the table pull_requests.
    '''
    enum = ENUM('NO_CHANGE', 'FFORWARD', 'CONFLICTS', 'MERGE',
                name='merge_status_enum', create_type=False)
    enum.create(op.get_bind(), checkfirst=False)
    op.add_column(
        'pull_requests',
        sa.Column('merge_status', enum, nullable=True)
    )

def downgrade():
    ''' Remove the column merge_status from the table pull_requests.
    '''
    ENUM(name="merge_status_enum").drop(op.get_bind(), checkfirst=False)
    op.drop_column('pull_requests', 'merge_status')
