"""Create diagrams table.

Revision ID: 002
Revises: 001
Create Date: 2025-12-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create diagrams table."""
    op.create_table(
        "diagrams",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("diagram_set_id", sa.String(36), nullable=False),
        sa.Column("diagram_type", sa.String(50), nullable=False),
        sa.Column("source_code", sa.Text(), nullable=False),
        sa.Column("rendered_svg", sa.LargeBinary(), nullable=True),
        sa.Column("rendered_png", sa.LargeBinary(), nullable=True),
        sa.Column("version", sa.String(20), nullable=False, server_default="v1.0.0"),
        sa.Column("previous_version_id", sa.String(36), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["diagram_set_id"],
            ["diagram_sets.id"],
            name="fk_diagrams_diagram_set_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["previous_version_id"],
            ["diagrams.id"],
            name="fk_diagrams_previous_version_id",
        ),
    )

    # Create indexes
    op.create_index("ix_diagrams_diagram_set_id", "diagrams", ["diagram_set_id"])


def downgrade() -> None:
    """Drop diagrams table."""
    op.drop_index("ix_diagrams_diagram_set_id", table_name="diagrams")
    op.drop_table("diagrams")
