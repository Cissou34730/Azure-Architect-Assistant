"""
Phase Status Management
Tracks the status of each ingestion phase independently.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional
from datetime import datetime


class PhaseState(str, Enum):
    """Status of an individual phase."""
    PENDING = "pending"      # Not started yet
    IN_PROGRESS = "in_progress"  # Currently running
    COMPLETED = "completed"  # Successfully finished
    SKIPPED = "skipped"      # Skipped (e.g., resume after crawl complete)
    FAILED = "failed"        # Failed with error


@dataclass
class PhaseStatus:
    """Status information for a single phase."""
    state: PhaseState = PhaseState.PENDING
    progress: int = 0  # 0-100
    message: str = ""
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metrics: Dict = field(default_factory=dict)
    
    def start(self, message: str = ""):
        """Mark phase as started."""
        self.state = PhaseState.IN_PROGRESS
        self.started_at = datetime.utcnow()
        self.message = message
        
    def complete(self, message: str = ""):
        """Mark phase as completed."""
        self.state = PhaseState.COMPLETED
        self.progress = 100
        self.completed_at = datetime.utcnow()
        self.message = message
        
    def skip(self, reason: str = ""):
        """Mark phase as skipped."""
        self.state = PhaseState.SKIPPED
        self.progress = 100
        self.completed_at = datetime.utcnow()
        self.message = reason
        
    def fail(self, error: str):
        """Mark phase as failed."""
        self.state = PhaseState.FAILED
        self.error = error
        self.completed_at = datetime.utcnow()
        
    def update_progress(self, progress: int, message: str = ""):
        """Update progress within phase."""
        self.progress = min(100, max(0, progress))
        if message:
            self.message = message


@dataclass
class IngestionPhaseTracker:
    """Tracks status of all ingestion phases."""
    crawling: PhaseStatus = field(default_factory=PhaseStatus)
    chunking: PhaseStatus = field(default_factory=PhaseStatus)
    embedding: PhaseStatus = field(default_factory=PhaseStatus)
    indexing: PhaseStatus = field(default_factory=PhaseStatus)
    
    def get_current_phase(self) -> Optional[str]:
        """Get the name of the currently active phase."""
        if self.crawling.state == PhaseState.IN_PROGRESS:
            return "crawling"
        elif self.chunking.state == PhaseState.IN_PROGRESS:
            return "chunking"
        elif self.embedding.state == PhaseState.IN_PROGRESS:
            return "embedding"
        elif self.indexing.state == PhaseState.IN_PROGRESS:
            return "indexing"
        return None
    
    def get_overall_progress(self) -> int:
        """Calculate overall progress (0-100) across all phases."""
        # Weight each phase equally (25% each)
        total = 0
        phases = [self.crawling, self.chunking, self.embedding, self.indexing]
        
        for phase in phases:
            if phase.state == PhaseState.COMPLETED:
                total += 25
            elif phase.state == PhaseState.SKIPPED:
                total += 25
            elif phase.state == PhaseState.IN_PROGRESS:
                total += int(phase.progress * 0.25)
        
        return min(100, total)
    
    def is_complete(self) -> bool:
        """Check if all phases are complete or skipped."""
        phases = [self.crawling, self.chunking, self.embedding, self.indexing]
        return all(
            p.state in {PhaseState.COMPLETED, PhaseState.SKIPPED}
            for p in phases
        )
    
    def has_failure(self) -> bool:
        """Check if any phase has failed."""
        phases = [self.crawling, self.chunking, self.embedding, self.indexing]
        return any(p.state == PhaseState.FAILED for p in phases)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "crawling": {
                "state": self.crawling.state.value,
                "progress": self.crawling.progress,
                "message": self.crawling.message,
                "error": self.crawling.error,
                "started_at": self.crawling.started_at.isoformat() if self.crawling.started_at else None,
                "completed_at": self.crawling.completed_at.isoformat() if self.crawling.completed_at else None,
                "metrics": self.crawling.metrics,
            },
            "chunking": {
                "state": self.chunking.state.value,
                "progress": self.chunking.progress,
                "message": self.chunking.message,
                "error": self.chunking.error,
                "started_at": self.chunking.started_at.isoformat() if self.chunking.started_at else None,
                "completed_at": self.chunking.completed_at.isoformat() if self.chunking.completed_at else None,
                "metrics": self.chunking.metrics,
            },
            "embedding": {
                "state": self.embedding.state.value,
                "progress": self.embedding.progress,
                "message": self.embedding.message,
                "error": self.embedding.error,
                "started_at": self.embedding.started_at.isoformat() if self.embedding.started_at else None,
                "completed_at": self.embedding.completed_at.isoformat() if self.embedding.completed_at else None,
                "metrics": self.embedding.metrics,
            },
            "indexing": {
                "state": self.indexing.state.value,
                "progress": self.indexing.progress,
                "message": self.indexing.message,
                "error": self.indexing.error,
                "started_at": self.indexing.started_at.isoformat() if self.indexing.started_at else None,
                "completed_at": self.indexing.completed_at.isoformat() if self.indexing.completed_at else None,
                "metrics": self.indexing.metrics,
            },
            "current_phase": self.get_current_phase(),
            "overall_progress": self.get_overall_progress(),
            "is_complete": self.is_complete(),
            "has_failure": self.has_failure(),
        }
