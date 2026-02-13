"""Create WAF normalized checklist tables

Revision ID: 005
Revises: 004
Create Date: 2026-02-04

This migration creates normalized tables for WAF checklist management:
- checklist_templates: Template definitions from Microsoft Learn
- checklists: Project-specific checklist instances
- checklist_items: Individual checklist items
- checklist_item_evaluations: Evaluation history per item

IMPORTANT: After running this migration, execute backfill:
python scripts/backfill_waf.py --dry-run --batch-size=50

Estimated runtime: ~5-10 minutes for 1000 projects
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum types manually for Postgres, though SQLite won't strictly need them
    # For SQLite compatibility with Alembic, we can just use sa.Enum

    # 1. checklist_templates
    op.create_table(
        "checklist_templates",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("source_url", sa.String(length=1000), nullable=False),
        sa.Column("source_version", sa.String(length=100), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
    )
    op.create_index(
        "ix_template_source_version",
        "checklist_templates",
        ["source", "source_version"],
        unique=False,
    )

    # 2. checklists
    op.create_table(
        "checklists",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("template_slug", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=True),
        sa.Column("created_by", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            sa.Enum("open", "archived", name="checklist_status"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["template_id"], ["checklist_templates.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "template_id", name="uq_project_template"),
    )
    op.create_index("ix_checklist_project_id", "checklists", ["project_id"], unique=False)
    op.create_index("ix_checklist_status", "checklists", ["status"], unique=False)

    # 3. checklist_items
    op.create_table(
        "checklist_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("checklist_id", sa.Uuid(), nullable=False),
        sa.Column("template_item_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=1000), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("pillar", sa.String(length=100), nullable=True),
        sa.Column(
            "severity",
            sa.Enum("low", "medium", "high", "critical", name="severity_level"),
            nullable=False,
        ),
        sa.Column("guidance", sa.JSON(), nullable=True),
        sa.Column("item_metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["checklist_id"], ["checklists.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("checklist_id", "template_item_id", name="uq_checklist_item_template"),
    )
    op.create_index("ix_item_checklist_id", "checklist_items", ["checklist_id"], unique=False)
    op.create_index("ix_item_severity", "checklist_items", ["severity"], unique=False)

    # 4. checklist_item_evaluations
    op.create_table(
        "checklist_item_evaluations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("evaluator", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "in_progress",
                "fixed",
                "false_positive",
                name="evaluation_status",
            ),
            nullable=False,
        ),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("evidence", sa.JSON(), nullable=True),
        sa.Column("source_type", sa.String(length=100), nullable=False),
        sa.Column("source_id", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["item_id"], ["checklist_items.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_evaluation_dedupe",
        "checklist_item_evaluations",
        ["item_id", "source_type", "source_id"],
        unique=False,
    )
    op.create_index(
        "ix_evaluation_item_id", "checklist_item_evaluations", ["item_id"], unique=False
    )
    op.create_index(
        "ix_evaluation_project_id",
        "checklist_item_evaluations",
        ["project_id"],
        unique=False,
    )
    op.create_index(
        "ix_evaluation_project_item",
        "checklist_item_evaluations",
        ["project_id", "item_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("checklist_item_evaluations")
    op.drop_table("checklist_items")
    op.drop_table("checklists")
    op.drop_table("checklist_templates")

    # Enum types are automatically handled in SQLite, but for Postgres we'd need:
    # op.execute("DROP TYPE checklist_status")
    # op.execute("DROP TYPE severity_level")
    # op.execute("DROP TYPE evaluation_status")
    # WARNING: This will permanently delete all checklist data
