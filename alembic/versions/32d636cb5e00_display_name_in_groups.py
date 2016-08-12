"""display_name_in_groups

Revision ID: 32d636cb5e00
Revises: 43df5e588a87
Create Date: 2016-08-13 02:54:27.199948

"""

# revision identifiers, used by Alembic.
revision = '32d636cb5e00'
down_revision = '43df5e588a87'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add attributes display name and description in PagureGroup '''
    op.add_column(
        'pagure_group',
        sa.Column(
            'display_name',
            sa.String(255),
            nullable=True,
            unique=True,
        )
    )

    op.execute('''UPDATE "pagure_group" SET display_name=group_name; ''')

    op.alter_column(
        'pagure_group',
        column_name='display_name',
        nullable=False,
        existing_nullable=True
        )

    op.add_column(
        'pagure_group',
        sa.Column(
            'description',
            sa.String(255),
            nullable=True,
        )
    )


def downgrade():
    ''' Remove attributes display name and description in PagureGroup '''

    op.drop_column('pagure_group', 'display_name')
    op.drop_column('pagure_group', 'description')

