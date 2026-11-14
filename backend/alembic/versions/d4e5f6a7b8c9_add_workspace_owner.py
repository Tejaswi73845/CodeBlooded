"""add workspace owner

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-11-14 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Scope workspaces to a user so accounts cannot see each other's data."""
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner_id', sa.Uuid(), nullable=True))
        batch_op.create_index(batch_op.f('ix_workspaces_owner_id'), ['owner_id'], unique=False)
        batch_op.create_foreign_key(
            batch_op.f('fk_workspaces_owner_id_users'),
            'users',
            ['owner_id'],
            ['id'],
            ondelete='CASCADE',
        )
        batch_op.drop_constraint('uq_workspaces_name', type_='unique')
        batch_op.create_unique_constraint('uq_workspaces_owner_name', ['owner_id', 'name'])


def downgrade() -> None:
    """Remove workspace ownership."""
    with op.batch_alter_table('workspaces', schema=None) as batch_op:
        batch_op.drop_constraint('uq_workspaces_owner_name', type_='unique')
        batch_op.create_unique_constraint('uq_workspaces_name', ['name'])
        batch_op.drop_constraint(batch_op.f('fk_workspaces_owner_id_users'), type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_workspaces_owner_id'))
        batch_op.drop_column('owner_id')
