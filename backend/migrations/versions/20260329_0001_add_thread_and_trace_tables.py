"""add_thread_and_trace_tables

Revision ID: 20260329_0001
Revises: 2804ca4d2c10
Create Date: 2026-03-29

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '20260329_0001'
down_revision: str | None = '2804ca4d2c10'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add project_threads, project_trace_events tables and thread_id to messages."""
    # Create project_threads table
    op.create_table(
        'project_threads',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('stage', sa.String(length=50), nullable=True),
        sa.Column('title', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.String(length=30), nullable=False),
        sa.Column('updated_at', sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Create project_trace_events table
    op.create_table(
        'project_trace_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('project_id', sa.String(length=36), nullable=False),
        sa.Column('thread_id', sa.String(length=36), nullable=True),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('payload', sa.Text(), nullable=False, server_default='{}'),
        sa.Column('created_at', sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['thread_id'], ['project_threads.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Add thread_id column to messages table
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.add_column(sa.Column('thread_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            'fk_messages_thread_id',
            'project_threads',
            ['thread_id'],
            ['id'],
            ondelete='SET NULL',
        )


def downgrade() -> None:
    """Remove thread_id from messages, drop project_trace_events and project_threads."""
    with op.batch_alter_table('messages', schema=None) as batch_op:
        batch_op.drop_constraint('fk_messages_thread_id', type_='foreignkey')
        batch_op.drop_column('thread_id')

    op.drop_table('project_trace_events')
    op.drop_table('project_threads')
