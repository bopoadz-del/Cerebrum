"""create projects and google drive projects

Revision ID: cf3ec9cca1a4
Revises: 004_add_document_tables
Create Date: 2026-02-24 19:24:00.000000

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "cf3ec9cca1a4"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- projects ---
    op.create_table(
        "projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False, server_default="unknown"),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    # --- google_drive_projects ---
    op.create_table(
        "google_drive_projects",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("root_folder_id", sa.String(length=128), nullable=False),
        sa.Column("root_folder_name", sa.String(length=512), nullable=False),
        sa.Column("score", sa.Float(), nullable=False, server_default="0"),
        sa.Column("confidence", sa.Float(), nullable=False, server_default="0"),
        sa.Column("reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("entry_points", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("tags", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("indexing_status", sa.String(length=32), nullable=False, server_default="idle"),
        sa.Column("indexing_progress", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("last_indexed_at", sa.DateTime(), nullable=True),
        sa.Column("last_scanned_at", sa.DateTime(), nullable=True),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.text("now()")),
    )

    op.create_index("ix_gdp_user_root", "google_drive_projects", ["user_id", "root_folder_id"], unique=True)
    op.create_index("ix_gdp_user_id", "google_drive_projects", ["user_id"], unique=False)
    op.create_index("ix_gdp_project_id", "google_drive_projects", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_gdp_project_id", table_name="google_drive_projects")
    op.drop_index("ix_gdp_user_id", table_name="google_drive_projects")
    op.drop_index("ix_gdp_user_root", table_name="google_drive_projects")
    op.drop_table("google_drive_projects")
    op.drop_table("projects")
