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
        state_override: Optional[IngestionState] = None,
        **kwargs: Any,
    ) -> IngestionState:
        """Start threaded ingestion for a knowledge base."""

        return await asyncio.to_thread(
            self._start_sync,
            kb_id,
            run_callable,
            args,
            kwargs,
            state_override,
        )

    def _start_sync(
        self,
        kb_id: str,
        run_callable: Callable[..., Any],
        args: Tuple[Any, ...],
        kwargs: Dict[str, Any],
        state_override: Optional[IngestionState],
    ) -> IngestionState:
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if runtime and runtime.producer_thread and runtime.producer_thread.is_alive():
                return runtime.state

            kb_config = self._extract_kb_config(args)
            source_type = kb_config.get("source_type", "website") if kb_config else "website"
            source_config = kb_config.get("source_config", {}) if kb_config else {}
            priority = kb_config.get("priority", 0) if kb_config else 0

            state = state_override or IngestionState(kb_id=kb_id, job_id="")
            state.status = "running"
            state.phase = "crawling"
            state.progress = 0
            state.message = "Ingestion started"
            state.error = None
            state.paused = False
            state.cancel_requested = False
            if state.created_at is None:
                state.created_at = datetime.utcnow()
            state.started_at = datetime.utcnow()

            job_id = create_job_record(kb_id, source_type, source_config, priority)
            state.job_id = job_id
            runtime = JobRuntime(job_id=job_id, kb_id=kb_id, state=state)
            runtime.producer_target = run_callable
            runtime.producer_args = args
            producer_kwargs = dict(kwargs)
            producer_kwargs.setdefault("state", state)
            runtime.producer_kwargs = producer_kwargs

            runtime.consumer_target = self._noop_consumer

            producer_thread = threading.Thread(
                target=self._run_producer,
                args=(runtime,),
                name=f"ingest:{kb_id}:producer",
                daemon=True,
            )
            consumer_thread = threading.Thread(
                target=self._run_consumer,
                args=(runtime,),
                name=f"ingest:{kb_id}:consumer",
                daemon=True,
            )

            runtime.producer_thread = producer_thread
            runtime.consumer_thread = consumer_thread

            self._runtimes_by_kb[kb_id] = runtime
            self._runtimes_by_job[job_id] = runtime
            self._states[kb_id] = state

            producer_thread.start()
            consumer_thread.start()

            persist_state(state)
            return state

    async def pause(self, kb_id: str) -> bool:
        return await asyncio.to_thread(self._pause_sync, kb_id)

    def _pause_sync(self, kb_id: str) -> bool:
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if not runtime:
                return False

            state = runtime.state
            if state.status != "running":
                return False

            state.status = "paused"
            state.paused = True
            state.message = "Paused by user"
            runtime.pause_event.set()
            update_job_status(runtime.job_id, JobStatus.PAUSED)
            persist_state(state)
            return True

    async def resume(self, kb_id: str) -> bool:
        return await asyncio.to_thread(self._resume_sync, kb_id)

    def _resume_sync(self, kb_id: str) -> bool:
        with self._lock:
            runtime = self._runtimes_by_kb.get(kb_id)
            if not runtime:
                return False

            state = runtime.state
            if state.status != "paused":
                return False

            # Clear paused state
            state.status = "running"
            state.paused = False
            state.message = "Resumed by user"
            runtime.pause_event.clear()
            update_job_status(runtime.job_id, JobStatus.RUNNING)

            # If the producer thread already exited (e.g., crawler returned on pause),
            # restart the producer to resume crawling from the saved checkpoint.
            producer_dead = not runtime.producer_thread or not runtime.producer_thread.is_alive()
            if producer_dead and runtime.producer_target:
                try:
                    producer_thread = threading.Thread(
                        target=self._run_producer,
                        args=(runtime,),
                        name=f"ingest:{kb_id}:producer",
                        daemon=True,
                    )
                    runtime.producer_thread = producer_thread
                    producer_thread.start()
                    # Ensure consumer exists too
                    if not runtime.consumer_thread or not runtime.consumer_thread.is_alive():
                        consumer_thread = threading.Thread(
                            target=self._run_consumer,
                            args=(runtime,),
                            name=f"ingest:{kb_id}:consumer",
                            daemon=True,
                        )
                        runtime.consumer_thread = consumer_thread
                        consumer_thread.start()
                    state.message = "Resumed: crawling restarted from checkpoint"
                except Exception as exc:
                    logger.error("Failed to restart producer for KB %s: %s", kb_id, exc, exc_info=True)
                    state.message = "Resume failed to restart producer"

            persist_state(state)
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
            runtime.pause_event.clear()
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

    async def resume_or_start(
        self,
        kb_id: str,
        run_callable: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> bool:
        state = self.status(kb_id)
        if state and state.status == "paused":
            return await self.resume(kb_id)

        new_state = await self.start(kb_id, run_callable, *args, **kwargs)
        return new_state is not None

    def load_all_states(self) -> None:
        recover_inflight_jobs()
        with self._lock:
            self._states = load_states_from_disk()

    def _run_producer(self, runtime: JobRuntime) -> None:
        state = runtime.state
        try:
            logger.info("Starting producer thread for KB %s", runtime.kb_id)
            if runtime.producer_target is None:
                logger.warning(
                    "Producer target not assigned for job %s (KB %s)",
                    runtime.job_id,
                    runtime.kb_id,
                )
                return

            asyncio.run(self._execute_producer(runtime))
        except Exception as exc:
            logger.error(
                "Producer thread failed for KB %s: %s",
                runtime.kb_id,
                exc,
                exc_info=True,
            )
            state.status = "failed"
            state.phase = "failed"
            state.error = str(exc)
            state.message = "Ingestion failed"
            state.completed_at = datetime.utcnow()
            update_job_status(runtime.job_id, JobStatus.FAILED)
            persist_state(state)
        finally:
            runtime.stop_event.set()
            if (
                state.status not in {"failed", "cancelled"}
                and state.error is None
                and not state.cancel_requested
            ):
                state.status = "completed"
                state.phase = "completed"
                state.progress = 100
                state.message = "Ingestion completed"
                state.completed_at = datetime.utcnow()
                update_job_status(runtime.job_id, JobStatus.COMPLETED)
                persist_state(state)
            logger.info("Producer thread finished for KB %s", runtime.kb_id)

    async def _execute_producer(self, runtime: JobRuntime) -> None:
        target = runtime.producer_target
        args = runtime.producer_args
        kwargs = runtime.producer_kwargs

        if asyncio.iscoroutinefunction(target):
            await target(*args, **kwargs)
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: target(*args, **kwargs))

    def _run_consumer(self, runtime: JobRuntime) -> None:
        logger.info("Starting consumer placeholder thread for KB %s", runtime.kb_id)
        stop_event = runtime.stop_event
        pause_event = runtime.pause_event

        while not stop_event.is_set():
            if pause_event.is_set():
                stop_event.wait(timeout=0.5)
            else:
                stop_event.wait(timeout=0.5)

        logger.info("Consumer placeholder thread exiting for KB %s", runtime.kb_id)

    def _noop_consumer(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def _join_threads(self, runtime: JobRuntime, timeout: float = 5.0) -> None:
        if runtime.producer_thread and runtime.producer_thread.is_alive():
            runtime.producer_thread.join(timeout=timeout)
        if runtime.consumer_thread and runtime.consumer_thread.is_alive():
            runtime.consumer_thread.join(timeout=timeout)

    def _extract_kb_config(self, args: Tuple[Any, ...]) -> Dict[str, Any]:
        for value in args:
            if isinstance(value, dict) and value.get("id"):
                return value
        return {}
