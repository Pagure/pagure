"""Add the pr_to_issue table

Revision ID: 369deb8c8b63
Revises: eab41ce5f92a
Create Date: 2018-03-12 11:38:00.955252

"""

# revision identifiers, used by Alembic.
revision = '369deb8c8b63'
down_revision = 'eab41ce5f92a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Create the pr_to_issue table. '''

    op.create_table(
        'pr_to_issue',
        sa.Column(
            'pull_request_uid',
            sa.String(32),
            sa.ForeignKey(
                'pull_requests.uid', ondelete='CASCADE', onupdate='CASCADE',
            ),
            primary_key=True),
        sa.Column(
            'issue_uid',
            sa.String(32),
            sa.ForeignKey(
                'issues.uid', ondelete='CASCADE', onupdate='CASCADE',
            ),
            primary_key=True)
    )


def downgrade():
    ''' Drop the pr_to_issue table. '''

    op.drop_table('pr_to_issue')
