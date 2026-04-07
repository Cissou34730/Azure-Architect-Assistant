"""add_project_state_components

Revision ID: 20260402_0003
Revises: 20260401_0002
Create Date: 2026-04-02

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260402_0003"
down_revision: str | None = "20260401_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the generic ProjectState component store table."""
    op.create_table(
        "project_state_components",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("component_key", sa.String(length=128), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "component_key"),
    )


def downgrade() -> None:
    """Drop the generic ProjectState component store table."""
    op.drop_table("project_state_components")
