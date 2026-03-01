"""Add account_email to integration_tokens

Revision ID: 007
Revises: cf3ec9cca1a4
Create Date: 2026-03-01 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '007'
down_revision = 'cf3ec9cca1a4'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add account_email column if not exists (for idempotency)
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('integration_tokens')]
    
    if 'account_email' not in columns:
        op.add_column('integration_tokens', sa.Column('account_email', sa.String(255), nullable=True))
    if 'account_name' not in columns:
        op.add_column('integration_tokens', sa.Column('account_name', sa.String(255), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [col['name'] for col in inspector.get_columns('integration_tokens')]
    
    if 'account_email' in columns:
        op.drop_column('integration_tokens', 'account_email')
    if 'account_name' in columns:
        op.drop_column('integration_tokens', 'account_name')
