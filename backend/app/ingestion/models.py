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
    """Lifecycle states for an ingestion job (database model)."""
    NOT_STARTED = "NOT_STARTED"
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


class PhaseStatusDB(str, enum.Enum):
    """Phase status values for database storage."""

    NOT_STARTED = "not_started"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class IngestionJob(Base):
    """Persisted ingestion job definition."""

    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        Index("ix_ingestion_jobs_status", "status"),
        Index("ix_ingestion_jobs_created_at", "created_at"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    kb_id = Column(String(255), nullable=False)
    status = Column(String(20), nullable=False, default=JobStatus.NOT_STARTED.value)
    source_type = Column(String(50), nullable=False)
    source_config = Column(JSON, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_items = Column(Integer, nullable=True, default=0)
    processed_items = Column(Integer, nullable=True, default=0)
    priority = Column(Integer, nullable=False, default=0)
    
    # Phase-level tracking
    current_phase = Column(String(50), nullable=True, default="loading")
    phase_progress = Column(JSON, nullable=True, default=dict)

    queue_items = relationship(
        "IngestionQueueItem",
        back_populates="job",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def update_status(self, status: JobStatus) -> None:
        self.status = status.value
        self.updated_at = datetime.utcnow()


class IngestionPhaseStatus(Base):
    """Tracks status of individual phases within an ingestion job."""

    __tablename__ = "ingestion_phase_status"
    __table_args__ = (
        UniqueConstraint("job_id", "phase_name", name="uq_phase_status_job_phase"),
        Index("ix_phase_status_job_id", "job_id"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(36), ForeignKey("ingestion_jobs.id", ondelete="CASCADE"), nullable=False)
    phase_name = Column(String(50), nullable=False)  # loading, chunking, embedding, indexing
    status = Column(String(20), nullable=False, default=PhaseStatusDB.NOT_STARTED.value)
    progress_percent = Column(Integer, nullable=False, default=0)
    items_processed = Column(Integer, nullable=False, default=0)
    items_total = Column(Integer, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship("IngestionJob", backref="phase_statuses")

    def start(self) -> None:
        """Mark phase as started."""
        self.status = PhaseStatusDB.RUNNING.value
        self.started_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def pause(self) -> None:
        """Mark phase as paused."""
        self.status = PhaseStatusDB.PAUSED.value
        self.updated_at = datetime.utcnow()

    def resume(self) -> None:
        """Mark phase as resumed."""
        self.status = PhaseStatusDB.RUNNING.value
        self.updated_at = datetime.utcnow()

    def complete(self) -> None:
        """Mark phase as completed."""
        self.status = PhaseStatusDB.COMPLETED.value
        self.progress_percent = 100
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def fail(self, error_message: str) -> None:
        """Mark phase as failed."""
        self.status = PhaseStatusDB.FAILED.value
        self.error_message = error_message
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def update_progress(self, items_processed: int, items_total: int = None) -> None:
        """Update phase progress."""
        self.items_processed = items_processed
        if items_total is not None:
            self.items_total = items_total
        
        if self.items_total and self.items_total > 0:
            self.progress_percent = min(100, int((items_processed / self.items_total) * 100))
        else:
            # Without total, cap at 99% until completion
            self.progress_percent = min(99, int((items_processed / max(items_processed + 1, 100)) * 100))
        
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
    # 'metadata' is reserved by SQLAlchemy Declarative; use attribute 'item_metadata'
    item_metadata = Column('metadata', JSON, nullable=False, default=dict)
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
