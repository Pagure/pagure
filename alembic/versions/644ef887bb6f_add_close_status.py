"""Add close status

Revision ID: 644ef887bb6f
Revises: 368fd931cf7f
Create Date: 2016-10-04 15:38:41.908679

"""

# revision identifiers, used by Alembic.
revision = '644ef887bb6f'
down_revision = '368fd931cf7f'

from alembic import op
import sqlalchemy as sa


try:
    from pagure.lib import model
except ImportError:
    import sys
    sys.path.insert(0, '.')
    from pagure.lib import model


def upgrade():
    ''' Add the column _close_status to the table projects.
    '''
    op.add_column(
        'projects',
        sa.Column('_close_status', sa.Text, nullable=True)
    )
    op.add_column(
        'issues',
        sa.Column('close_status', sa.Text, nullable=True)
    )

    engine = op.get_bind()
    Session = sa.orm.scoped_session(sa.orm.sessionmaker())
    Session.configure(bind=engine)
    session = Session()

    # Update all the existing projects
    statuses = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
    for project in session.query(model.Project).all():
        project.close_status = statuses
        session.add(project)
    session.commit()

    # Add the status 'Closed' for issues
    ticket_stat = model.StatusIssue(status='Closed')
    session.add(ticket_stat)
    session.commit()

    # Set the close_status for all the closed tickets
    op.execute('''UPDATE "issues" SET "close_status"=status where status != 'Open'; ''')

    # Mark all the tickets as closed
    op.execute('''UPDATE "issues" SET status='Closed' where status != 'Open';  ''')

    # Remove the old status
    op.execute('''DELETE FROM "status_issue" WHERE "status" NOT IN ('Open', 'Closed'); ''')


def downgrade():
    ''' Add the column _close_status to the table projects.
    '''
    engine = op.get_bind()
    Session = sa.orm.scoped_session(sa.orm.sessionmaker())
    Session.configure(bind=engine)
    session = Session()

    statuses = ['Invalid', 'Insufficient data', 'Fixed', 'Duplicate']
    for status in statuses:
        ticket_stat = model.StatusIssue(status=status)
        session.add(ticket_stat)
        session.commit()

    # Set the close_status for all the closed tickets
    op.execute('''UPDATE "issues" SET status=close_status where status != 'Open'; ''')

    # Remove the old status
    op.execute('''DELETE FROM "status_issue" WHERE status = 'Closed'; ''')

    op.drop_column('projects', '_close_status')
    op.drop_column('issues', 'close_status')
