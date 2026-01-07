"""Create ambiguity_reports table.

Revision ID: 003
Revises: 002
Create Date: 2025-12-17

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create ambiguity_reports table."""
    op.create_table(
        "ambiguity_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("diagram_set_id", sa.String(36), nullable=False),
        sa.Column("ambiguous_text", sa.Text(), nullable=False),
        sa.Column("suggested_clarification", sa.Text(), nullable=False),
        sa.Column("resolved", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["diagram_set_id"],
            ["diagram_sets.id"],
            name="fk_ambiguity_reports_diagram_set_id",
            ondelete="CASCADE",
        ),
    )

    # Create indexes
    op.create_index(
        "ix_ambiguity_reports_diagram_set_id", "ambiguity_reports", ["diagram_set_id"]
    )


def downgrade() -> None:
    """Drop ambiguity_reports table."""
    op.drop_index("ix_ambiguity_reports_diagram_set_id", table_name="ambiguity_reports")
    op.drop_table("ambiguity_reports")
