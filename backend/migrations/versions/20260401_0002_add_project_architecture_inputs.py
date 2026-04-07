"""add_project_architecture_inputs

Revision ID: 20260401_0002
Revises: 20260329_0001
Create Date: 2026-04-01

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260401_0002"
down_revision: str | None = "20260329_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the dedicated project architecture-input table."""
    op.create_table(
        "project_architecture_inputs",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("context_json", sa.Text(), nullable=True),
        sa.Column("nfrs_json", sa.Text(), nullable=True),
        sa.Column("application_structure_json", sa.Text(), nullable=True),
        sa.Column("data_compliance_json", sa.Text(), nullable=True),
        sa.Column("technical_constraints_json", sa.Text(), nullable=True),
        sa.Column("open_questions_json", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.String(length=30), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id"),
    )


def downgrade() -> None:
    """Drop the dedicated project architecture-input table."""
    op.drop_table("project_architecture_inputs")
