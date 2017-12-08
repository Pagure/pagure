"""Fix pr project_from key

Revision ID: 61ac23e35f86
Revises: 47f5fab6f46a
Create Date: 2017-12-05 16:59:17.117199

"""

# revision identifiers, used by Alembic.
revision = '61ac23e35f86'
down_revision = '47f5fab6f46a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """ Alter the pull_requests table to update the foreign key to set null
    on delete.
    """

    op.drop_constraint(
        'pull_requests_project_id_from_fkey',
        'pull_requests',
        type_='foreignkey')
    op.create_foreign_key(
        name='pull_requests_project_id_from_fkey',
        source_table='pull_requests',
        referent_table='projects',
        local_cols=['project_id_from'],
        remote_cols=['id'],
        onupdate='cascade',
        ondelete='set null',
    )


def downgrade():
    """ Alter the pull_requests table to update the foreign key to cascade
    on delete.
    """

    op.drop_constraint(
        'pull_requests_project_id_from_fkey',
        'pull_requests',
        type_='foreignkey')
    op.create_foreign_key(
        name='pull_requests_project_id_from_fkey',
        source_table='pull_requests',
        referent_table='projects',
        local_cols=['project_id_from'],
        remote_cols=['id'],
        onupdate='cascade',
        ondelete='cascade',
    )
