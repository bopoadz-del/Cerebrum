"""add_quality_inspections

Revision ID: 009
Revises: ef6e1e8c0a26
Create Date: 2026-04-20 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '009'
down_revision = 'ef6e1e8c0a26'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'quality_standards',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=False),
        sa.Column('checklist_items', postgresql.JSONB(), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
    )
    op.create_index('ix_quality_standards_category', 'quality_standards', ['category'])
    op.create_index('ix_quality_standards_code', 'quality_standards', ['code'])

    op.create_table(
        'quality_inspections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('project_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('inspection_type', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='pending'),
        sa.Column('inspector_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('findings', postgresql.JSONB(), nullable=True),
        sa.Column('checklist_results', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['inspector_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_quality_inspections_project_id', 'quality_inspections', ['project_id'])
    op.create_index('ix_quality_inspections_status', 'quality_inspections', ['status'])
    op.create_index('ix_quality_inspections_type', 'quality_inspections', ['inspection_type'])

    # Seed built-in quality standards
    op.execute("""
        INSERT INTO quality_standards (id, name, code, description, category, checklist_items)
        VALUES
        (gen_random_uuid(), 'Concrete Strength', 'ACI-318', 'Building code requirements for structural concrete', 'structural',
         '[{"id":"1","description":"Min compressive strength 3000 psi","required":true,"category":"strength"},
           {"id":"2","description":"Proper curing time 28 days","required":true,"category":"curing"},
           {"id":"3","description":"Water-cement ratio within spec","required":true,"category":"mix"}]'::jsonb),
        (gen_random_uuid(), 'Rebar Grade Compliance', 'ASTM-A615', 'Standard specification for deformed steel bars', 'structural',
         '[{"id":"1","description":"Grade 60 minimum for structural","required":true,"category":"material"},
           {"id":"2","description":"Proper lap splice lengths","required":true,"category":"installation"},
           {"id":"3","description":"Corrosion protection where required","required":false,"category":"protection"}]'::jsonb),
        (gen_random_uuid(), 'Fire Safety', 'NFPA-101', 'Life Safety Code compliance', 'safety',
         '[{"id":"1","description":"Sprinkler coverage complete","required":true,"category":"fire_suppression"},
           {"id":"2","description":"Exit signs illuminated","required":true,"category":"egress"},
           {"id":"3","description":"Fire doors rated and self-closing","required":true,"category":"fire_doors"}]'::jsonb)
    """)


def downgrade():
    op.drop_table('quality_inspections')
    op.drop_table('quality_standards')
