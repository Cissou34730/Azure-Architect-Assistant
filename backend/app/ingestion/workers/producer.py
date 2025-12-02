"""Producer worker - crawls, chunks, and enqueues documents."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from app.ingestion.domain.models import JobRuntime
from app.ingestion.domain.enums import JobStatus
from app.ingestion.config import get_settings
from .producer_pipeline import ProducerPipeline

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
            
            # Extract KB config from args
            kb_config = ProducerWorker._extract_kb_config(runtime.producer_args)
            
            # Create and run producer pipeline
            pipeline = ProducerPipeline(kb_config, state)
            asyncio.run(pipeline.run())
            
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
            
        finally:
            # Signal consumer to stop (no more work coming)
            runtime.stop_event.set()
            
            # DO NOT mark as completed here - consumer will do that after finishing all work
            # Producer only handles crawl/chunk/enqueue phase
            if state.status not in {JobStatus.FAILED.value, JobStatus.CANCELED.value}:
                state.phase = "embedding"
                state.message = "Crawling complete, processing chunks..."
                logger.info(f"{log_prefix} Producer finished - consumer will continue processing queue")
                
            logger.info(f"{log_prefix} Producer thread finished")

    @staticmethod
    def _extract_kb_config(args) -> dict:
        """Extract KB config dict from producer args tuple."""
        for value in args:
            if isinstance(value, dict) and value.get("id"):
                return value
        return {}
