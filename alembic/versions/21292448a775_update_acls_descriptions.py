"""Update ACLs descriptions

Revision ID: 21292448a775
Revises: 3237fc64b306
Create Date: 2017-10-12 16:55:05.066340

"""

# revision identifiers, used by Alembic.
revision = '21292448a775'
down_revision = '3237fc64b306'

from alembic import op
import sqlalchemy as sa

ACLS = {
    'create_project': 'Create a new project',
    'fork_project': 'Fork a project',
    'issue_assign': 'Assign issue to someone',
    'issue_create': 'Create a new ticket',
    'issue_change_status': 'Change the status of a ticket',
    'issue_comment': 'Comment on a ticket',
    'pull_request_close': 'Close a pull-request',
    'pull_request_comment': 'Comment on a pull-request',
    'pull_request_flag': 'Flag a pull-request',
    'pull_request_merge': 'Merge a pull-request',
    'issue_subscribe': 'Subscribe the user with this token to an issue',
    'issue_update': 'Update an issue, status, comments, custom fields...',
    'issue_update_custom_fields': 'Update the custom fields of an issue',
    'issue_update_milestone': 'Update the milestone of an issue',
    'modify_project': 'Modify an existing project',
    'generate_acls_project': 'Generate the Gitolite ACLs on a project'
}

def upgrade():
    """ Update the ACLs description stored in the database to be more
    generic.
    """
    for acl in ACLS:
        op.execute(
            "UPDATE acls SET description='%s' WHERE name='%s';" % (
                ACLS[acl], acl)
        )


def downgrade():
    """ There isn't really anything to back out, so just keep going. """
    pass
