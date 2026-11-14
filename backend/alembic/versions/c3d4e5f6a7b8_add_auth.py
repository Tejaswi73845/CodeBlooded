"""add authentication

Revision ID: c3d4e5f6a7b8
Revises: a1b2c3d4e5f6
Create Date: 2026-11-14 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add password credentials and bearer-token sessions."""
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('password_hash', sa.String(length=256), nullable=True))
        batch_op.add_column(sa.Column('is_active', sa.Boolean(), nullable=True))

    op.execute("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")

    op.create_table(
        'auth_sessions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'], ['users.id'],
            name=op.f('fk_auth_sessions_user_id_users'), ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_auth_sessions')),
        sa.UniqueConstraint('token_hash', name=op.f('uq_auth_sessions_token_hash')),
    )
    with op.batch_alter_table('auth_sessions', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_auth_sessions_token_hash'), ['token_hash'], unique=True)
        batch_op.create_index(batch_op.f('ix_auth_sessions_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    """Remove authentication."""
    with op.batch_alter_table('auth_sessions', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_auth_sessions_user_id'))
        batch_op.drop_index(batch_op.f('ix_auth_sessions_token_hash'))

    op.drop_table('auth_sessions')

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_column('is_active')
        batch_op.drop_column('password_hash')
