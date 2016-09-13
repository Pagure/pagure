"""Add namespace to project

Revision ID: 350efb3f6baf
Revises: 1640c7d75e5f
Create Date: 2016-08-30 22:02:07.645138

"""

# revision identifiers, used by Alembic.
revision = '350efb3f6baf'
down_revision = '1640c7d75e5f'

from alembic import op
import sqlalchemy as sa

try:
    from pagure.lib import model
except ImportError:
    import sys
    sys.path.insert(0, '.')
    from pagure.lib import model


def upgrade():
    ''' Add the column namespace to the table projects.
    '''
    op.add_column(
        'projects',
        sa.Column('namespace', sa.String(255), nullable=True, index=True)
    )

    # Update all the existing projects
    engine = op.get_bind()
    Session = sa.orm.scoped_session(sa.orm.sessionmaker())
    Session.configure(bind=engine)
    session = Session()
    for project in session.query(model.Project).filter(
            model.Project.name.ilike('%/%')).all():
        nspace, name = project.name.split('/', 1)
        project.name = name
        project.namespace = nspace
        session.add(project)
    session.commit()


def downgrade():
    ''' Remove the column namespace from the table projects.
    '''
    # Update all the existing projects
    engine = op.get_bind()
    Session = sa.orm.scoped_session(sa.orm.sessionmaker())
    Session.configure(bind=engine)
    session = Session()
    for project in session.query(model.Project).filter(
            model.Project.namespace != None).all():
        if project.namespace.strip():
            project.name = '%s/%s' % (project.namespace, project.name)
            session.add(project)
    session.commit()

    op.drop_column('projects', 'namespace')
