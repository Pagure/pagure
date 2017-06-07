"""Add modify_project ACL

Revision ID: 27a79ff0fb41
Revises: d4d2c5aa8a0
Create Date: 2017-06-01 14:20:06.769321

"""

# revision identifiers, used by Alembic.
revision = '27a79ff0fb41'
down_revision = '5179e99d35a5'

from alembic import op
import sqlalchemy as sa

try:
    from pagure.lib import model
except ImportError:
    import sys
    sys.path.insert(0, '.')
    from pagure.lib import model


def get_session():
    engine = op.get_bind()
    Session = sa.orm.scoped_session(sa.orm.sessionmaker())
    Session.configure(bind=engine)
    return Session()


def upgrade():
    session = get_session()
    modify_project_acl = model.ACL()
    modify_project_acl.name = 'modify_project'
    modify_project_acl.description = 'Modify a project'
    session.add(modify_project_acl)
    session.commit()


def downgrade():
    session = get_session()
    modify_project_acl = session.query(model.ACL).filter_by(
        name='modify_project').one()
    session.delete(modify_project_acl)
    session.commit()
