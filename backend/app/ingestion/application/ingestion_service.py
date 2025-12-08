"""Main ingestion service orchestrating threaded jobs via interfaces."""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime
from typing import Any, Dict, Optional

from app.ingestion.domain.models import IngestionState, JobRuntime
# TODO: Rebuild status logic from PhaseStatus aggregation
# from app.ingestion.domain.enums import JobStatus, transition_or_raise, StateTransitionError
from app.ingestion.domain.errors import RuntimeNotFoundError, InvalidJobStateError
from app.ingestion.infrastructure.repository import DatabaseRepository
from app.ingestion.application.phase_tracker import PhaseTracker
from app.ingestion.application.lifecycle import LifecycleManager
from app.ingestion.workers import ProducerWorker, ConsumerWorker
from config import get_settings

logger = logging.getLogger(__name__)


class IngestionService:
    """Singleton service orchestrating threaded ingestion jobs via interfaces."""

    _instance: Optional["IngestionService"] = None

    def __init__(
        self,
        repository: Optional[DatabaseRepository] = None,
        lifecycle: Optional[LifecycleManager] = None,
    ) -> None:
        """
        Initialize ingestion service with dependencies.
        
        Args:
            repository: Job/queue repository (defaults to DatabaseRepository)
            lifecycle: Thread lifecycle manager (defaults to LifecycleManager)
        """
        self.settings = get_settings()
        self.repository = repository or DatabaseRepository()
        self.lifecycle = lifecycle or LifecycleManager()
        self.phase_tracker = PhaseTracker(self.repository)
        
        self._runtimes_by_kb: Dict[str, JobRuntime] = {}
        self._runtimes_by_job: Dict[str, JobRuntime] = {}
        self._states: Dict[str, IngestionState] = {}
        self._lock = threading.RLock()

        # Initialize database and recover inflight jobs
        try:
            from app.ingestion.ingestion_database import init_ingestion_database
            init_ingestion_database()
        except Exception as exc:
            logger.warning(f"Failed to initialize ingestion database: {exc}")
        
        try:
            self.repository.recover_inflight_jobs()
        except Exception as exc:
            logger.warning(f"Failed to recover inflight jobs: {exc}")

    @classmethod
    def instance(cls) -> "IngestionService":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = IngestionService()
        return cls._instance

    async def start(
        self,
        kb_id: str,
        kb_config: Dict[str, Any],
    ) -> IngestionState:
        """
        Start fresh ingestion for a knowledge base (first run).
        
        Args:
            kb_id: Knowledge base identifier
            kb_config: KB configuration dict
            
        Returns:
            IngestionState of the started job
        """
        return await asyncio.to_thread(
            self._start_sync,
            kb_id,
            kb_config,
        )

    def _start_sync(
        self,
        kb_id: str,
        kb_config: Dict[str, Any],
    ) -> IngestionState:
        """
        Start fresh ingestion (first run).
        
        Args:
            kb_id: Knowledge base identifier
            kb_config: KB configuration dict
            
        Returns:
            IngestionState of the started job
        """
        logger.info(f"[IngestionService] KB {kb_id}: Starting fresh ingestion")
        
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if runtime and self.lifecycle.is_running(runtime):
                logger.info(f"[IngestionService] KB {kb_id}: Already running")
                return runtime.state
            
            # Clean up stale runtime
            if runtime:
                logger.warning(f"[IngestionService] KB {kb_id}: Cleaning up stale runtime")
                self._cleanup_runtime(kb_id, runtime)

            # Extract config
            from config.settings import get_kb_defaults
            defaults = get_kb_defaults()
            merged = defaults.merge_with_kb_config(kb_config)
            
            source_type = kb_config["source_type"]  # Must come from user's KB config
            source_config = kb_config.get("source_config", {})
            priority = kb_config.get("priority", 0)

            # Create fresh state
            logger.info(f"[IngestionService] KB {kb_id}: Creating fresh state")
            state = IngestionState(kb_id=kb_id, job_id="")
            # Initialize via helper to keep invariants consistent
            state.created_at = datetime.utcnow()
            state.started_at = datetime.utcnow()
            self._set_running(state, phase="crawling", message="Ingestion started")
            
            # Create job record
            logger.info(f"[IngestionService] KB {kb_id}: Creating new job record")
            job_id = self.repository.create_job(kb_id, source_type, source_config, priority)
            logger.info(f"[IngestionService] KB {kb_id}: Created job_id={job_id}")
            state.job_id = job_id

            # Initialize phases via tracker (NOT_STARTED for all)
            self.phase_tracker.initialize_phases(job_id)
            # Mark first phase as RUNNING (loading/crawling)
            self.phase_tracker.start_phase(job_id, "loading")

            # Create and start threads with kb_config
            return self._create_and_start_threads(kb_id, job_id, state, kb_config)



    def status(self, kb_id: str) -> Optional[IngestionState]:
        """Get ingestion status for a knowledge base."""
        with self._lock:
            state = self._states.get(kb_id)
            if state:
                return state

        # Fallback to repository
        state = self.repository.get_latest_job(kb_id)
        if state:
            with self._lock:
                self._states[kb_id] = state
        return state

    def list_kb_states(self) -> Dict[str, IngestionState]:
        """List all KB states."""
        with self._lock:
            return dict(self._states)

    # -------------------------
    # Phase 6 Controls
    # -------------------------
    def pause(self, kb_id: str) -> None:
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if not runtime:
                raise RuntimeNotFoundError(f"No runtime for KB {kb_id}")
        self.lifecycle.request_pause(runtime)

    def resume(self, kb_id: str) -> None:
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if not runtime:
                raise RuntimeNotFoundError(f"No runtime for KB {kb_id}")
        self.lifecycle.request_resume(runtime)

    def cancel(self, kb_id: str) -> None:
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if not runtime:
                raise RuntimeNotFoundError(f"No runtime for KB {kb_id}")
        self.lifecycle.request_cancel(runtime)







    def _create_and_start_threads(
        self,
        kb_id: str,
        job_id: str,
        state: IngestionState,
        kb_config: Dict[str, Any],
    ) -> IngestionState:
        """
        Create runtime and start threads.
        
        Args:
            kb_id: Knowledge base identifier
            job_id: Job identifier
            state: IngestionState
            kb_config: KB configuration dict
            
        Returns:
            IngestionState with updated runtime info
        """
        # Create runtime via lifecycle manager
        runtime = self.lifecycle.create_runtime(
            job_id=job_id,
            kb_id=kb_id,
            state=state,
            producer_target=None,  # Not used - workers know what to do
            producer_args=(kb_config,),
            producer_kwargs={"state": state},
        )

        # Register runtime
        self._runtimes_by_kb[kb_id] = runtime
        self._runtimes_by_job[job_id] = runtime
        self._states[kb_id] = state

        # Start threads via lifecycle manager
        self.lifecycle.start_threads(
            runtime,
            ProducerWorker.run,
            ConsumerWorker.run,
        )

        # Persist initial state
        # Start threads via lifecycle manager
        self.lifecycle.start_threads(
            runtime,
            ProducerWorker.run,
            ConsumerWorker.run,
        )

        return state
    # ---------------------------------------------------------------------
    # State helpers: single source of truth for status/flags
    # ---------------------------------------------------------------------
    def _set_running(self, state: IngestionState, *, phase: Optional[str] = None, message: Optional[str] = None) -> None:
        """Mark state as running."""
        # TODO: Rebuild - use PhaseStatus aggregation instead
        state.status = "running"  # JobStatus.RUNNING.value
        if phase:
            state.phase = phase
        state.error = None
        if message is not None:
            state.message = message

    def _set_failed(self, state: IngestionState, *, error_message: str) -> None:
        """Mark state failed with error message."""
        # TODO: Rebuild - use PhaseStatus aggregation instead
        state.status = "failed"  # JobStatus.FAILED.value
        state.error = error_message
        state.message = error_message

    def _set_completed(self, state: IngestionState, *, message: Optional[str] = "Completed") -> None:
        """Mark state completed."""
        # TODO: Rebuild - use PhaseStatus aggregation instead
        state.status = "completed"  # JobStatus.COMPLETED.value
        if message is not None:
            state.message = message
