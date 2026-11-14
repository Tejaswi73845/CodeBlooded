"""add workspaces

Revision ID: a1b2c3d4e5f6
Revises: 94a81cfc3baf
Create Date: 2026-11-14 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '94a81cfc3baf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add workspaces and scope evidence, reports and audit entries to them."""
    op.create_table(
        'workspaces',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=160), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_workspaces')),
        sa.UniqueConstraint('name', name=op.f('uq_workspaces_name')),
    )

    for table in ('evidence', 'reports', 'audit_logs'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.add_column(sa.Column('workspace_id', sa.Uuid(), nullable=True))
            batch_op.create_index(batch_op.f(f'ix_{table}_workspace_id'), ['workspace_id'], unique=False)
            batch_op.create_foreign_key(
                batch_op.f(f'fk_{table}_workspace_id_workspaces'),
                'workspaces',
                ['workspace_id'],
                ['id'],
                ondelete='SET NULL',
            )


def downgrade() -> None:
    """Remove workspace scoping."""
    for table in ('evidence', 'reports', 'audit_logs'):
        with op.batch_alter_table(table, schema=None) as batch_op:
            batch_op.drop_constraint(batch_op.f(f'fk_{table}_workspace_id_workspaces'), type_='foreignkey')
            batch_op.drop_index(batch_op.f(f'ix_{table}_workspace_id'))
            batch_op.drop_column('workspace_id')

    op.drop_table('workspaces')
