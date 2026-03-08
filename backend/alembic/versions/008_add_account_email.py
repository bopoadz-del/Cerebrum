"""add account_email column

Revision ID: 008
Create Date: 2024-03-08

"""
from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = None

def upgrade():
    op.add_column('integration_tokens', sa.Column('account_email', sa.String(255), nullable=True))

def downgrade():
    op.drop_column('integration_tokens', 'account_email')
