"""Table for no new branches hook

Revision ID: 131ad2dc5bbd
Revises: 7f31a9fad89f
Create Date: 2018-05-11 10:52:05.088806

"""

# revision identifiers, used by Alembic.
revision = '131ad2dc5bbd'
down_revision = '7f31a9fad89f'

from alembic import op
import sqlalchemy as sa


def upgrade():
    """ Create table for PagureNoNewBranchesHook. """
    op.create_table(
        'hook_pagure_no_new_branches',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('active', sa.BOOLEAN(), nullable=False),
        sa.CheckConstraint(u'active IN (0, 1)'),
        sa.ForeignKeyConstraint(
            ['project_id'],
            [u'projects.id'],
            name=u'hook_pagure_no_new_branches_project_id_fkey',
            onupdate=u'CASCADE',
            ondelete=u'CASCADE'
        ),
        sa.PrimaryKeyConstraint('id', name=u'hook_pagure_no_new_branches_pkey')
    )


def downgrade():
    """ Remove table for PagureNoNewBranchesHook. """
    op.drop_table('hook_pagure_no_new_branches')
