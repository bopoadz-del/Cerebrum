"""
Conversation Sessions Migration

Creates the conversation_sessions table for long-session mode with capacity tracking.

Revision ID: 002
Revises: 001
Create Date: 2024-01-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create conversation_sessions table."""
    op.create_table(
        'conversation_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('session_token', sa.String(64), nullable=False),
        sa.Column('title', sa.String(255), nullable=True),
        sa.Column('capacity_percent', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('message_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('token_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Indexes for efficient lookups
    op.create_index(
        'idx_conversation_sessions_token',
        'conversation_sessions',
        ['session_token'],
        unique=True,
    )
    op.create_index(
        'idx_conversation_sessions_user_id',
        'conversation_sessions',
        ['user_id'],
    )
    op.create_index(
        'idx_conversation_sessions_user_active',
        'conversation_sessions',
        ['user_id'],
        postgresql_where=sa.text('is_active = true'),
    )
    op.create_index(
        'idx_conversation_sessions_expires_at',
        'conversation_sessions',
        ['expires_at'],
    )
    op.create_index(
        'idx_conversation_sessions_last_activity',
        'conversation_sessions',
        [sa.text('last_activity_at DESC')],
    )


def downgrade() -> None:
    """Drop conversation_sessions table."""
    op.drop_index('idx_conversation_sessions_last_activity', table_name='conversation_sessions')
    op.drop_index('idx_conversation_sessions_expires_at', table_name='conversation_sessions')
    op.drop_index('idx_conversation_sessions_user_active', table_name='conversation_sessions')
    op.drop_index('idx_conversation_sessions_user_id', table_name='conversation_sessions')
    op.drop_index('idx_conversation_sessions_token', table_name='conversation_sessions')
    op.drop_table('conversation_sessions')
