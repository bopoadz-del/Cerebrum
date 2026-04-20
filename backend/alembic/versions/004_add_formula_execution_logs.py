"""add formula_execution_logs table

Revision ID: 004
Revises: 003
Create Date: 2026-04-20

Creates the formula_execution_logs table required by the FormulaExecutionLog model.
"""
revision = '004'
down_revision = '003'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine.reflection import Inspector


def _table_exists(conn, table_name: str) -> bool:
    inspector = Inspector.from_engine(conn)
    return table_name in inspector.get_table_names()


def upgrade() -> None:
    conn = op.get_bind()

    if _table_exists(conn, 'formula_execution_logs'):
        return

    op.create_table(
        'formula_execution_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column('execution_id', sa.String(100), nullable=False, unique=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('formula_id', sa.String(100), nullable=False),
        sa.Column('formula_type', sa.String(50), nullable=False),
        sa.Column('formula_name', sa.String(255), nullable=True),
        sa.Column('inputs', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('outputs', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('credibility_score', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('credibility_level', sa.String(20), nullable=False, server_default='uncertain'),
        sa.Column('credibility_factors', postgresql.JSONB, nullable=True),
        sa.Column('status', sa.String(50), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('execution_time_ms', sa.Float, nullable=False, server_default='0.0'),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source', sa.String(50), nullable=True),
        sa.Column('request_id', sa.String(100), nullable=True),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(255), nullable=True),
    )

    op.create_index('ix_formula_execution_logs_execution_id', 'formula_execution_logs', ['execution_id'], unique=True)
    op.create_index('ix_formula_execution_logs_user_id', 'formula_execution_logs', ['user_id'], unique=False)
    op.create_index('ix_formula_execution_logs_formula_id', 'formula_execution_logs', ['formula_id'], unique=False)
    op.create_index('ix_formula_execution_logs_formula_type', 'formula_execution_logs', ['formula_type'], unique=False)


def downgrade() -> None:
    op.drop_table('formula_execution_logs')
