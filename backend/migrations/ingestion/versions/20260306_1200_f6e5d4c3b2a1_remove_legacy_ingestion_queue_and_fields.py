"""remove_legacy_ingestion_queue_and_fields

Revision ID: f6e5d4c3b2a1
Revises: a1b2c3d4e5f6
Create Date: 2026-03-06

"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = 'f6e5d4c3b2a1'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table('ingestion_queue'):
        op.drop_table('ingestion_queue')

    with op.batch_alter_table('ingestion_jobs') as batch_op:
        columns = {column['name'] for column in inspector.get_columns('ingestion_jobs')}
        if 'current_phase' in columns:
            batch_op.drop_column('current_phase')
        if 'phase_progress' in columns:
            batch_op.drop_column('phase_progress')


def downgrade() -> None:
    with op.batch_alter_table('ingestion_jobs') as batch_op:
        batch_op.add_column(sa.Column('phase_progress', sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column('current_phase', sa.String(length=50), nullable=True))

    op.create_table(
        'ingestion_queue',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True, nullable=False),
        sa.Column(
            'job_id',
            sa.String(length=36),
            sa.ForeignKey('ingestion_jobs.id', ondelete='CASCADE'),
            nullable=False,
        ),
        sa.Column('doc_hash', sa.String(length=128), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('error_log', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('available_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('job_id', 'doc_hash', name='uq_ingestion_queue_job_doc_hash'),
    )
    op.create_index(
        'ix_ingestion_queue_status_available',
        'ingestion_queue',
        ['status', 'available_at'],
    )
