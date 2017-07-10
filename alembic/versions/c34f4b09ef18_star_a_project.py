"""star_a_project

Revision ID: c34f4b09ef18
Revises: 27a79ff0fb41
Create Date: 2017-07-07 00:08:18.257075

"""

# revision identifiers, used by Alembic.
revision = 'c34f4b09ef18'
down_revision = '27a79ff0fb41'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add a new table to store data about who starred which project '''
    op.create_table(
        'stargazers',
        sa.MetaData(),
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column(
            'project_id',
            sa.Integer,
            sa.ForeignKey(
                'projects.id', onupdate='CASCADE', ondelete='CASCADE'),
            nullable=False,
            index=True,
        ),
        sa.Column(
            'user_id',
            sa.Integer,
            sa.ForeignKey('users.id', onupdate='CASCADE', ondelete='CASCADE'),
            nullable=False,
        )
    )

    op.create_unique_constraint(
        constraint_name='stargazers_project_id_user_id_key',
        table_name='stargazers',
        columns=['project_id', 'user_id']
    )


def downgrade():
    ''' Remove the stargazers table from the database '''
    op.drop_constraint(
        constraint_name='stargazers_project_id_user_id_key',
        table_name='stargazers'
    )
    op.drop_table('stargazers')
