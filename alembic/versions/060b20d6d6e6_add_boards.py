"""Add boards

Revision ID: 060b20d6d6e6
Revises: d7589827abbb
Create Date: 2020-06-03 09:38:36.189205

"""

import datetime

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '060b20d6d6e6'
down_revision = 'd7589827abbb'


def upgrade():
    op.create_table(
        'boards',
        sa.Column('id', sa.INTEGER(), nullable=False, autoincrement=True),
        sa.Column('project_id', sa.INTEGER(), nullable=False),
        sa.Column('tag_id', sa.INTEGER(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('active', sa.BOOLEAN(), nullable=False, default=True),
        sa.Column('created', sa.DateTime(), nullable=False, default=datetime.datetime.utcnow),
        sa.Column('date_updated', sa.DateTime(), nullable=False,
            default=datetime.datetime.utcnow,
            onupdate=datetime.datetime.utcnow),
        sa.ForeignKeyConstraint(
            ['project_id'],
            [u'projects.id'],
            name=u'boards_project_id_fkey',
            onupdate=u'CASCADE',
            ondelete=u'CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['tag_id'],
            [u'tags_colored.id'],
            name=u'boards_tag_id_fkey',
            onupdate=u'CASCADE'
        ),
        sa.PrimaryKeyConstraint('id', name=u'boards_pkey'),
        sa.UniqueConstraint(
            "project_id", "name", name="boards_project_id_name_uix"
        ),
    )

    op.create_table(
        'board_statuses',
        sa.Column('id', sa.INTEGER(), nullable=False),
        sa.Column('board_id', sa.INTEGER(), nullable=False),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('rank', sa.INTEGER, nullable=False),
        sa.Column('default', sa.Boolean, nullable=False, default=False),
        sa.Column('bg_color', sa.String(32), nullable=False),
        sa.Column('close', sa.BOOLEAN(), nullable=False, default=False),
        sa.Column('close_status', sa.Text(), nullable=True),
        sa.Column('created', sa.DateTime(), nullable=False, default=datetime.datetime.utcnow),
        sa.ForeignKeyConstraint(
            ['board_id'],
            [u'boards.id'],
            name=u'board_statuses_board_id_fkey',
            onupdate=u'CASCADE',
            ondelete=u'CASCADE'
        ),
        sa.PrimaryKeyConstraint('id', name=u'board_statuses_pkey'),
        sa.UniqueConstraint(
            "board_id", "name", name="board_statuses_board_id_name_uix"
        ),
    )

    op.create_table(
        'boards_issues',
        sa.Column('issue_uid', sa.String(32), nullable=False),
        sa.Column('status_id', sa.INTEGER(), nullable=False),
        sa.Column('rank', sa.INTEGER(), nullable=False),
        sa.Column('created', sa.DateTime(), nullable=False, default=datetime.datetime.utcnow),
        sa.ForeignKeyConstraint(
            ['issue_uid'],
            [u'issues.uid'],
            name=u'boards_issues_issue_uid_fkey',
            onupdate=u'CASCADE',
            ondelete=u'CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['status_id'],
            [u'board_statuses.id'],
            name=u'boards_issues_status_id_fkey',
            onupdate=u'CASCADE',
            ondelete=u'CASCADE'
        ),
        sa.PrimaryKeyConstraint('status_id', "issue_uid", name=u'boards_issues_pkey'),
        sa.UniqueConstraint(
            "status_id", "issue_uid", name="boards_issues_status_id_issue_uid_uix"
        ),
    )


def downgrade():
    """ Remove the tables related to the boards feature. """
    op.drop_table('boards_issues')
    op.drop_table('board_statuses')
    op.drop_table('boards')
