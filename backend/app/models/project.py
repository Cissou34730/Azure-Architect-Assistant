"""
SQLAlchemy models for projects and related entities.
Migrated from TypeScript backend.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, ForeignKey, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Project(Base):
    """Project model - Architecture project container."""

    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    text_requirements = Column(Text, nullable=True)
    created_at = Column(
        String(30),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )
    deleted_at = Column(String(30), nullable=True)

    # Relationships
    documents = relationship(
        "ProjectDocument", back_populates="project", cascade="all, delete-orphan"
    )
    states = relationship(
        "ProjectState",
        back_populates="project",
        cascade="all, delete-orphan",
        uselist=False,
    )
    messages = relationship(
        "ConversationMessage", back_populates="project", cascade="all, delete-orphan"
    )
    checklists = relationship(
        "Checklist", back_populates="project", cascade="all, delete-orphan"
    )
    checklist_evaluations = relationship(
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


class ProjectDocument(Base):
    """Document uploaded to a project."""

    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    raw_text = Column(Text, nullable=False)
    stored_path = Column(Text, nullable=True)
    parse_status = Column(String(32), nullable=True)
    analysis_status = Column(String(32), nullable=True)
    parse_error = Column(Text, nullable=True)
    analyzed_at = Column(String(30), nullable=True)
    last_analysis_run_id = Column(String(36), nullable=True)
    uploaded_at = Column(
        String(30),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    # Relationships
    project = relationship("Project", back_populates="documents")

    def to_dict(self) -> dict[str, str | None]:
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "projectId": str(self.project_id),
            "fileName": str(self.file_name),
            "mimeType": str(self.mime_type),
            "rawText": str(self.raw_text),
            "storedPath": self.stored_path,
            "parseStatus": self.parse_status,
            "analysisStatus": self.analysis_status,
            "parseError": self.parse_error,
            "uploadedAt": str(self.uploaded_at),
            "analyzedAt": self.analyzed_at,
            "lastAnalysisRunId": self.last_analysis_run_id,
        }


class ProjectState(Base):
    """Project state - Architecture Sheet."""

    __tablename__ = "project_states"

    project_id = Column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    state = Column(Text, nullable=False)  # JSON string
    updated_at = Column(
        String(30),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )

    # Relationships
    project = relationship("Project", back_populates="states")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        state_data: dict[str, Any] = json.loads(str(self.state))
        state_data["projectId"] = str(self.project_id)
        state_data["lastUpdated"] = str(self.updated_at)
        return state_data


class ConversationMessage(Base):
    """Chat message in project conversation."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(
        String(30),
        nullable=False,
        default=lambda: datetime.now(timezone.utc).isoformat(),
    )
    waf_sources = Column(Text, nullable=True)  # JSON string for WAF sources

    # Relationships
    project = relationship("Project", back_populates="messages")

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

