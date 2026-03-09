"""SQLAlchemy models for WAF checklists."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from typing import Any
from uuid import UUID

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

# Import base from existing models
from app.models.project import Base


class ChecklistStatus(str, PyEnum):
    """Status of a checklist."""

    OPEN = 'open'
    ARCHIVED = 'archived'


class SeverityLevel(str, PyEnum):
    """Severity level of a checklist item."""

    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class EvaluationStatus(str, PyEnum):
    """Status of a checklist item evaluation."""

    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    FIXED = 'fixed'
    FALSE_POSITIVE = 'false_positive'


class ChecklistTemplate(Base):
    """
    Template definitions for WAF checklists from Microsoft Learn.
    """

    __tablename__ = 'checklist_templates'

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    source_version: Mapped[str] = mapped_column(String(100), nullable=False)
    content: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    checklists: Mapped[list[Checklist]] = relationship('Checklist', back_populates='template')

    __table_args__ = (Index('ix_template_source_version', 'source', 'source_version'),)


class Checklist(Base):
    """
    Project-specific checklist instances.
    """

    __tablename__ = 'checklists'

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id'), nullable=False)
    template_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey('checklist_templates.id'), nullable=True)
    template_slug: Mapped[str | None] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[ChecklistStatus] = mapped_column(
        Enum(ChecklistStatus, name='checklist_status'), default=ChecklistStatus.OPEN, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    project: Mapped[Any] = relationship('Project', back_populates='checklists')
    template: Mapped[ChecklistTemplate | None] = relationship('ChecklistTemplate', back_populates='checklists')
    items: Mapped[list[ChecklistItem]] = relationship('ChecklistItem', back_populates='checklist', cascade='all, delete-orphan')

    __table_args__ = (
        Index('ix_checklist_project_id', 'project_id'),
        UniqueConstraint('project_id', 'template_id', name='uq_project_template'),
        Index('ix_checklist_status', 'status'),
    )


class ChecklistItem(Base):
    """
    Individual checklist items within a checklist.
    """

    __tablename__ = 'checklist_items'

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    checklist_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('checklists.id', ondelete='CASCADE'), nullable=False
    )
    template_item_id: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    pillar: Mapped[str | None] = mapped_column(String(100), nullable=True)
    severity: Mapped[SeverityLevel] = mapped_column(Enum(SeverityLevel, name='severity_level'), nullable=False)
    guidance: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    item_metadata: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    checklist: Mapped[Checklist] = relationship('Checklist', back_populates='items')
    evaluations: Mapped[list[ChecklistItemEvaluation]] = relationship(
        'ChecklistItemEvaluation', back_populates='item', cascade='all, delete-orphan'
    )

    __table_args__ = (
        Index('ix_item_checklist_id', 'checklist_id'),
        Index('ix_item_severity', 'severity'),
        UniqueConstraint('checklist_id', 'template_item_id', name='uq_checklist_item_template'),
    )

    @classmethod
    def compute_deterministic_id(
        cls, project_id: str, template_slug: str, template_item_id: str, namespace_uuid: UUID
    ) -> UUID:
        """
        Generates a deterministic UUID for checklist items to ensure idempotency.
        """
        # Uses UUID v5 with a fixed namespace and a string combining key identifying fields
        name = f'{project_id}:{template_slug}:{template_item_id}'
        return uuid.uuid5(namespace_uuid, name)


class ChecklistItemEvaluation(Base):
    """
    Evaluation history per checklist item.
    """

    __tablename__ = 'checklist_item_evaluations'

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey('checklist_items.id', ondelete='CASCADE'), nullable=False
    )
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey('projects.id'), nullable=False)
    evaluator: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[EvaluationStatus] = mapped_column(Enum(EvaluationStatus, name='evaluation_status'), nullable=False)
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    item: Mapped[ChecklistItem] = relationship('ChecklistItem', back_populates='evaluations')
    project: Mapped[Any] = relationship('Project', back_populates='checklist_evaluations')

    __table_args__ = (
        Index('ix_evaluation_item_id', 'item_id'),
        Index('ix_evaluation_project_id', 'project_id'),
        Index('ix_evaluation_project_item', 'project_id', 'item_id', 'created_at'),
        Index('ix_evaluation_dedupe', 'item_id', 'source_type', 'source_id'),
    )
