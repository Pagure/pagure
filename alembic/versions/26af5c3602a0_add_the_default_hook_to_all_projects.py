"""Add the default hook to all projects

Revision ID: 26af5c3602a0
Revises: 644ef887bb6f
Create Date: 2016-10-08 12:14:31.155018

"""

# revision identifiers, used by Alembic.
revision = '26af5c3602a0'
down_revision = '644ef887bb6f'

from alembic import op
import sqlalchemy as sa


try:
    import pagure.lib.plugins
    from pagure.lib import model
except ImportError:
    import sys
    sys.path.insert(0, '.')
    import pagure.lib.plugins
    from pagure.lib import model



def upgrade():
    ''' Add the default hook to all existing projects.
    '''

    engine = op.get_bind()
    Session = sa.orm.scoped_session(sa.orm.sessionmaker())
    Session.configure(bind=engine)
    session = Session()

    # Update all the existing projects
    for project in session.query(model.Project).all():
        # Install the default hook
        plugin = pagure.lib.plugins.get_plugin('default')
        dbobj = plugin.db_object()
        dbobj.active = True
        dbobj.project_id = project.id
        session.add(dbobj)
        session.flush()
        plugin.set_up(project)
        plugin.install(project, dbobj)
        # Save the change
        session.commit()


def downgrade():
    engine = op.get_bind()
    Session = sa.orm.scoped_session(sa.orm.sessionmaker())
    Session.configure(bind=engine)
    session = Session()

    # Update all the existing projects
    for project in session.query(model.Project).all():
        # Install the default hook
        plugin = pagure.lib.plugins.get_plugin('default')
        dbobj = plugin.db_object()
        dbobj.active = False
        dbobj.project_id = project.id
        session.add(dbobj)
        session.flush()
        plugin.remove(project, dbobj)

        # Save the change
        session.commit()
