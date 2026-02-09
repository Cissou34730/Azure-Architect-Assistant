from __future__ import annotations

import logging
from typing import Any

from app.ingestion.domain.errors import PhaseNotFoundError, PhaseRepositoryError
from app.ingestion.infrastructure.phase_repository import PhaseRepository

logger = logging.getLogger(__name__)


def start_phase_noncritical(phase_repo: PhaseRepository, job_id: str, phase_name: str) -> None:
    try:
        phase_repo.start_phase(job_id, phase_name)
    except (PhaseNotFoundError, PhaseRepositoryError) as exc:
        logger.warning(
            'Failed to start phase tracking (non-critical)',
            extra={'job_id': job_id, 'phase_name': phase_name, 'error_type': type(exc).__name__},
            exc_info=True,
        )


def complete_phase_noncritical(phase_repo: PhaseRepository, job_id: str, phase_name: str) -> None:
    try:
        phase_repo.complete_phase(job_id, phase_name)
    except (PhaseNotFoundError, PhaseRepositoryError) as exc:
        logger.warning(
            'Failed to complete phase (non-critical)',
            extra={'job_id': job_id, 'phase_name': phase_name, 'error_type': type(exc).__name__},
            exc_info=True,
        )


def fail_phase_noncritical(
    phase_repo: PhaseRepository, job_id: str, phase_name: str, error_message: str
) -> None:
    try:
        phase_repo.fail_phase(job_id, phase_name, error_message=error_message)
    except (PhaseNotFoundError, PhaseRepositoryError) as exc:
        logger.warning(
            'Failed to fail phase (non-critical)',
            extra={'job_id': job_id, 'phase_name': phase_name, 'error_type': type(exc).__name__},
            exc_info=True,
        )


def update_progress_noncritical(
    phase_repo: PhaseRepository, job_id: str, phase_name: str, **kwargs: Any
) -> None:
    try:
        phase_repo.update_progress(job_id, phase_name, **kwargs)
    except (PhaseNotFoundError, PhaseRepositoryError) as exc:
        logger.warning(
            'Failed to persist phase progress (non-critical)',
            extra={
                'job_id': job_id,
                'phase_name': phase_name,
                'kwargs': kwargs,
                'error_type': type(exc).__name__,
            },
            exc_info=True,
        )
