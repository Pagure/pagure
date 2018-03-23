"""add active_commit attribute to the hook_pagure_ci table

Revision ID: eab41ce5f92a
Revises: e18d5b78d782
Create Date: 2018-03-21 13:37:24.117434

"""

# revision identifiers, used by Alembic.
revision = 'eab41ce5f92a'
down_revision = 'e18d5b78d782'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add active_commit column to hook_pagure_ci table'''
    op.add_column(
        'hook_pagure_ci',
        sa.Column('active_commit', sa.Boolean, nullable=True, default=False)
    )
    op.add_column(
        'hook_pagure_ci',
        sa.Column('active_pr', sa.Boolean, nullable=True, default=False)
    )
    op.execute('UPDATE hook_pagure_ci SET active_pr=active')
    op.execute('UPDATE hook_pagure_ci SET active_commit=False')
    op.alter_column(
        'hook_pagure_ci', 'active_pr',
        nullable=False, existing_nullable=True)
    op.alter_column(
        'hook_pagure_ci', 'active_commit',
        nullable=False, existing_nullable=True)


def downgrade():
    ''' Revert the active_commit column added'''

    op.execute('UPDATE hook_pagure_ci SET active=active_pr')
    op.drop_column('hook_pagure_ci', 'active_commit')
    op.drop_column('hook_pagure_ci', 'active_pr')
