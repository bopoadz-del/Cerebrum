"""Ensure google_drive_tokens table exists

Revision ID: 006
Revises: 005
Create Date: 2026-02-20 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Check if table exists
    conn = op.get_bind()
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_name = 'google_drive_tokens'
        )
    """))
    table_exists = result.scalar()
    
    if not table_exists:
        print("Creating google_drive_tokens table...")
        # Create table
        op.create_table(
            'google_drive_tokens',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column('access_token', sa.Text(), nullable=False),
            sa.Column('refresh_token', sa.Text(), nullable=False),
            sa.Column('token_type', sa.String(50), nullable=True),
            sa.Column('expires_at', sa.DateTime(), nullable=False),
            sa.Column('google_email', sa.String(255), nullable=True),
            sa.Column('is_active', sa.Boolean(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=False),
            sa.Column('last_used_at', sa.DateTime(), nullable=True),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id')
        )
        print("Table created successfully")
    else:
        print("google_drive_tokens table already exists")

def downgrade() -> None:
    op.drop_table('google_drive_tokens')
