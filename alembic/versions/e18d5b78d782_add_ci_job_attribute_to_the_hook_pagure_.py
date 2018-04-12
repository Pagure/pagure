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

    con = op.get_bind()
    results = con.execute('SELECT id, ci_url FROM hook_pagure_ci')

    for id, url in results:
        ci_job = url.split('/job/', 1)[1].split('/', 1)[0]
        ci_url = url.split('/job/')[0]
        op.execute(
            "UPDATE hook_pagure_ci SET ci_job='{}' WHERE id = '{}'".format(ci_job, id))
        op.execute(
            "UPDATE hook_pagure_ci SET ci_url='{}' WHERE id = '{}'".format(ci_url, id))

    op.alter_column(
        'hook_pagure_ci', 'ci_job',
        nullable=False, existing_nullable=True)


def downgrade():
    ''' Revert the ci_job column added'''

    con = op.get_bind()
    results = con.execute('SELECT id, ci_url, ci_job FROM hook_pagure_ci')

    for id, url, job in results:
        ci_url = url + '/job/' + job + '/'
        op.execute(
            "UPDATE hook_pagure_ci SET ci_url='{}' WHERE id = '{}'".format(ci_url, id))

    op.drop_column('hook_pagure_ci', 'ci_job')
