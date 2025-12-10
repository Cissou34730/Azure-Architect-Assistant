"""
Producer worker - crawls, chunks, and enqueues documents.

.. deprecated:: 2025-12-10
    This producer/consumer worker pattern is deprecated. Use the orchestrator-based
    implementation with `/ingestion/v2/jobs` API instead.
    See docs/ingestion/LEGACY_DEPRECATION.md for migration guide.
"""

from __future__ import annotations

import asyncio
import logging
import warnings
from datetime import datetime
from typing import Any

from app.ingestion.domain.models import JobRuntime
# TODO: Rebuild status management
# from app.ingestion.domain.enums import JobStatus
from config import get_settings
from app.ingestion.application.producer_pipeline import ProducerPipeline
from app.ingestion.application.phase_tracker import PhaseTracker
from app.ingestion.infrastructure.repository import DatabaseRepository

logger = logging.getLogger(__name__)


class ProducerWorker:
    """
    Worker that runs the producer pipeline in a separate thread.
    
    .. deprecated:: 2025-12-10
        Use `IngestionOrchestrator` with `/ingestion/v2/jobs` API instead.
        See docs/ingestion/LEGACY_DEPRECATION.md
    """

    @staticmethod
    def run(runtime: JobRuntime) -> None:
        """
        Producer thread entry point.
        
        Executes the ingestion pipeline (crawl → chunk → enqueue).
        Updates state and handles errors.
        Sets stop_event when done.
        """
        warnings.warn(
            "ProducerWorker is deprecated. Use IngestionOrchestrator instead. "
            "See docs/ingestion/LEGACY_DEPRECATION.md",
            DeprecationWarning,
            stacklevel=2
        )
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
            
            # Phase tracking: start loading
            tracker = PhaseTracker(DatabaseRepository())
            tracker.start_phase(job_id, "loading")

            # Create and run producer pipeline
            pipeline = ProducerPipeline(kb_config, state)
            asyncio.run(pipeline.run())
            
        except Exception as exc:
            logger.error(
                f"{log_prefix} Producer thread failed: {exc}",
                exc_info=True,
            )
            try:
                from app.ingestion.application.ingestion_service import IngestionService
                IngestionService.instance()._set_failed(state, error_message=str(exc))
            except Exception:
                state.status = "failed"  # TODO: Rebuild
                state.phase = "failed"
                state.error = str(exc)
                state.message = "Ingestion failed"
                state.completed_at = datetime.utcnow()
            
        finally:
            # Signal consumer to stop (no more work coming)
            runtime.stop_event.set()
            
            # DO NOT mark as completed here - consumer will do that after finishing all work
            # Producer only handles crawl/chunk/enqueue phase
            if state.status != "failed":  # TODO: Rebuild
                # Mark chunking completed; next phases handled by consumer
                try:
                    tracker.complete_phase(job_id, "chunking")
                except Exception:
                    pass
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
