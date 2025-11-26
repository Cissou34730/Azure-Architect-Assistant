"""
SQLAlchemy models for projects and related entities.
Migrated from TypeScript backend.
"""

from sqlalchemy import Column, String, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime
import uuid

Base = declarative_base()


class Project(Base):
    """Project model - Architecture project container."""
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    text_requirements = Column(Text, nullable=True)
    created_at = Column(String(30), nullable=False, default=lambda: datetime.utcnow().isoformat())

    # Relationships
    documents = relationship("ProjectDocument", back_populates="project", cascade="all, delete-orphan")
    states = relationship("ProjectState", back_populates="project", cascade="all, delete-orphan", uselist=False)
    messages = relationship("ConversationMessage", back_populates="project", cascade="all, delete-orphan")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "name": self.name,
            "textRequirements": self.text_requirements,
            "createdAt": self.created_at
        }


class ProjectDocument(Base):
    """Document uploaded to a project."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    file_name = Column(String(255), nullable=False)
    mime_type = Column(String(100), nullable=False)
    raw_text = Column(Text, nullable=False)
    uploaded_at = Column(String(30), nullable=False, default=lambda: datetime.utcnow().isoformat())

    # Relationships
    project = relationship("Project", back_populates="documents")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": self.id,
            "projectId": self.project_id,
            "fileName": self.file_name,
            "mimeType": self.mime_type,
            "rawText": self.raw_text,
            "uploadedAt": self.uploaded_at
        }


class ProjectState(Base):
    """Project state - Architecture Sheet."""
    __tablename__ = "project_states"

    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True)
    state = Column(Text, nullable=False)  # JSON string
    updated_at = Column(String(30), nullable=False, default=lambda: datetime.utcnow().isoformat())

    # Relationships
    project = relationship("Project", back_populates="states")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        import json
        state_data = json.loads(self.state)
        state_data["projectId"] = self.project_id
        state_data["lastUpdated"] = self.updated_at
        return state_data


class ConversationMessage(Base):
    """Chat message in project conversation."""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(20), nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    timestamp = Column(String(30), nullable=False, default=lambda: datetime.utcnow().isoformat())
    waf_sources = Column(Text, nullable=True)  # JSON string for WAF sources

    # Relationships
    project = relationship("Project", back_populates="messages")

    def to_dict(self):
        """Convert to dictionary for API responses."""
        import json
        result = {
            "id": self.id,
            "projectId": self.project_id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp
        }
        if self.waf_sources:
            result["wafSources"] = json.loads(self.waf_sources)
        return result
