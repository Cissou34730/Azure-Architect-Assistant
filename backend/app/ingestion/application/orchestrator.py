"""
Ingestion Orchestrator
Sequential orchestrator implementing load -> chunk -> embed -> index pipeline.
See docs/SYSTEM_ARCHITECTURE.md for a pipeline overview.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any

from app.ingestion.application.job_gate import JobGate
from app.ingestion.application.pipeline_components import create_pipeline_components
from app.ingestion.application.pipeline_coordinator import PipelineCoordinator
from app.ingestion.application.policies import RetryPolicy, WorkflowDefinition
from app.ingestion.application.shutdown_manager import ShutdownManager
from app.ingestion.domain.errors import PhaseNotFoundError, PhaseRepositoryError
from app.ingestion.infrastructure.job_repository import JobRepository, create_job_repository
from app.ingestion.infrastructure.phase_repository import create_phase_repository

try:  # pragma: no cover
    from backend.app.ingestion.domain.errors import (
        PhaseNotFoundError as BackendPhaseNotFoundError,
    )
    from backend.app.ingestion.domain.errors import (
        PhaseRepositoryError as BackendPhaseRepositoryError,
    )
except Exception:  # noqa: BLE001
    BackendPhaseNotFoundError = PhaseNotFoundError
    BackendPhaseRepositoryError = PhaseRepositoryError

logger = logging.getLogger(__name__)


class IngestionOrchestrator:
    """
    Sequential orchestrator for ingestion pipeline.
    Implements load → chunk → embed → index with gates, checkpoints, and cleanup.
    """

    def __init__(
        self,
        repo: JobRepository | None = None,
        workflow: WorkflowDefinition | None = None,
        retry_policy: RetryPolicy | None = None,
        shutdown_manager: ShutdownManager | None = None,
    ) -> None:
        """
        Initialize orchestrator.

        Args:
            repo: Repository for job persistence
            workflow: Workflow definition (defaults to standard)
            retry_policy: Retry policy (defaults to 3 attempts)
        """
        self.repo = repo or create_job_repository()
        self.phase_repo = create_phase_repository()
        self.workflow = workflow or WorkflowDefinition()
        self.retry_policy = retry_policy or RetryPolicy()
        self.shutdown_manager = shutdown_manager
        self._shutdown_event = asyncio.Event()
        self._interrupted = False
        logger.info('IngestionOrchestrator initialized')

    def _safe_phase_repo_call(
        self, operation: str, job_id: str, phase_name: str, fn, /, **kwargs: Any
    ) -> None:
        try:
            fn(job_id, phase_name, **kwargs)
        except (
            PhaseNotFoundError,
            PhaseRepositoryError,
            BackendPhaseNotFoundError,
            BackendPhaseRepositoryError,
        ) as exc:
            logging.warning(
                'Phase repository operation failed (non-critical)',
                extra={
                    'operation': operation,
                    'job_id': job_id,
                    'phase_name': phase_name,
                    'kwargs': kwargs,
                    'error_type': type(exc).__name__,
                },
                exc_info=True,
            )
        except Exception as exc:
            logger.error(
                'Unexpected error during phase repository operation',
                extra={
                    'operation': operation,
                    'job_id': job_id,
                    'phase_name': phase_name,
                    'kwargs': kwargs,
                    'error_type': type(exc).__name__,
                },
                exc_info=True,
            )
            raise

    def _safe_phase_start(self, job_id: str, phase_name: str) -> None:
        self._safe_phase_repo_call('start_phase', job_id, phase_name, self.phase_repo.start_phase)

    def _safe_phase_complete(self, job_id: str, phase_name: str) -> None:
        self._safe_phase_repo_call(
            'complete_phase', job_id, phase_name, self.phase_repo.complete_phase
        )

    def _safe_phase_fail(self, job_id: str, phase_name: str, error_message: str) -> None:
        self._safe_phase_repo_call(
            'fail_phase',
            job_id,
            phase_name,
            self.phase_repo.fail_phase,
            error_message=error_message,
        )

    def _safe_phase_update_progress(self, job_id: str, phase_name: str, **kwargs: Any) -> None:
        self._safe_phase_repo_call(
            'update_progress', job_id, phase_name, self.phase_repo.update_progress, **kwargs
        )

    def is_shutdown_requested(self) -> bool:
        """Check if shutdown has been requested for this job."""
        is_set = self._shutdown_event.is_set()
        if is_set:
            logger.warning('⚠️  SHUTDOWN FLAG DETECTED - Orchestrator should pause')
        return is_set

    async def run(self, job_id: str, kb_id: str, kb_config: dict[str, Any]) -> None:
        """
        Run ingestion pipeline for a job.

        Args:
            job_id: Job identifier
            kb_id: Knowledge base identifier
            kb_config: KB configuration dict

        Raises:
            Exception: On unrecoverable errors
        """
        logger.info(f'Starting ingestion: job_id={job_id}, kb_id={kb_id}')

        if self.shutdown_manager is not None:
            self._shutdown_event = self.shutdown_manager.register_job(job_id)
        try:
            # 1. Load job state
            checkpoint, counters = self._prepare_job_state(job_id)

            # 2. Initialize components
            try:
                components = create_pipeline_components(kb_id, kb_config, checkpoint)
            except Exception as exc:
                self.repo.set_job_status(
                    job_id,
                    status='failed',
                    finished_at=datetime.now(timezone.utc),
                    last_error=f'Initialization failed: {exc}',
                )
                raise

            # 3. Process pipeline
            try:
                job_gate = JobGate(self.repo)
                coordinator = PipelineCoordinator(
                    repo=self.repo,
                    phase_repo=self.phase_repo,
                    job_gate=job_gate,
                    is_shutdown_requested=self.is_shutdown_requested,
                    retry_policy=self.retry_policy,
                )
                await coordinator.run(
                    job_id=job_id,
                    kb_id=kb_id,
                    kb_config=kb_config,
                    components=components,
                    checkpoint=checkpoint,
                    counters=counters,
                )
            except Exception as exc:
                logger.exception(f'Ingestion failed: job_id={job_id}')
                self.repo.set_job_status(
                    job_id,
                    status='failed',
                    finished_at=datetime.now(timezone.utc),
                    last_error=str(exc),
                )
                raise
        finally:
            if self.shutdown_manager is not None:
                self.shutdown_manager.unregister_job(job_id)

    def _prepare_job_state(self, job_id: str) -> tuple[dict[str, Any], dict[str, int]]:
        """Load and initialize job state."""
        job = self.repo.get_job(job_id)
        checkpoint = job.checkpoint or {}
        counters = job.counters or {
            'docs_seen': 0,
            'chunks_seen': 0,
            'chunks_processed': 0,
            'chunks_skipped': 0,
            'chunks_error': 0,
        }
        return checkpoint, counters
