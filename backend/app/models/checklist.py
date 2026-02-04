"""
SQLAlchemy models for WAF checklists.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from uuid import UUID

from sqlalchemy import (
    JSON,
    Column,
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
from sqlalchemy.orm import relationship

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

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=False)
    source = Column(String(100), nullable=False)  # e.g., "microsoft-learn"
    source_url = Column(String(1000), nullable=False)
    source_version = Column(String(100), nullable=False)
    content = Column(JSON, nullable=False)  # Original template structure
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    checklists = relationship('Checklist', back_populates='template')

    __table_args__ = (Index('ix_template_source_version', 'source', 'source_version'),)


class Checklist(Base):
    """
    Project-specific checklist instances.
    """

    __tablename__ = 'checklists'

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=False)
    template_id = Column(Uuid(as_uuid=True), ForeignKey('checklist_templates.id'), nullable=True)
    template_slug = Column(String(255), nullable=True)
    title = Column(String(500), nullable=False)
    version = Column(String(50), nullable=True)
    created_by = Column(String(255), nullable=True)
    status = Column(
        Enum(ChecklistStatus, name='checklist_status'), default=ChecklistStatus.OPEN, nullable=False
    )
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    project = relationship('Project', back_populates='checklists')
    template = relationship('ChecklistTemplate', back_populates='checklists')
    items = relationship('ChecklistItem', back_populates='checklist', cascade='all, delete-orphan')

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

    id = Column(Uuid(as_uuid=True), primary_key=True)  # Deterministic UUID v5
    checklist_id = Column(
        Uuid(as_uuid=True), ForeignKey('checklists.id', ondelete='CASCADE'), nullable=False
    )
    template_item_id = Column(String(255), nullable=False)  # Original ID from template
    title = Column(String(1000), nullable=False)
    description = Column(Text, nullable=True)
    pillar = Column(String(100), nullable=True)
    severity = Column(Enum(SeverityLevel, name='severity_level'), nullable=False)
    guidance = Column(JSON, nullable=True)  # Recommended fix
    item_metadata = Column(JSON, nullable=True)  # Tags, remediations
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    checklist = relationship('Checklist', back_populates='items')
    evaluations = relationship(
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

    id = Column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_id = Column(
        Uuid(as_uuid=True), ForeignKey('checklist_items.id', ondelete='CASCADE'), nullable=False
    )
    project_id = Column(String(36), ForeignKey('projects.id'), nullable=False)
    evaluator = Column(String(255), nullable=False)  # tool/agent/user identifier
    status = Column(Enum(EvaluationStatus, name='evaluation_status'), nullable=False)
    score = Column(Float, nullable=True)
    comment = Column(Text, nullable=True)
    evidence = Column(JSON, nullable=True)  # artifacts, citations
    source_type = Column(String(100), nullable=False)  # e.g., 'agent-validation', 'manual'
    source_id = Column(String(255), nullable=True)  # tool run ID for deduplication
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    item = relationship('ChecklistItem', back_populates='evaluations')
    project = relationship('Project', back_populates='checklist_evaluations')

    __table_args__ = (
        Index('ix_evaluation_item_id', 'item_id'),
        Index('ix_evaluation_project_id', 'project_id'),
        Index('ix_evaluation_project_item', 'project_id', 'item_id', 'created_at'),
        Index('ix_evaluation_dedupe', 'item_id', 'source_type', 'source_id'),
    )
