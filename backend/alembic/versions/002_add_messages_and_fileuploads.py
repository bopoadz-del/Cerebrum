"""add messages and fileuploads

Revision ID: 002
Revises: 001
Create Date: 2026-04-11

"""
revision = '002'
down_revision = '001'

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


def upgrade():
    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('model', sa.String(50), nullable=True),
        sa.Column('attachments', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversation_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for messages
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_user_id', 'messages', ['user_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])
    
    # Create file_uploads table
    op.create_table(
        'file_uploads',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('filename', sa.String(500), nullable=False),
        sa.Column('original_filename', sa.String(500), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('storage_provider', sa.String(20), nullable=False, server_default='gcs'),
        sa.Column('storage_bucket', sa.String(255), nullable=False),
        sa.Column('storage_path', sa.String(500), nullable=False),
        sa.Column('public_url', sa.String(1000), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversation_sessions.id'], ondelete='SET NULL'),
    )
    
    # Create indexes for file_uploads
    op.create_index('ix_file_uploads_user_id', 'file_uploads', ['user_id'])
    op.create_index('ix_file_uploads_conversation_id', 'file_uploads', ['conversation_id'])
    op.create_index('ix_file_uploads_created_at', 'file_uploads', ['created_at'])


def downgrade():
    op.drop_index('ix_file_uploads_created_at', table_name='file_uploads')
    op.drop_index('ix_file_uploads_conversation_id', table_name='file_uploads')
    op.drop_index('ix_file_uploads_user_id', table_name='file_uploads')
    op.drop_table('file_uploads')
    
    op.drop_index('ix_messages_created_at', table_name='messages')
    op.drop_index('ix_messages_user_id', table_name='messages')
    op.drop_index('ix_messages_conversation_id', table_name='messages')
    op.drop_table('messages')
