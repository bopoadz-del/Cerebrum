"""add_google_drive_projects

Revision ID: 010
Revises: 009
Create Date: 2026-04-20 13:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '010'
down_revision = '009'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'google_drive_projects',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False, index=True),
        sa.Column('drive_folder_id', sa.String(255), nullable=False),
        sa.Column('folder_name', sa.String(500), nullable=True),
        sa.Column('folder_path', sa.Text(), nullable=True),
        sa.Column('is_synced', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_google_drive_projects_project_id', 'google_drive_projects', ['project_id'])
    op.create_index('ix_google_drive_projects_drive_folder_id', 'google_drive_projects', ['drive_folder_id'])


def downgrade():
    op.drop_table('google_drive_projects')
