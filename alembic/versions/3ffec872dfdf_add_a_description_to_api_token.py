"""Add a description to api token

Revision ID: 3ffec872dfdf
Revises: 770149d96e24
Create Date: 2017-03-23 11:30:34.827399

"""

# revision identifiers, used by Alembic.
revision = '3ffec872dfdf'
down_revision = '770149d96e24'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the column description to the table tokens
    '''
    op.add_column(
        'tokens',
        sa.Column('description', sa.Text, nullable=True)
    )


def downgrade():
    ''' Drop the column description from the table tokens.
    '''
    op.drop_column('tokens', 'description')
