"""SQLAlchemy models for the resilient ingestion pipeline."""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Text,
    Integer,
    DateTime,
    JSON,
    ForeignKey,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class JobStatus(str, enum.Enum):
    """Lifecycle states for an ingestion job."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class QueueStatus(str, enum.Enum):
    """Processing states for queued ingestion work items."""

    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    DONE = "DONE"
    ERROR = "ERROR"


class IngestionJob(Base):
    """Persisted ingestion job definition."""

    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        Index("ix_ingestion_jobs_status", "status"),
        Index("ix_ingestion_jobs_created_at", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kb_id = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default=JobStatus.PENDING.value)
    source_type = Column(String(50), nullable=False)
    source_config = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_items = Column(Integer, nullable=True, default=0)
    processed_items = Column(Integer, nullable=True, default=0)
    priority = Column(Integer, nullable=False, default=0)

    queue_items = relationship(
        "IngestionQueueItem",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def update_status(self, status: JobStatus) -> None:
        self.status = status.value
        self.updated_at = datetime.utcnow()


class IngestionQueueItem(Base):
    """Chunk-level work item persisted between producer and consumer stages."""

    __tablename__ = "ingestion_queue"
    __table_args__ = (
        UniqueConstraint("job_id", "doc_hash", name="uq_ingestion_queue_job_doc_hash"),
        Index("ix_ingestion_queue_status_available", "status", "available_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("ingestion_jobs.id", ondelete="CASCADE"), nullable=False)
    doc_hash = Column(String(128), nullable=False)
    content = Column(Text, nullable=False)
    metadata = Column(JSON, nullable=False, default=dict)
    status = Column(String(20), nullable=False, default=QueueStatus.PENDING.value)
    attempts = Column(Integer, nullable=False, default=0)
    error_log = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    available_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    job = relationship("IngestionJob", back_populates="queue_items")

    def mark_processing(self) -> None:
        self.status = QueueStatus.PROCESSING.value
        self.updated_at = datetime.utcnow()

    def mark_done(self) -> None:
        self.status = QueueStatus.DONE.value
        self.updated_at = datetime.utcnow()

    def mark_error(self, message: str) -> None:
        self.status = QueueStatus.ERROR.value
        self.error_log = message
        self.attempts += 1
        self.updated_at = datetime.utcnow()
*** End Patch