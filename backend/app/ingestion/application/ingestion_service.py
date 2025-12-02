"""Main ingestion service orchestrating threaded jobs via interfaces."""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

from app.ingestion.domain.models import IngestionState, JobRuntime
from app.ingestion.domain.enums import JobStatus, transition_or_raise, StateTransitionError
from app.ingestion.domain.errors import RuntimeNotFoundError, InvalidJobStateError
from app.ingestion.infrastructure.repository import DatabaseRepository
from app.ingestion.infrastructure.persistence import LocalDiskPersistenceStore
from app.ingestion.application.lifecycle import LifecycleManager
from app.ingestion.workers import ProducerWorker, ConsumerWorker
from app.ingestion.config import get_settings

logger = logging.getLogger(__name__)


class IngestionService:
    """Singleton service orchestrating threaded ingestion jobs via interfaces."""

    _instance: Optional["IngestionService"] = None

    def __init__(
        self,
        repository: Optional[DatabaseRepository] = None,
        persistence: Optional[LocalDiskPersistenceStore] = None,
        lifecycle: Optional[LifecycleManager] = None,
    ) -> None:
        """
        Initialize ingestion service with dependencies.
        
        Args:
            repository: Job/queue repository (defaults to DatabaseRepository)
            persistence: State persistence store (defaults to LocalDiskPersistenceStore)
            lifecycle: Thread lifecycle manager (defaults to LifecycleManager)
        """
        self.settings = get_settings()
        self.repository = repository or DatabaseRepository()
        self.persistence = persistence or LocalDiskPersistenceStore()
        self.lifecycle = lifecycle or LifecycleManager()
        
        self._runtimes_by_kb: Dict[str, JobRuntime] = {}
        self._runtimes_by_job: Dict[str, JobRuntime] = {}
        self._states: Dict[str, IngestionState] = {}
        self._lock = threading.RLock()

        # Initialize database and recover inflight jobs
        try:
            from app.ingestion.db import init_ingestion_database
            init_ingestion_database()
        except Exception as exc:
            logger.warning(f"Failed to initialize ingestion database: {exc}")
        
        try:
            self.repository.recover_inflight_jobs()
        except Exception as exc:
            logger.warning(f"Failed to recover inflight jobs: {exc}")
        
        # Load persisted states and recover orphaned jobs
        persisted_states = self.persistence.load_all_states()
        for kb_id, state in persisted_states.items():
            # If state shows "running" but no runtime exists, mark as paused
            if state.status == "running":
                logger.info(f"[Recovery] KB {kb_id} shows 'running' status but no active threads - marking as paused")
                state.status = "paused"
                state.paused = True
                state.message = "Job was interrupted (server restart)"
                try:
                    self.persistence.save_state(state)
                    logger.info(f"[Recovery] Updated persisted state for KB {kb_id} to 'paused'")
                except Exception as exc:
                    logger.warning(f"[Recovery] Failed to update state for KB {kb_id}: {exc}")
            self._states[kb_id] = state
        
        if persisted_states:
            logger.info(f"[Recovery] Loaded {len(persisted_states)} persisted KB states")

    @classmethod
    def instance(cls) -> "IngestionService":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = IngestionService()
        return cls._instance

    async def start(
        self,
        kb_id: str,
        run_callable: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> IngestionState:
        """Start fresh ingestion for a knowledge base (first run)."""
        return await asyncio.to_thread(
            self._start_sync,
            kb_id,
            run_callable,
            args,
            kwargs,
        )

    def _start_sync(
        self,
        kb_id: str,
        run_callable: Callable[..., Any],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> IngestionState:
        """Start fresh ingestion (first run)."""
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

            # Extract config from args
            kb_config = self._extract_kb_config(args)
            source_type = kb_config.get("source_type", "website") if kb_config else "website"
            source_config = kb_config.get("source_config", {}) if kb_config else {}
            priority = kb_config.get("priority", 0) if kb_config else 0

            # Create fresh state
            logger.info(f"[IngestionService] KB {kb_id}: Creating fresh state")
            state = IngestionState(kb_id=kb_id, job_id="")
            state.status = JobStatus.RUNNING.value
            state.phase = "crawling"
            state.progress = 0
            state.message = "Ingestion started"
            state.error = None
            state.paused = False
            state.cancel_requested = False
            state.created_at = datetime.utcnow()
            state.started_at = datetime.utcnow()
            
            # Create job record
            logger.info(f"[IngestionService] KB {kb_id}: Creating new job record")
            job_id = self.repository.create_job(kb_id, source_type, source_config, priority)
            logger.info(f"[IngestionService] KB {kb_id}: Created job_id={job_id}")
            state.job_id = job_id

            # Create and start threads
            return self._create_and_start_threads(kb_id, job_id, state, run_callable, args, kwargs)

    async def resume(
        self,
        kb_id: str,
        run_callable: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        """Resume paused ingestion from checkpoint."""
        return await asyncio.to_thread(
            self._resume_sync,
            kb_id,
            run_callable,
            args,
            kwargs,
        )

    def _resume_sync(
        self,
        kb_id: str,
        run_callable: Callable[..., Any],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> bool:
        """Resume ingestion from checkpoint."""
        logger.info(f"[IngestionService] KB {kb_id}: Resuming from checkpoint")
        
        # Check if already running
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if runtime and self.lifecycle.is_running(runtime):
                logger.info(f"[IngestionService] KB {kb_id}: Already running")
                return True
            
            # Clean up stale runtime
            if runtime:
                logger.warning(f"[IngestionService] KB {kb_id}: Cleaning up stale runtime")
                self._cleanup_runtime(kb_id, runtime)
        
        # Load checkpoint state
        state = self.status(kb_id)
        if not state:
            logger.error(f"[IngestionService] KB {kb_id}: No checkpoint found")
            return False
        
        if state.status not in (JobStatus.PAUSED.value, JobStatus.RUNNING.value):
            logger.error(f"[IngestionService] KB {kb_id}: Invalid status for resume: {state.status}")
            return False
        
        with self._lock:
            # Validate and update state for resume
            try:
                current_status = JobStatus(state.status)
                transition_or_raise(current_status, JobStatus.RUNNING)
            except (ValueError, StateTransitionError) as exc:
                logger.error(f"[IngestionService] KB {kb_id}: Invalid transition: {exc}")
                return False
            
            state.status = JobStatus.RUNNING.value
            state.paused = False
            state.cancel_requested = False
            state.error = None
            state.message = "Resumed from checkpoint"
            
            # Update job record
            if state.job_id:
                self.repository.update_job_status(state.job_id, JobStatus.RUNNING.value)
                job_id = state.job_id
            else:
                logger.error(f"[IngestionService] KB {kb_id}: No job_id in checkpoint")
                return False
            
            # Create and start threads
            new_state = self._create_and_start_threads(kb_id, job_id, state, run_callable, args, kwargs)
            return new_state is not None

    async def pause(self, kb_id: str) -> bool:
        """Pause = graceful stop. Threads exit after current work, state saved as 'paused'."""
        return await asyncio.to_thread(self._pause_sync, kb_id)

    def _pause_sync(self, kb_id: str) -> bool:
        """Pause ingestion gracefully."""
        logger.info(f"[IngestionService] KB {kb_id}: Starting pause (graceful stop)")
        
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if not runtime:
                # Check if there's a persisted state that's already paused or completed
                state = self._states.get(kb_id) or self.persistence.load(kb_id)
                if state and state.status in [JobStatus.PAUSED.value, JobStatus.COMPLETED.value, JobStatus.FAILED.value, JobStatus.CANCELED.value]:
                    logger.info(f"[IngestionService] KB {kb_id}: Already in {state.status} state")
                    return True
                logger.warning(f"[IngestionService] KB {kb_id}: No runtime found and no pausable state")
                return False

            state = runtime.state
            
            # Validate transition
            try:
                current_status = JobStatus(state.status)
                transition_or_raise(current_status, JobStatus.PAUSED)
            except (ValueError, StateTransitionError) as exc:
                logger.warning(f"[IngestionService] KB {kb_id}: Cannot pause: {exc}")
                return False

            # Signal threads to stop gracefully
            logger.info(f"[IngestionService] KB {kb_id}: Signaling threads to stop")
            state.paused = True
            state.message = "Pausing - waiting for threads to finish"
            self.persistence.save_state(state)
        
        # Wait for threads to exit (outside lock)
        logger.info(f"[IngestionService] KB {kb_id}: Waiting for threads to exit")
        self.lifecycle.stop_threads(runtime)
        
        # Update state after threads exited
        with self._lock:
            state.status = JobStatus.PAUSED.value
            state.message = "Paused - checkpoint saved"
            self.repository.update_job_status(runtime.job_id, JobStatus.PAUSED.value)
            self.persistence.save_state(state)
            
            # Clean up runtime from memory
            self._cleanup_runtime(kb_id, runtime)
        
        logger.info(f"[IngestionService] KB {kb_id}: Pause complete")
        return True

    async def cancel(self, kb_id: str) -> bool:
        """Cancel ingestion immediately."""
        return await asyncio.to_thread(self._cancel_sync, kb_id)

    def _cancel_sync(self, kb_id: str) -> bool:
        """Cancel ingestion."""
        logger.info(f"[IngestionService] KB {kb_id}: Cancelling")
        
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if not runtime:
                return False

            state = runtime.state
            state.cancel_requested = True
            state.status = JobStatus.CANCELED.value
            state.phase = "cancelled"
            state.message = "Cancellation requested"
            self.repository.update_job_status(runtime.job_id, JobStatus.CANCELED.value)
            self.persistence.save_state(state)

        self.lifecycle.stop_threads(runtime)
        
        with self._lock:
            self._cleanup_runtime(kb_id, runtime)
        
        return True

    def status(self, kb_id: str) -> Optional[IngestionState]:
        """Get ingestion status for a knowledge base."""
        with self._lock:
            state = self._states.get(kb_id)
            if state:
                return state

        # Fallback to persisted state (for paused/stopped jobs)
        persisted = self.persistence.load(kb_id)
        if persisted:
            with self._lock:
                self._states[kb_id] = persisted
            return persisted

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

    async def cancel_all(self) -> None:
        """Cancel all running jobs."""
        await asyncio.to_thread(self._cancel_all_sync)

    def _cancel_all_sync(self) -> None:
        """Cancel all jobs synchronously."""
        with self._lock:
            kb_ids = list(self._runtimes_by_kb.keys())
        for kb_id in kb_ids:
            try:
                self._cancel_sync(kb_id)
            except Exception as exc:
                logger.error(f"Failed to cancel KB {kb_id}: {exc}")

    async def pause_all(self) -> None:
        """Pause all running jobs."""
        await asyncio.to_thread(self._pause_all_sync)

    def _pause_all_sync(self) -> None:
        """Pause all jobs synchronously."""
        with self._lock:
            kb_ids = list(self._runtimes_by_kb.keys())
        for kb_id in kb_ids:
            try:
                self._pause_sync(kb_id)
            except Exception as exc:
                logger.error(f"Failed to pause KB {kb_id}: {exc}")

    def _create_and_start_threads(
        self,
        kb_id: str,
        job_id: str,
        state: IngestionState,
        run_callable: Callable[..., Any],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> IngestionState:
        """Create runtime and start threads."""
        # Create runtime via lifecycle manager
        producer_kwargs = dict(kwargs)
        producer_kwargs.setdefault("state", state)
        
        runtime = self.lifecycle.create_runtime(
            job_id=job_id,
            kb_id=kb_id,
            state=state,
            producer_target=run_callable,
            producer_args=args,
            producer_kwargs=producer_kwargs,
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
        self.persistence.save_state(state)
        return state

    def _cleanup_runtime(self, kb_id: str, runtime: JobRuntime) -> None:
        """Clean up runtime from memory."""
        if kb_id in self._runtimes_by_kb:
            del self._runtimes_by_kb[kb_id]
        if runtime.job_id in self._runtimes_by_job:
            del self._runtimes_by_job[runtime.job_id]

    def _extract_kb_config(self, args: Tuple[Any, ...]) -> Optional[Dict[str, Any]]:
        """Extract KB config from args (first arg should be kb_config dict)."""
        if args and isinstance(args[0], dict):
            return args[0]
        return None
