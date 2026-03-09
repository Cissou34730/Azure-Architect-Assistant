"""SQLAlchemy models for projects and related entities."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for project-related SQLAlchemy models."""


class Project(Base):
    """Project model - Architecture project container."""

    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    text_requirements: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )
    deleted_at: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Relationships
    documents: Mapped[list[ProjectDocument]] = relationship(
        "ProjectDocument", back_populates="project", cascade="all, delete-orphan"
    )
    states: Mapped[ProjectState | None] = relationship(
        "ProjectState",
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )
    messages: Mapped[list[ConversationMessage]] = relationship(
        "ConversationMessage", back_populates="project", cascade="all, delete-orphan"
    )
    checklists: Mapped[list[Any]] = relationship(
        "Checklist", back_populates="project", cascade="all, delete-orphan"
    )
    checklist_evaluations: Mapped[list[Any]] = relationship(
        "ChecklistItemEvaluation",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "name": str(self.name),
            "textRequirements": self.text_requirements or "",
            "createdAt": str(self.created_at),
        }

    @property
    def state(self) -> str | None:
        """Compatibility accessor for legacy callers expecting project.state."""
        return self.states.state if self.states is not None else None

    @property
    def updated_at(self) -> str | None:
        """Compatibility accessor for legacy callers expecting project.updated_at."""
        return self.states.updated_at if self.states is not None else None


class ProjectDocument(Base):
    """Document uploaded to a project."""

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    stored_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    analysis_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    parse_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    analyzed_at: Mapped[str | None] = mapped_column(String(30), nullable=True)
    last_analysis_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    uploaded_at: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="documents")

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "projectId": str(self.project_id),
            "fileName": str(self.file_name),
            "mimeType": str(self.mime_type),
            "rawText": str(self.raw_text),
            "storedPath": str(self.stored_path) if self.stored_path is not None else None,
            "parseStatus": str(self.parse_status) if self.parse_status is not None else None,
            "analysisStatus": str(self.analysis_status) if self.analysis_status is not None else None,
            "parseError": str(self.parse_error) if self.parse_error is not None else None,
            "uploadedAt": str(self.uploaded_at),
            "analyzedAt": str(self.analyzed_at) if self.analyzed_at is not None else None,
            "lastAnalysisRunId": str(self.last_analysis_run_id) if self.last_analysis_run_id is not None else None,
        }


class ProjectState(Base):
    """Project state - Architecture Sheet."""

    __tablename__ = "project_states"

    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    state: Mapped[str] = mapped_column(Text, nullable=False)  # JSON string
    updated_at: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="states")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        state_data: dict[str, Any] = json.loads(str(self.state))
        state_data["projectId"] = str(self.project_id)
        state_data["lastUpdated"] = str(self.updated_at)
        return state_data


class ConversationMessage(Base):
    """Chat message in project conversation."""

    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # "user" or "assistant"
    content: Mapped[str] = mapped_column(Text, nullable=False)
    timestamp: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )
    waf_sources: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string for WAF sources

    # Relationships
    project: Mapped[Project] = relationship("Project", back_populates="messages")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        result: dict[str, Any] = {
            "id": str(self.id),
            "projectId": str(self.project_id),
            "role": str(self.role),
            "content": str(self.content),
            "timestamp": str(self.timestamp),
        }
        if self.waf_sources:
            result["wafSources"] = json.loads(str(self.waf_sources))
        return result

