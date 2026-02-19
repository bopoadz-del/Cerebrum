"""add_document_tables

Revision ID: 004
Revises: 003_integration_tokens
Create Date: 2026-02-18 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('drive_id', sa.String(length=255), nullable=False),
        sa.Column('filename', sa.String(length=500), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('project_name', sa.String(length=255), nullable=True),
        sa.Column('mime_type', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes
    op.create_index(op.f('ix_documents_drive_id'), 'documents', ['drive_id'], unique=True)
    op.create_index(op.f('ix_documents_project_name'), 'documents', ['project_name'], unique=False)
    op.create_index(op.f('ix_documents_status'), 'documents', ['status'], unique=False)
    op.create_index(op.f('ix_documents_user_id'), 'documents', ['user_id'], unique=False)
    
    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('document_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('embedding_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(op.f('ix_document_chunks_document_id'), 'document_chunks', ['document_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_document_chunks_document_id'), table_name='document_chunks')
    op.drop_table('document_chunks')
    
    op.drop_index(op.f('ix_documents_user_id'), table_name='documents')
    op.drop_index(op.f('ix_documents_status'), table_name='documents')
    op.drop_index(op.f('ix_documents_project_name'), table_name='documents')
    op.drop_index(op.f('ix_documents_drive_id'), table_name='documents')
    op.drop_table('documents')
