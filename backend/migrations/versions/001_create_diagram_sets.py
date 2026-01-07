"""Create diagram_sets table.

Revision ID: 001
Revises:
Create Date: 2025-12-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create diagram_sets table."""
    op.create_table(
        "diagram_sets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("adr_id", sa.String(255), nullable=True),
        sa.Column("input_description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )

    # Create indexes
    op.create_index("ix_diagram_sets_adr_id", "diagram_sets", ["adr_id"])


def downgrade() -> None:
    """Drop diagram_sets table."""
    op.drop_index("ix_diagram_sets_adr_id", table_name="diagram_sets")
    op.drop_table("diagram_sets")
