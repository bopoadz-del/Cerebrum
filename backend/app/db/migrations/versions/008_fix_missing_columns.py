"""Fix missing account columns

Revision ID: 008
Revises: 007
Create Date: 2024-03-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = '008'
down_revision = '007'

def upgrade():
    # Add columns if they don't exist
    inspector = inspect(op.get_bind())
    columns = [c['name'] for c in inspector.get_columns('integration_tokens')]
    
    if 'account_email' not in columns:
        op.add_column('integration_tokens', sa.Column('account_email', sa.String(255), nullable=True))
    if 'account_name' not in columns:
        op.add_column('integration_tokens', sa.Column('account_name', sa.String(255), nullable=True))

def downgrade():
    pass
