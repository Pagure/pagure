"""Add ci_username and ci_password to hook_pagure_ci

Revision ID: 5a2327825b9a
Revises: 1a510f2216c0
Create Date: 2019-03-19 10:06:25.292081

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5a2327825b9a'
down_revision = '1a510f2216c0'


def upgrade():
    ''' Add the ci_username and ci_password fields to hook_pagure_ci'''
    op.add_column(
        'hook_pagure_ci',
        sa.Column('ci_username', sa.String(255), nullable=True, unique=False)
    )
    op.add_column(
        'hook_pagure_ci',
        sa.Column('ci_password', sa.String(255), nullable=True, unique=False)
    )


def downgrade():
    ''' Drop the ci_username and ci_password fields from hook_pagure_ci'''
    op.drop_column('hook_pagure_ci', 'ci_username')
    op.drop_column('hook_pagure_ci', 'ci_password')
