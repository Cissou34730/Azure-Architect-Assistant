"""
Consumer worker - thread executor for consumer pipeline.

.. deprecated:: 2025-12-10
    This producer/consumer worker pattern is deprecated. Use the orchestrator-based
    implementation with `/ingestion/v2/jobs` API instead.
    See docs/ingestion/LEGACY_DEPRECATION.md for migration guide.
"""

from __future__ import annotations

import logging
import warnings

from app.ingestion.domain.models import JobRuntime
from app.ingestion.application.consumer_pipeline import ConsumerPipeline
from app.ingestion.application.phase_tracker import PhaseTracker
from app.ingestion.infrastructure.repository import DatabaseRepository

logger = logging.getLogger(__name__)


class ConsumerWorker:
    """
    Worker that runs the consumer pipeline in a separate thread.
    
    .. deprecated:: 2025-12-10
        Use `IngestionOrchestrator` with `/ingestion/v2/jobs` API instead.
        See docs/ingestion/LEGACY_DEPRECATION.md
    """

    @staticmethod
    def run(runtime: JobRuntime) -> None:
        """
        Consumer thread entry point.
        
        Executes the consumer pipeline (dequeue → embed → index).
        Updates state and handles errors.
        """
        warnings.warn(
            "ConsumerWorker is deprecated. Use IngestionOrchestrator instead. "
            "See docs/ingestion/LEGACY_DEPRECATION.md",
            DeprecationWarning,
            stacklevel=2
        )
        kb_id = runtime.kb_id
        job_id = runtime.job_id
        log_prefix = f"[Consumer|KB={kb_id}|Job={job_id}]"
        
        try:
            logger.info(f"{log_prefix} Starting consumer thread")
            
            tracker = PhaseTracker(DatabaseRepository())
            # Start embedding when first item is dequeued in pipeline; mark here as running
            tracker.start_phase(job_id, "embedding")

            # Create and run consumer pipeline
            pipeline = ConsumerPipeline(runtime)
            pipeline.run()
            
        except Exception as exc:
            logger.error(
                f"{log_prefix} Consumer thread failed: {exc}",
                exc_info=True,
            )
            try:
                from app.ingestion.application.ingestion_service import IngestionService
                IngestionService.instance()._set_failed(runtime.state, error_message=str(exc))
            except Exception:
                # TODO: Rebuild status management
                runtime.state.status = "failed"
                runtime.state.error = str(exc)
            
        finally:
            logger.info(f"{log_prefix} Consumer thread finished")
            # Mark indexing completed at end
            try:
                tracker.complete_phase(job_id, "indexing")
            except Exception:
                pass
