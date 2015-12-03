"""Issue editors

Revision ID: 3b441ef4e928
Revises: 15ea3c2cf83d
Create Date: 2015-12-03 12:34:28.316699

"""

# revision identifiers, used by Alembic.
revision = '3b441ef4e928'
down_revision = '15ea3c2cf83d'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ''' Add the columns editor_id and edited_on to the table issue_comments.
    '''

    op.add_column(
        'issue_comments',
        sa.Column(
            'editor_id',
            sa.Integer,
            sa.ForeignKey('users.id', onupdate='CASCADE'),
            nullable=True)
    )

    op.add_column(
        'issue_comments',
        sa.Column(
            'edited_on',
            sa.DateTime,
            nullable=True)
    )


def downgrade():
    ''' Remove the columns editor_id and edited_on from the table
    issue_comments.
    '''
    op.drop_column('issue_comments', 'editor_id')
    op.drop_column('issue_comments', 'edited_on')
