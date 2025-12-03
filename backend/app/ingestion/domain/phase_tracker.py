"""
Phase Tracker - Manages phase-level state transitions and persistence
Tracks CRAWLING → CLEANING → CHUNKING → EMBEDDING → INDEXING phases
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class IngestionPhase(str, Enum):
    """Phases of the ingestion process."""
    CRAWLING = "crawling"
    CLEANING = "cleaning"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"


class PhaseStatus(str, Enum):
    """Status of each phase - mirrors job status."""
    PENDING = "pending"  # Waiting for upstream phases or queued items
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PhaseTracker:
    """
    Tracks ingestion phases and their status.
    Manages phase transitions and persistence to database.
    """
    
    # Phase order for validation
    PHASE_ORDER = [
        IngestionPhase.CRAWLING,
        IngestionPhase.CLEANING,
        IngestionPhase.CHUNKING,
        IngestionPhase.EMBEDDING,
        IngestionPhase.INDEXING
    ]
    
    # Progress weights for each phase (total = 100%)
    PHASE_WEIGHTS = {
        IngestionPhase.CRAWLING: 20,
        IngestionPhase.CLEANING: 10,
        IngestionPhase.CHUNKING: 10,
        IngestionPhase.EMBEDDING: 30,
        IngestionPhase.INDEXING: 30,
    }
    
    def __init__(self, job_id: str, kb_id: str):
        """Initialize phase tracker."""
        self.job_id = job_id
        self.kb_id = kb_id
        self.phases: Dict[str, Dict[str, Any]] = {}
        self._initialize_phases()
    
    def _initialize_phases(self):
        """Initialize all phases as pending."""
        for phase in self.PHASE_ORDER:
            self.phases[phase.value] = {
                "status": PhaseStatus.PENDING.value,
                "started_at": None,
                "completed_at": None,
                "progress": 0,
                "items_processed": 0,
                "items_total": 0,
                "error": None
            }
    
    def load_from_dict(self, phase_data: Dict[str, Any]) -> None:
        """Load phase status from dictionary (from database)."""
        if phase_data:
            self.phases.update(phase_data)
            logger.info(f"[PhaseTracker|Job={self.job_id}] Loaded phase data from database")
    
    def start_phase(self, phase: IngestionPhase) -> None:
        """Mark a phase as started."""
        phase_key = phase.value
        
        # Validate phase order
        if not self._can_start_phase(phase):
            prev_phase = self._get_previous_phase(phase)
            raise ValueError(
                f"Cannot start {phase_key}: previous phase {prev_phase.value if prev_phase else 'N/A'} not completed"
            )
        
        self.phases[phase_key]["status"] = PhaseStatus.RUNNING.value
        self.phases[phase_key]["started_at"] = datetime.utcnow().isoformat()
        self.phases[phase_key]["progress"] = 0
        
        logger.info(f"[PhaseTracker|Job={self.job_id}] Phase {phase_key} STARTED")
    
    def update_phase_progress(
        self, 
        phase: IngestionPhase, 
        progress: int, 
        items_processed: Optional[int] = None,
        items_total: Optional[int] = None
    ) -> None:
        """Update phase progress."""
        phase_key = phase.value
        self.phases[phase_key]["progress"] = min(100, max(0, progress))
        
        if items_processed is not None:
            self.phases[phase_key]["items_processed"] = items_processed
        if items_total is not None:
            self.phases[phase_key]["items_total"] = items_total
    
    def complete_phase(self, phase: IngestionPhase, items_processed: Optional[int] = None) -> None:
        """Mark a phase as completed."""
        phase_key = phase.value
        self.phases[phase_key]["status"] = PhaseStatus.COMPLETED.value
        self.phases[phase_key]["completed_at"] = datetime.utcnow().isoformat()
        self.phases[phase_key]["progress"] = 100
        
        if items_processed is not None:
            self.phases[phase_key]["items_processed"] = items_processed
        
        logger.info(
            f"[PhaseTracker|Job={self.job_id}] Phase {phase_key} COMPLETED "
            f"(processed: {self.phases[phase_key]['items_processed']})"
        )
    
    def fail_phase(self, phase: IngestionPhase, error: str) -> None:
        """Mark a phase as failed."""
        phase_key = phase.value
        self.phases[phase_key]["status"] = PhaseStatus.FAILED.value
        self.phases[phase_key]["error"] = error
        self.phases[phase_key]["completed_at"] = datetime.utcnow().isoformat()
        
        logger.error(f"[PhaseTracker|Job={self.job_id}] Phase {phase_key} FAILED: {error}")
    
    def pause_phase(self, phase: IngestionPhase) -> None:
        """Mark a phase as paused."""
        phase_key = phase.value
        if self.phases[phase_key]["status"] == PhaseStatus.RUNNING.value:
            self.phases[phase_key]["status"] = PhaseStatus.PAUSED.value
            logger.info(f"[PhaseTracker|Job={self.job_id}] Phase {phase_key} PAUSED")
    
    def resume_phase(self, phase: IngestionPhase) -> None:
        """Resume a paused phase."""
        phase_key = phase.value
        if self.phases[phase_key]["status"] == PhaseStatus.PAUSED.value:
            self.phases[phase_key]["status"] = PhaseStatus.RUNNING.value
            logger.info(f"[PhaseTracker|Job={self.job_id}] Phase {phase_key} RESUMED")
    
    def cancel_phase(self, phase: IngestionPhase) -> None:
        """Mark a phase as cancelled."""
        phase_key = phase.value
        self.phases[phase_key]["status"] = PhaseStatus.CANCELLED.value
        logger.info(f"[PhaseTracker|Job={self.job_id}] Phase {phase_key} CANCELLED")
    
    def get_current_phase(self) -> Optional[IngestionPhase]:
        """Get the currently running or last incomplete phase."""
        # Find first running phase
        for phase in self.PHASE_ORDER:
            if self.phases[phase.value]["status"] == PhaseStatus.RUNNING.value:
                return phase
        
        # Find first paused phase
        for phase in self.PHASE_ORDER:
            if self.phases[phase.value]["status"] == PhaseStatus.PAUSED.value:
                return phase
        
        # Find first pending/incomplete phase
        for phase in self.PHASE_ORDER:
            status = self.phases[phase.value]["status"]
            if status not in [PhaseStatus.COMPLETED.value, PhaseStatus.FAILED.value, PhaseStatus.CANCELLED.value]:
                return phase
        
        return None
    
    def get_next_phase(self, current_phase: IngestionPhase) -> Optional[IngestionPhase]:
        """Get the next phase in sequence."""
        try:
            current_idx = self.PHASE_ORDER.index(current_phase)
            if current_idx < len(self.PHASE_ORDER) - 1:
                return self.PHASE_ORDER[current_idx + 1]
        except ValueError:
            pass
        return None
    
    def _get_previous_phase(self, phase: IngestionPhase) -> Optional[IngestionPhase]:
        """Get the previous phase in sequence."""
        try:
            idx = self.PHASE_ORDER.index(phase)
            if idx > 0:
                return self.PHASE_ORDER[idx - 1]
        except ValueError:
            pass
        return None
    
    def _can_start_phase(self, phase: IngestionPhase) -> bool:
        """Check if a phase can be started based on previous phase completion."""
        if phase == IngestionPhase.CRAWLING:
            return True  # First phase can always start
        
        prev_phase = self._get_previous_phase(phase)
        if not prev_phase:
            return True
        
        prev_status = self.phases[prev_phase.value]["status"]
        return prev_status == PhaseStatus.COMPLETED.value
    
    def is_phase_completed(self, phase: IngestionPhase) -> bool:
        """Check if a specific phase is completed."""
        return self.phases[phase.value]["status"] == PhaseStatus.COMPLETED.value
    
    def is_phase_failed(self, phase: IngestionPhase) -> bool:
        """Check if a specific phase failed."""
        return self.phases[phase.value]["status"] == PhaseStatus.FAILED.value
    
    def has_any_failed_phase(self) -> bool:
        """Check if any phase has failed."""
        for phase_data in self.phases.values():
            if phase_data["status"] == PhaseStatus.FAILED.value:
                return True
        return False
    
    def get_overall_progress(self) -> int:
        """Calculate overall job progress based on phase completion."""
        total_progress = 0
        
        for phase in self.PHASE_ORDER:
            phase_data = self.phases[phase.value]
            phase_progress = phase_data["progress"]
            weight = self.PHASE_WEIGHTS[phase]
            total_progress += (phase_progress / 100.0) * weight
        
        return int(total_progress)
    
    def get_status_summary(self) -> str:
        """Get a human-readable status summary."""
        current = self.get_current_phase()
        if not current:
            if all(self.is_phase_completed(p) for p in self.PHASE_ORDER):
                return "All phases completed"
            return "No active phase"
        
        phase_data = self.phases[current.value]
        status = phase_data["status"]
        progress = phase_data["progress"]
        
        return f"{current.value.title()}: {status} ({progress}%)"
    
    def to_dict(self) -> Dict[str, Any]:
        """Export phase status as dictionary for persistence."""
        return self.phases.copy()
    
    def get_failed_phase_errors(self) -> Dict[str, str]:
        """Get all failed phases and their error messages."""
        errors = {}
        for phase_key, phase_data in self.phases.items():
            if phase_data["status"] == PhaseStatus.FAILED.value:
                errors[phase_key] = phase_data.get("error", "Unknown error")
        return errors
