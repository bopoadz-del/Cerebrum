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
    # Add account_email column
    op.add_column('integration_tokens', sa.Column('account_email', sa.String(255), nullable=True))
    op.add_column('integration_tokens', sa.Column('account_name', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('integration_tokens', 'account_email')
    op.drop_column('integration_tokens', 'account_name')
