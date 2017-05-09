"""Add granularity to watching repos

Revision ID: d4d2c5aa8a0
Revises: 4255158a6913
Create Date: 2017-04-28 14:39:09.746953

"""

# revision identifiers, used by Alembic.
revision = 'd4d2c5aa8a0'
down_revision = '4255158a6913'

from alembic import op
import sqlalchemy as sa

# A helper table that is a hybrid with both states. This is used for data
# migrations later on.
watcher_helper = sa.Table(
    'watchers',
    sa.MetaData(),
    sa.Column('id', sa.Integer, primary_key=True),
    sa.Column('watch_issues', sa.Boolean),
    sa.Column('watch_commits', sa.Boolean),
    sa.Column('watch', sa.Boolean),
)


def upgrade():
    op.add_column('watchers', sa.Column('watch_commits', sa.Boolean(),
                                        nullable=True))
    op.add_column('watchers', sa.Column('watch_issues', sa.Boolean(),
                                        nullable=True))
    # This section is to update the `watch_issues` and `watch_commits` columns
    # with the value of `watch`
    connection = op.get_bind()
    for watcher in connection.execute(watcher_helper.select()):
        connection.execute(
            watcher_helper.update().where(
                watcher_helper.c.id == watcher.id
            ).values(
                watch_issues=watcher.watch,
                watch_commits=False
            )
        )

    with op.batch_alter_table('watchers') as b:
        # Set nullable to False now that we've set values
        b.alter_column('watch_issues', nullable=False)
        b.alter_column('watch_commits', nullable=False)
        # Remove the watch column
        b.drop_column('watch')


def downgrade():
    op.add_column('watchers', sa.Column('watch', sa.BOOLEAN(), nullable=True))

    # This section is to update the `watch` column with the value of
    # `watch_issues`
    connection = op.get_bind()
    for watcher in connection.execute(watcher_helper.select()):
        connection.execute(
            watcher_helper.update().where(
                watcher_helper.c.id == watcher.id
            ).values(
                watch=watcher.watch_issues
            )
        )

    with op.batch_alter_table('watchers') as b:
        # Set nullable to False now that we've set values
        b.alter_column('watch', nullable=False)
        # Drop the added columns
        b.drop_column('watch_issues')
        b.drop_column('watch_commits')
