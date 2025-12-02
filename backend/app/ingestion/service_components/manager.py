"""Threaded ingestion manager coordinating producer and consumer workers."""

from __future__ import annotations

import asyncio
import logging
import threading
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

from app.ingestion.models import JobStatus
from .repository import (
    create_job_record,
    get_latest_job_record,
    job_to_state,
    recover_inflight_jobs,
    update_job_status,
)
from .runtime import JobRuntime
from .state import IngestionState
from .storage import load_states_from_disk, persist_state
from .producer import ProducerWorker
from .consumer import ConsumerWorker

logger = logging.getLogger(__name__)


class IngestionService:
    """Singleton manager orchestrating threaded ingestion jobs."""

    _instance: Optional["IngestionService"] = None

    def __init__(self) -> None:
        self._runtimes_by_kb: Dict[str, JobRuntime] = {}
        self._runtimes_by_job: Dict[str, JobRuntime] = {}
        self._states: Dict[str, IngestionState] = {}
        self._lock = threading.RLock()

        try:
            from app.ingestion.db import init_ingestion_database
            init_ingestion_database()
        except Exception:
            pass
        try:
            recover_inflight_jobs()
        except Exception:
            pass
        self._states.update(load_states_from_disk())

    @classmethod
    def instance(cls) -> "IngestionService":
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
        logger.info(f"[_start_sync] KB {kb_id}: Starting fresh ingestion")
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if runtime:
                producer_alive = runtime.producer_thread and runtime.producer_thread.is_alive()
                if producer_alive:
                    logger.info(f"[_start_sync] KB {kb_id}: Already running")
                    return runtime.state
                
                # Clean up stale runtime
                logger.warning(f"[_start_sync] KB {kb_id}: Cleaning up stale runtime")
                del self._runtimes_by_kb[kb_id]
                if runtime.job_id in self._runtimes_by_job:
                    del self._runtimes_by_job[runtime.job_id]

            kb_config = self._extract_kb_config(args)
            source_type = kb_config.get("source_type", "website") if kb_config else "website"
            source_config = kb_config.get("source_config", {}) if kb_config else {}
            priority = kb_config.get("priority", 0) if kb_config else 0

            # Create fresh state
            logger.info(f"[_start_sync] KB {kb_id}: Creating fresh state")
            state = IngestionState(kb_id=kb_id, job_id="")
            state.status = "running"
            state.phase = "crawling"
            state.progress = 0
            state.message = "Ingestion started"
            state.error = None
            state.paused = False
            state.cancel_requested = False
            state.created_at = datetime.utcnow()
            state.started_at = datetime.utcnow()
            
            logger.info(f"[_start_sync] KB {kb_id}: Creating new job record")
            job_id = create_job_record(kb_id, source_type, source_config, priority)
            logger.info(f"[_start_sync] KB {kb_id}: Created job_id={job_id}")
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
        logger.info(f"[_resume_sync] KB {kb_id}: Resuming from checkpoint")
        
        # Check if already running
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if runtime:
                producer_alive = runtime.producer_thread and runtime.producer_thread.is_alive()
                if producer_alive:
                    logger.info(f"[_resume_sync] KB {kb_id}: Already running")
                    return True
                
                # Clean up stale runtime
                logger.warning(f"[_resume_sync] KB {kb_id}: Cleaning up stale runtime")
                del self._runtimes_by_kb[kb_id]
                if runtime.job_id in self._runtimes_by_job:
                    del self._runtimes_by_job[runtime.job_id]
        
        # Load checkpoint state
        state = self.status(kb_id)
        if not state:
            logger.error(f"[_resume_sync] KB {kb_id}: No checkpoint found")
            return False
        
        if state.status not in ("paused", "running"):
            logger.error(f"[_resume_sync] KB {kb_id}: Invalid status for resume: {state.status}")
            return False
        
        with self._lock:
            # Update state for resume
            state.status = "running"
            state.paused = False
            state.cancel_requested = False
            state.error = None
            state.message = "Resumed from checkpoint"
            
            # Update job record
            if state.job_id:
                update_job_status(state.job_id, JobStatus.RUNNING)
                job_id = state.job_id
            else:
                logger.error(f"[_resume_sync] KB {kb_id}: No job_id in checkpoint")
                return False
            
            # Create and start threads
            new_state = self._create_and_start_threads(kb_id, job_id, state, run_callable, args, kwargs)
            return new_state is not None

    async def pause(self, kb_id: str) -> bool:
        return await asyncio.to_thread(self._pause_sync, kb_id)

    def _pause_sync(self, kb_id: str) -> bool:
        """Pause = graceful stop. Threads exit after current work, state saved as 'paused'."""
        logger.info(f"[_pause_sync] KB {kb_id}: Starting pause (graceful stop)")
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if not runtime:
                logger.warning(f"[_pause_sync] KB {kb_id}: No runtime found")
                return False

            state = runtime.state
            if state.status != "running":
                logger.warning(f"[_pause_sync] KB {kb_id}: Status is {state.status}, not running")
                return False

            # Signal threads to stop gracefully
            logger.info(f"[_pause_sync] KB {kb_id}: Setting stop_event")
            runtime.stop_event.set()
            state.paused = True
            state.message = "Pausing - waiting for threads to finish"
            persist_state(state)
        
        # Wait for threads to exit (outside lock)
        logger.info(f"[_pause_sync] KB {kb_id}: Waiting for threads to exit")
        self._join_threads(runtime)
        
        # Update state after threads exited
        with self._lock:
            state.status = "paused"
            state.message = "Paused - checkpoint saved"
            update_job_status(runtime.job_id, JobStatus.PAUSED)
            persist_state(state)
            # Clean up runtime from memory
            if kb_id in self._runtimes_by_kb:
                del self._runtimes_by_kb[kb_id]
            if runtime.job_id in self._runtimes_by_job:
                del self._runtimes_by_job[runtime.job_id]
        
        logger.info(f"[_pause_sync] KB {kb_id}: Pause complete, threads exited, runtime cleaned up")
        return True

    async def cancel(self, kb_id: str) -> bool:
        return await asyncio.to_thread(self._cancel_sync, kb_id)

    def _cancel_sync(self, kb_id: str) -> bool:
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if not runtime:
                return False

            state = runtime.state
            state.cancel_requested = True
            state.status = "cancelled"
            state.phase = "cancelled"
            state.message = "Cancellation requested"
            runtime.stop_event.set()
            update_job_status(runtime.job_id, JobStatus.CANCELED)
            persist_state(state)

        self._join_threads(runtime)
        return True

    def status(self, kb_id: str) -> Optional[IngestionState]:
        with self._lock:
            state = self._states.get(kb_id)
            if state:
                return state

        job = get_latest_job_record(kb_id)
        if job:
            return job_to_state(job)
        return None

    def list_kb_states(self) -> Dict[str, IngestionState]:
        with self._lock:
            return dict(self._states)

    async def cancel_all(self) -> None:
        await asyncio.to_thread(self._cancel_all_sync)

    def _cancel_all_sync(self) -> None:
        with self._lock:
            runtimes = list(self._runtimes_by_kb.values())
        for runtime in runtimes:
            self._cancel_sync(runtime.kb_id)

    async def pause_all(self) -> None:
        await asyncio.to_thread(self._pause_all_sync)

    def _pause_all_sync(self) -> None:
        with self._lock:
            runtimes = list(self._runtimes_by_kb.values())
        for runtime in runtimes:
            try:
                self._pause_sync(runtime.kb_id)
            except Exception:
                pass

    def _create_and_start_threads(
        self,
        kb_id: str,
        job_id: str,
        state: IngestionState,
        run_callable: Callable[..., Any],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
    ) -> IngestionState:
        """Common logic to create runtime and start threads (called by start and resume)."""
        runtime = JobRuntime(job_id=job_id, kb_id=kb_id, state=state)
        runtime.producer_target = run_callable
        runtime.producer_args = args
        producer_kwargs = dict(kwargs)
        producer_kwargs.setdefault("state", state)
        runtime.producer_kwargs = producer_kwargs

        # Create threads
        producer_thread = threading.Thread(
            target=ProducerWorker.run,
            args=(runtime,),
            name=f"ingest:{kb_id}:producer",
            daemon=True,
        )
        consumer_thread = threading.Thread(
            target=ConsumerWorker.run,
            args=(runtime,),
            name=f"ingest:{kb_id}:consumer",
            daemon=True,
        )

        runtime.producer_thread = producer_thread
        runtime.consumer_thread = consumer_thread

        self._runtimes_by_kb[kb_id] = runtime
        self._runtimes_by_job[job_id] = runtime
        self._states[kb_id] = state

        logger.info(f"[_create_and_start_threads] KB {kb_id}: Starting threads")
        producer_thread.start()
        consumer_thread.start()

        persist_state(state)
        return state

    def load_all_states(self) -> None:
        recover_inflight_jobs()
        with self._lock:
            self._states = load_states_from_disk()

    def _join_threads(self, runtime: JobRuntime, timeout: float = 5.0) -> None:
        """Wait for both producer and consumer threads to exit."""
        if runtime.producer_thread and runtime.producer_thread.is_alive():
            runtime.producer_thread.join(timeout=timeout)
        if runtime.consumer_thread and runtime.consumer_thread.is_alive():
            runtime.consumer_thread.join(timeout=timeout)

    def _extract_kb_config(self, args: Tuple[Any, ...]) -> Optional[Dict[str, Any]]:
        """Extract KB config from args (first arg should be kb_config dict)."""
        if args and isinstance(args[0], dict):
            return args[0]
        return None
