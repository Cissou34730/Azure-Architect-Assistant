"""Producer worker thread - handles crawling, chunking, and enqueueing."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Dict, Tuple

from app.ingestion.models import JobStatus
from .repository import update_job_status
from .runtime import JobRuntime
from .storage import persist_state

logger = logging.getLogger(__name__)


class ProducerWorker:
    """Worker that runs the producer pipeline in a separate thread."""

    @staticmethod
    def run(runtime: JobRuntime) -> None:
        """
        Producer thread entry point.
        
        Executes the ingestion pipeline (crawl → chunk → enqueue).
        Updates state and handles errors.
        Sets stop_event when done.
        """
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

            # Execute the pipeline (async function in new event loop)
            asyncio.run(ProducerWorker._execute(runtime))
            
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
            # Signal consumer to stop (no more work coming)
            runtime.stop_event.set()
            
            # If not failed/cancelled, mark as completed
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

    @staticmethod
    async def _execute(runtime: JobRuntime) -> None:
        """
        Execute the producer pipeline function.
        
        Handles both sync and async callables.
        """
        target = runtime.producer_target
        args = runtime.producer_args
        kwargs = runtime.producer_kwargs

        if asyncio.iscoroutinefunction(target):
            await target(*args, **kwargs)
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: target(*args, **kwargs))
