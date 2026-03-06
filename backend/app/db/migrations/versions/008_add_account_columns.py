"""Add account_email and account_name to integration_tokens

Revision ID: 008
Revises: 007
Create Date: 2024-03-05

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    # Check if columns exist before adding
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [c['name'] for c in inspector.get_columns('integration_tokens')]
    
    if 'account_email' not in columns:
        op.add_column('integration_tokens', sa.Column('account_email', sa.String(255), nullable=True))
        print("Added account_email column")
    
    if 'account_name' not in columns:
        op.add_column('integration_tokens', sa.Column('account_name', sa.String(255), nullable=True))
        print("Added account_name column")


def downgrade():
    op.drop_column('integration_tokens', 'account_email')
    op.drop_column('integration_tokens', 'account_name')
