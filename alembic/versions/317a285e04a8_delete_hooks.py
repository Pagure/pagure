"""Delete hooks

Revision ID: 317a285e04a8
Revises: 2aa7b3958bc5
Create Date: 2016-05-30 11:28:48.512577

"""

# revision identifiers, used by Alembic.
revision = '317a285e04a8'
down_revision = '2aa7b3958bc5'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """ Alter the hooks table to update the foreign key to cascade on delete.
    """

    for table in [
            'hook_fedmsg', 'hook_irc', 'hook_mail',
            'hook_pagure_force_commit', 'hook_pagure', 'hook_pagure_requests',
            'hook_pagure_tickets', 'hook_pagure_unsigned_commit', 'hook_rtd',
            ]:
        op.drop_constraint(
            '%s_project_id_fkey' % table,
            table,
            type_='foreignkey')
        op. create_foreign_key(
            name='%s_project_id_fkey' % table,
            source_table=table,
            referent_table='projects',
            local_cols=['project_id'],
            remote_cols=['id'],
            onupdate='cascade',
            ondelete='cascade',
        )

    op.drop_constraint(
        'projects_groups_project_id_fkey',
        'projects_groups',
        type_='foreignkey')
    op. create_foreign_key(
        name='projects_groups_project_id_fkey',
        source_table='projects_groups',
        referent_table='projects',
        local_cols=['project_id'],
        remote_cols=['id'],
        onupdate='cascade',
        ondelete='cascade',
    )



def downgrade():
    """ Alter the hooks table to update the foreign key to undo the cascade
    on delete.
    """
