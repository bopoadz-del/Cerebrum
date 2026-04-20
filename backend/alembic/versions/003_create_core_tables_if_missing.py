"""create core tables if missing

Revision ID: 003
Revises: 002
Create Date: 2026-04-20

Migration 001 was a no-op placeholder that got stamped before the real
table definitions were added. This migration creates any missing core
tables using IF NOT EXISTS so it is safe to run on both fresh and
existing databases.
"""
revision = '003'
down_revision = '002'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector


def _table_exists(conn, table_name: str) -> bool:
    inspector = Inspector.from_engine(conn)
    return table_name in inspector.get_table_names()


def upgrade():
    conn = op.get_bind()

    # ── roles ────────────────────────────────────────────────────────────────
    if not _table_exists(conn, 'roles'):
        op.create_table(
            'roles',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('name', sa.String(50), unique=True, nullable=False),
            sa.Column('description', sa.Text(), nullable=True),
            sa.Column('permissions', postgresql.JSONB(), nullable=False, server_default='[]'),
            sa.Column('is_system', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )

    # ── users ────────────────────────────────────────────────────────────────
    if not _table_exists(conn, 'users'):
        op.create_table(
            'users',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('email', sa.String(255), unique=True, nullable=False),
            sa.Column('hashed_password', sa.String(255), nullable=False),
            sa.Column('full_name', sa.String(255), nullable=True),
            sa.Column('avatar_url', sa.String(512), nullable=True),
            sa.Column('role', sa.String(50), nullable=False, server_default='user'),
            sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('is_verified', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('mfa_enabled', sa.Boolean(), nullable=False, server_default='false'),
            sa.Column('mfa_secret', sa.String(255), nullable=True),
            sa.Column('mfa_backup_codes', postgresql.JSONB(), nullable=True),
            sa.Column('mfa_verified_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_login_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('last_login_ip', sa.String(45), nullable=True),
            sa.Column('failed_login_attempts', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('locked_until', sa.DateTime(timezone=True), nullable=True),
            sa.Column('password_changed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('preferences', postgresql.JSONB(), nullable=True),
            sa.Column('timezone', sa.String(50), nullable=False, server_default='UTC'),
            sa.Column('language', sa.String(10), nullable=False, server_default='en'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index('ix_users_email', 'users', ['email'])
        op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
        op.create_index('ix_users_role', 'users', ['role'])
        op.create_index('ix_users_deleted_at', 'users', ['deleted_at'])

    # ── user_roles ───────────────────────────────────────────────────────────
    if not _table_exists(conn, 'user_roles'):
        op.create_table(
            'user_roles',
            sa.Column('user_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('role_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
            sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('assigned_by', postgresql.UUID(as_uuid=True), nullable=True),
        )

    # ── api_keys ─────────────────────────────────────────────────────────────
    if not _table_exists(conn, 'api_keys'):
        op.create_table(
            'api_keys',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True),
                      sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('name', sa.String(100), nullable=False),
            sa.Column('key_hash', sa.String(255), nullable=False),
            sa.Column('key_prefix', sa.String(8), nullable=False),
            sa.Column('scopes', postgresql.JSONB(), nullable=False, server_default='[]'),
            sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        )

    # ── conversation_sessions ────────────────────────────────────────────────
    if not _table_exists(conn, 'conversation_sessions'):
        op.create_table(
            'conversation_sessions',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('session_token', sa.String(64), unique=True, nullable=False),
            sa.Column('title', sa.String(255), nullable=True),
            sa.Column('capacity_percent', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
            sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index('ix_conversation_sessions_user_id', 'conversation_sessions', ['user_id'])
        op.create_index('ix_conversation_sessions_token', 'conversation_sessions', ['session_token'])


def downgrade():
    conn = op.get_bind()
    for table in ['conversation_sessions', 'api_keys', 'user_roles', 'users', 'roles']:
        if _table_exists(conn, table):
            op.drop_table(table)
