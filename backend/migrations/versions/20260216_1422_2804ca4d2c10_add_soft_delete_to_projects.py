"""Mako template for migration scripts."""

"""add_soft_delete_to_projects

Revision ID: 2804ca4d2c10
Revises: 005
Create Date: 2026-02-16 14:22:19.291249

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2804ca4d2c10'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Add deleted_at column to projects table for soft delete support
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.add_column(sa.Column('deleted_at', sa.String(length=30), nullable=True))


def downgrade() -> None:
    """Downgrade database schema."""
    # Remove deleted_at column from projects table
    with op.batch_alter_table('projects', schema=None) as batch_op:
        batch_op.drop_column('deleted_at')
