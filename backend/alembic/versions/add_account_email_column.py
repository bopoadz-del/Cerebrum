"""add account_email to integration_tokens

Revision ID: add_email_col
Revises: 
Create Date: 2024-03-08 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_email_col'
down_revision = None  # Update this if you know your last migration
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('integration_tokens', sa.Column('account_email', sa.String(255), nullable=True))

def downgrade():
    op.drop_column('integration_tokens', 'account_email')
