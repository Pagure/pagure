"""versioning_passwords

Revision ID: 1b6d7dc5600a
Revises: 3b441ef4e928
Create Date: 2016-01-13 07:57:23.465676

"""

# revision identifiers, used by Alembic.
revision = '1b6d7dc5600a'
down_revision = '3b441ef4e928'

from alembic import op
import sqlalchemy as sa
import sqlalchemy.orm
from pagure.lib import model


def upgrade():
    engine = op.get_bind()
    Session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker())
    Session.configure(bind=engine)
    session = Session()
    for user in session.query(model.User).filter(
            model.User.password != None).all():
        user.password = '$1$%s' % user.password
        session.add(user)
    session.commit()


def downgrade():
    raise ValueError("Password can not be downgraded")
