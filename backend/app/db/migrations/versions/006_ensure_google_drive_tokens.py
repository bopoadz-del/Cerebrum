"""Ensure google_drive_tokens table exists

Revision ID: 006
Revises: 005
Create Date: 2026-02-20 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create table only if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS google_drive_tokens (
            id SERIAL PRIMARY KEY,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            access_token TEXT NOT NULL,
            refresh_token TEXT NOT NULL,
            token_type VARCHAR(50) DEFAULT 'Bearer',
            expires_at TIMESTAMP NOT NULL,
            google_email VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            last_used_at TIMESTAMP,
            UNIQUE (user_id)
        )
    """)
    
    # Create indexes
    op.execute("CREATE INDEX IF NOT EXISTS idx_google_drive_tokens_user_id ON google_drive_tokens(user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_google_drive_tokens_is_active ON google_drive_tokens(is_active)")

def downgrade() -> None:
    op.drop_table('google_drive_tokens')
