"""add edge control-plane tables

Revision ID: 005
Revises: 004
Create Date: 2026-07-17
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def _base_columns() -> list[sa.Column]:
    return [
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    ]


def upgrade() -> None:
    op.create_table(
        "edge_devices",
        *_base_columns(),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("device_type", sa.String(length=64), server_default="generic", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="provisioning", nullable=False),
        sa.Column("software_version", sa.String(length=64), nullable=True),
        sa.Column("capabilities", postgresql.JSONB(), server_default="[]", nullable=False),
        sa.Column("hardware", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("heartbeat_interval_seconds", sa.Integer(), server_default="30", nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id", "external_id", name="uq_edge_device_tenant_external"
        ),
    )
    op.create_index("ix_edge_devices_tenant_id", "edge_devices", ["tenant_id"])
    op.create_index("ix_edge_devices_deleted_at", "edge_devices", ["deleted_at"])

    op.create_table(
        "edge_heartbeats",
        *_base_columns(),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column("metrics", postgresql.JSONB(), server_default="{}", nullable=False),
        sa.Column("active_model_version", sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["edge_devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_edge_heartbeats_device_id", "edge_heartbeats", ["device_id"])
    op.create_index("ix_edge_heartbeats_received_at", "edge_heartbeats", ["received_at"])

    op.create_table(
        "edge_deployments",
        *_base_columns(),
        sa.Column("device_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("model_name", sa.String(length=255), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("adapter", sa.String(length=32), server_default="mock", nullable=False),
        sa.Column("artifact_uri", sa.String(length=1024), nullable=True),
        sa.Column("artifact_sha256", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("inference_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("average_latency_ms", sa.Float(), nullable=True),
        sa.Column("latest_drift_score", sa.Float(), nullable=True),
        sa.Column("retrain_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["edge_devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_edge_deployments_device_id", "edge_deployments", ["device_id"])
    op.create_index("ix_edge_deployments_status", "edge_deployments", ["status"])


def downgrade() -> None:
    op.drop_table("edge_deployments")
    op.drop_table("edge_heartbeats")
    op.drop_table("edge_devices")
