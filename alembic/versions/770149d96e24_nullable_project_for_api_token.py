"""nullable project for api token

Revision ID: 770149d96e24
Revises: 987edda096f5
Create Date: 2017-03-04 18:05:07.956057

"""

# revision identifiers, used by Alembic.
revision = '770149d96e24'
down_revision = '987edda096f5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """ Make the field 'project_id' of the table tokens be nullable. """
    op.alter_column(
        'tokens',
        'project_id',
        nullable=True,
        existing_nullable=False,
    )


def downgrade():
    """ Make the field 'project_id' of the table tokens be not nullable.
    """
    op.alter_column(
        'tokens',
        'project_id',
        nullable=False,
        existing_nullable=True,
    )
