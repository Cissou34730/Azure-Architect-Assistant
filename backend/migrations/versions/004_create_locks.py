"""Create locks table.

Revision ID: 004
Revises: 003
Create Date: 2025-12-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create locks table."""
    op.create_table(
        'locks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('diagram_set_id', sa.String(36), nullable=False),
        sa.Column('lock_held_by', sa.String(255), nullable=False),
        sa.Column('lock_acquired_at', sa.DateTime(), nullable=False),
        sa.Column('lock_expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ['diagram_set_id'],
            ['diagram_sets.id'],
            name='fk_locks_diagram_set_id',
            ondelete='CASCADE'
        ),
        sa.UniqueConstraint('diagram_set_id', name='uq_locks_diagram_set_id'),
    )


def downgrade() -> None:
    """Drop locks table."""
    op.drop_table('locks')
