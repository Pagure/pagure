"""access_id in user_projects

Revision ID: 987edda096f5
Revises: 8a3b10926153
Create Date: 2016-07-05 18:21:14.771273

"""

# revision identifiers, used by Alembic.
revision = '987edda096f5'
down_revision = '8a3b10926153'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column

acl = table (
    'access_levels',
    column('access', sa.String(255))
)

def upgrade():
    ''' Add a foreign key in user_projects and projects_groups
    table for access_levels
    '''

    # To allow N + 2 migrations easier
    # without going through N + 1
    # Make sure, we have all the tables
    op.create_table(
        'access_levels',
        sa.Column('access', sa.String(255), primary_key=True)
    )
    op.bulk_insert(
        acl,
        [
            {'access': 'ticket'},
            {'access': 'commit'},
            {'access': 'admin'},
        ],
    )
    op.add_column(
        'user_projects',
        sa.Column(
            'access',
            sa.String(255),
            sa.ForeignKey(
                'access_levels.access',
                onupdate='CASCADE',
                ondelete='CASCADE',
            ),
            nullable=True,
        ),
    )
    op.execute('UPDATE "user_projects" SET access=\'admin\'')
    op.alter_column(
        'user_projects',
        'access',
        nullable=False,
        existing_nullable=True,
    )

    # for groups
    op.add_column(
        'projects_groups',
        sa.Column(
            'access',
            sa.String(255),
            sa.ForeignKey(
                'access_levels.access',
                onupdate='CASCADE',
                ondelete='CASCADE',
            ),
            nullable=True,
        ),
    )
    op.execute('UPDATE "projects_groups" SET access=\'admin\'')
    op.alter_column(
        'projects_groups',
        'access',
        nullable=False,
        existing_nullable=True,
    )

    # alter the constraints
    op.drop_constraint('user_projects_project_id_fkey', 'user_projects')
    op.create_unique_constraint(
            None,
            'user_projects',
            ["project_id", "user_id", "access"]
    )

    op.drop_constraint('projects_groups_pkey', 'projects_groups')
    op.create_primary_key(
            None,
            'projects_groups',
            ['project_id', 'group_id', 'access'],
    )


def downgrade():
    ''' Remove column access_id from user_projects and projects_groups '''

    # this removes the current constraints as well.
    op.drop_column('user_projects', 'access')
    op.drop_column('projects_groups', 'access')

    # recreate the previous constraints
    op.create_unique_constraint(
            None,
            'user_projects',
            ['project_id', 'user_id'],
    )
    op.create_primary_key(
            None,
            'projects_groups',
            ['project_id', 'group_id'],
    )
    op.drop_table('access_levels')
