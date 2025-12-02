"""Producer worker - crawls, chunks, and enqueues documents."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from app.ingestion.domain.models import JobRuntime
from app.ingestion.domain.enums import JobStatus
from app.ingestion.config import get_settings

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
        settings = get_settings()
        state = runtime.state
        
        # Add correlation ID to logger
        kb_id = runtime.kb_id
        job_id = runtime.job_id
        log_prefix = f"[Producer|KB={kb_id}|Job={job_id}]"
        
        try:
            logger.info(f"{log_prefix} Starting producer thread")
            
            if runtime.producer_target is None:
                logger.warning(f"{log_prefix} Producer target not assigned")
                return

            # Execute the pipeline (async function in new event loop)
            asyncio.run(ProducerWorker._execute(runtime, log_prefix))
            
        except Exception as exc:
            logger.error(
                f"{log_prefix} Producer thread failed: {exc}",
                exc_info=True,
            )
            state.status = JobStatus.FAILED.value
            state.phase = "failed"
            state.error = str(exc)
            state.message = "Ingestion failed"
            state.completed_at = datetime.utcnow()
            
            # Repository update handled by service layer
            
        finally:
            # Signal consumer to stop (no more work coming)
            runtime.stop_event.set()
            
            # If not failed/cancelled, mark as completed
            if (
                state.status not in {JobStatus.FAILED.value, JobStatus.CANCELED.value}
                and state.error is None
                and not state.cancel_requested
            ):
                state.status = JobStatus.COMPLETED.value
                state.phase = "completed"
                state.progress = 100
                state.message = "Ingestion completed"
                state.completed_at = datetime.utcnow()
                
            logger.info(f"{log_prefix} Producer thread finished")

    @staticmethod
    async def _execute(runtime: JobRuntime, log_prefix: str) -> None:
        """
        Execute the producer pipeline function.
        
        Handles both sync and async callables.
        """
        target = runtime.producer_target
        args = runtime.producer_args
        kwargs = runtime.producer_kwargs

        logger.info(f"{log_prefix} Executing producer target")
        
        if asyncio.iscoroutinefunction(target):
            await target(*args, **kwargs)
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, lambda: target(*args, **kwargs))
