"""Add ci_job attribute to the hook_pagure_ci table

Revision ID: e18d5b78d782
Revises: 22fb5256f555
Create Date: 2018-03-16 11:51:04.613420

"""

# revision identifiers, used by Alembic.
revision = 'e18d5b78d782'
down_revision = '22fb5256f555'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add ci_job column to projects table'''
    op.add_column(
        'hook_pagure_ci',
        sa.Column('ci_job', sa.String(255), nullable=True, unique=False)
    )


def downgrade():
    ''' Revert the ci_job column added'''
    op.drop_column('hook_pagure_ci', 'ci_job')
