"""Add date_modified for project

Revision ID: 8a5d68f74beb
Revises: 27a79ff0fb41
Create Date: 2017-07-18 19:28:09.566997

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '8a5d68f74beb'
down_revision = '27a79ff0fb41'


def upgrade():
    ''' Add the column date_modified to the table projects.
    '''
    op.add_column(
        'projects',
        sa.Column('date_modified', sa.DateTime, nullable=True,
                  default=sa.func.now())
    )
    op.execute("UPDATE projects SET date_modified=date_created;")

    op.alter_column(
        'projects',
        column_name='date_modified',
        nullable=False,
        exisiting_nullable=True)


def downgrade():
    ''' Remove the column date_modified from the table projects.
    '''
    op.drop_column('projects', 'date_modified')
