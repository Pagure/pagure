"""Migrate SSH keys to the new format.

Revision ID: f16ab75e4d32
Revises: 0a8f99c161e2
Create Date: 2018-09-24 16:11:21.297620

"""

# revision identifiers, used by Alembic.
revision = "f16ab75e4d32"
down_revision = "0a8f99c161e2"

import datetime

from alembic import op
import sqlalchemy as sa

from pagure.lib import is_valid_ssh_key


def upgrade():
    """ Upgrade the database model for the way we store user's public ssh
    keys.

    For this we leverage the existing ``deploykeys`` table.
    It gets renamed to ``sshkeys``, we add the user_id foreign key as now
    ssh keys stored in this table can be linked to an user.
    Then we convert the existing ssh keys to this database model.
    Finally, we drop the ``public_ssh_key`` column from the ``users`` table.
    """
    users_table = sa.sql.table(
        "users",
        sa.sql.column("id", sa.Integer),
        sa.sql.column("public_ssh_key", sa.TEXT()),
    )
    sshkey_table = sa.sql.table(
        "sshkeys",
        sa.sql.column("id", sa.Integer),
        sa.sql.column("user_id", sa.Integer),
        sa.sql.column("public_ssh_key", sa.TEXT()),
        sa.sql.column("ssh_short_key", sa.TEXT()),
        sa.sql.column("ssh_search_key", sa.TEXT()),
        sa.sql.column("creator_user_id", sa.Integer),
        sa.sql.column("pushaccess", sa.Boolean),
        sa.sql.column("date_created", sa.DateTime),
    )

    op.rename_table("deploykeys", "sshkeys")

    op.add_column("sshkeys", sa.Column("user_id", sa.Integer(), nullable=True))
    op.create_index(
        op.f("ix_sshkeys_sshkeys_user_id"),
        "sshkeys",
        ["user_id"],
        unique=False,
    )
    op.create_foreign_key(
        op.f("sshkeys_user_id_fkey"),
        "sshkeys",
        "users",
        ["user_id"],
        ["id"],
        onupdate=u"CASCADE",
    )

    print("Convert existing ssh keys to the new format")

    seen = []
    conn = op.get_bind()
    for key in conn.execute(sshkey_table.select()):
        ssh_short_key = is_valid_ssh_key(key.public_ssh_key).strip()
        ssh_search_key = ssh_short_key.split(" ")[1]
        # There is no chance of dupes in the deploykeys alone
        seen.append(ssh_search_key)
        op.execute(
            sshkey_table.update()
            .where(sshkey_table.c.id == key.id)
            .values({
                "ssh_short_key": ssh_short_key,
                "ssh_search_key": ssh_search_key,
            })
        )

    data = []
    for user in conn.execute(users_table.select()):
        if not user.public_ssh_key:
            continue
        for key in user.public_ssh_key.split("\n"):
            if key in (None, False) or not key.strip():
                print("Skipping one key")
                continue
            ssh_short_key = is_valid_ssh_key(key).strip()
            ssh_search_key = ssh_short_key.split(" ")[1]
            if ssh_search_key in seen:
                print("Skipping previously seen key")
                continue
            seen.append(ssh_search_key)
            print("Key:    %s" % key)
            print("Short:  %s" % ssh_short_key)
            print("Search: %s" % ssh_search_key)
            tmp = {}
            tmp["user_id"] = user.id
            tmp["creator_user_id"] = user.id
            tmp["public_ssh_key"] = key
            tmp["ssh_search_key"] = ssh_search_key
            tmp["ssh_short_key"] = ssh_short_key
            tmp["pushaccess"] = True
            tmp['date_created'] = datetime.datetime.utcnow()
            data.append(tmp)

    op.bulk_insert(sshkey_table, data)

    op.drop_column("users", "public_ssh_key")


def downgrade():
    """ Downgrade the database model for the way we store user's public ssh
    keys.

    For this we bring back the keys present in the ``sshkeys`` table and
    put them back into the ``public_ssh_key`` column of the ``users`` table.
    """

    users_table = sa.sql.table(
        "users",
        sa.sql.column("id", sa.Integer),
        sa.sql.column("public_ssh_key", sa.TEXT()),
    )
    sshkey_table = sa.sql.table(
        "sshkeys",
        sa.sql.column("user_id", sa.Integer),
        sa.sql.column("public_ssh_key", sa.TEXT()),
        sa.sql.column("ssh_short_key", sa.TEXT()),
        sa.sql.column("ssh_search_key", sa.TEXT()),
        sa.sql.column("creator_user_id", sa.Integer),
        sa.sql.column("pushaccess", sa.Boolean),
        sa.sql.column("date_created", sa.DateTime),
    )

    op.add_column(
        "users", sa.Column("public_ssh_key", sa.TEXT(), nullable=True)
    )

    print("Convert existing ssh keys to the old format")

    conn = op.get_bind()
    data = []
    for key in conn.execute(sshkey_table.select()):
        if not key.user_id:
            continue
        user = [
            u
            for u in conn.execute(
                users_table.select().where(users_table.c.id == key.user_id)
            )
        ]
        user = user[0]
        ssh_key = ""
        if user.public_ssh_key:
            ssh_key = user.public_ssh_key + "\n"
        ssh_key += key.public_ssh_key

        op.execute(
            users_table.update()
            .where(users_table.c.id == key.user_id)
            .values({"public_ssh_key": ssh_key})
        )

    print("Remove the keys associated with users since we moved them")

    op.execute(
        sshkey_table.delete()
        .where(sshkey_table.c.user_id != None)
    )

    op.drop_constraint(
        op.f("sshkeys_user_id_fkey"), "sshkeys", type_="foreignkey"
    )
    op.drop_index(op.f("ix_sshkeys_sshkeys_user_id"), table_name="sshkeys")
    op.drop_column("sshkeys", "user_id")

    op.rename_table("sshkeys", "deploykeys")
