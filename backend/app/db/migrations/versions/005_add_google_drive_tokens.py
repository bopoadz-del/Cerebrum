"""Add google_drive_tokens table

Revision ID: 005
Revises: 004
Create Date: 2025-02-20 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func

# revision identifiers, used by Alembic.
revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'google_drive_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('token_type', sa.String(length=50), nullable=True),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('google_user_id', sa.String(length=255), nullable=True),
        sa.Column('google_email', sa.String(length=255), nullable=True),
        sa.Column('scopes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('revoked_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(op.f('ix_google_drive_tokens_id'), 'google_drive_tokens', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_google_drive_tokens_id'), table_name='google_drive_tokens')
    op.drop_table('google_drive_tokens')
