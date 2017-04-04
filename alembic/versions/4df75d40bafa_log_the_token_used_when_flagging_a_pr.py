"""Log the token used when flagging a PR

Revision ID: 4df75d40bafa
Revises: 3ffec872dfdf
Create Date: 2017-04-04 16:26:58.352213

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '4df75d40bafa'
down_revision = '3ffec872dfdf'


def upgrade():
    ''' Add the foreign key token_id to the table pull_request_flags.
    '''
    op.add_column(
        'pull_request_flags',
        sa.Column(
            'token_id',
            sa.String(64),
            sa.ForeignKey('tokens.id'),
            nullable=True
        )
    )

def downgrade():
    ''' Remove the column token_id from the table pull_request_flags.
    '''
    op.drop_column('pull_request_flags', 'token_id')
