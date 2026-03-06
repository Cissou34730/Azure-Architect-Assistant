"""initial_ingestion_schema

Revision ID: a1b2c3d4e5f6
Revises:
Create Date: 2026-02-08

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = 'a1b2c3d4e5f6'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ingestion_jobs',
        sa.Column('id', sa.String(length=36), primary_key=True, nullable=False),
        sa.Column('kb_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_config', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('total_items', sa.Integer(), nullable=True),
        sa.Column('processed_items', sa.Integer(), nullable=True),
        sa.Column('priority', sa.Integer(), nullable=False),
        sa.Column('checkpoint', sa.JSON(), nullable=True),
        sa.Column('counters', sa.JSON(), nullable=True),
        sa.Column('heartbeat_at', sa.DateTime(), nullable=True),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('last_error', sa.Text(), nullable=True),
    )
    op.create_index('ix_ingestion_jobs_status', 'ingestion_jobs', ['status'])
    op.create_index('ix_ingestion_jobs_created_at', 'ingestion_jobs', ['created_at'])

    op.create_table(
        'ingestion_phase_status',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column('job_id', sa.String(length=36), sa.ForeignKey('ingestion_jobs.id', ondelete='CASCADE'), nullable=False),
        sa.Column('phase_name', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('progress_percent', sa.Integer(), nullable=False),
        sa.Column('items_processed', sa.Integer(), nullable=False),
        sa.Column('items_total', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('job_id', 'phase_name', name='uq_phase_status_job_phase'),
    )
    op.create_index('ix_phase_status_job_id', 'ingestion_phase_status', ['job_id'])

def downgrade() -> None:
    op.drop_index('ix_phase_status_job_id', table_name='ingestion_phase_status')
    op.drop_table('ingestion_phase_status')

    op.drop_index('ix_ingestion_jobs_created_at', table_name='ingestion_jobs')
    op.drop_index('ix_ingestion_jobs_status', table_name='ingestion_jobs')
    op.drop_table('ingestion_jobs')
