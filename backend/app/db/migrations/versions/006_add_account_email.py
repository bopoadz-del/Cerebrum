"""Add account_email to integration_tokens

Revision ID: 006
Revises: 005
Create Date: 2026-02-28 01:30:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add account_email column
    op.add_column('integration_tokens', sa.Column('account_email', sa.String(255), nullable=True))
    op.add_column('integration_tokens', sa.Column('account_name', sa.String(255), nullable=True))


def downgrade() -> None:
    op.drop_column('integration_tokens', 'account_email')
    op.drop_column('integration_tokens', 'account_name')
