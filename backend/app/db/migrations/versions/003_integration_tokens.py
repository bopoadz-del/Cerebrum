"""
Integration Tokens Migration

Creates the integration_tokens table for storing OAuth tokens.

Revision ID: 003
Revises: 002
Create Date: 2024-02-18 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create integration_tokens table."""
    op.create_table(
        'integration_tokens',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_id', sa.String(64), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service', sa.String(50), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('token_uri', sa.String(255), nullable=False),
        sa.Column('client_id', sa.String(255), nullable=True),
        sa.Column('client_secret', sa.String(255), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=False),
        sa.Column('expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rotation_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    
    # Create indexes
    op.create_index(
        'ix_integration_tokens_token_id',
        'integration_tokens',
        ['token_id'],
        unique=True
    )
    op.create_index(
        'ix_integration_tokens_user_id',
        'integration_tokens',
        ['user_id'],
        unique=False
    )
    op.create_index(
        'ix_integration_tokens_service',
        'integration_tokens',
        ['service'],
        unique=False
    )
    op.create_index(
        'ix_integration_tokens_user_service',
        'integration_tokens',
        ['user_id', 'service'],
        unique=False
    )
    
    # Create foreign key
    op.create_foreign_key(
        'fk_integration_tokens_user',
        'integration_tokens',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Drop integration_tokens table."""
    op.drop_index('ix_integration_tokens_user_service', table_name='integration_tokens')
    op.drop_index('ix_integration_tokens_service', table_name='integration_tokens')
    op.drop_index('ix_integration_tokens_user_id', table_name='integration_tokens')
    op.drop_index('ix_integration_tokens_token_id', table_name='integration_tokens')
    op.drop_table('integration_tokens')
