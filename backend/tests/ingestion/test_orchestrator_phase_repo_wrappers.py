import logging

import pytest

from backend.app.ingestion.application.orchestrator import IngestionOrchestrator
from backend.app.ingestion.domain.errors import PhaseNotFoundError, PhaseRepositoryError


class _RepoStub:
    pass


class _PhaseRepoStub:
    def __init__(self, exc: Exception):
        self._exc = exc

    def update_progress(self, job_id: str, phase_name: str, **kwargs: object) -> None:
        raise self._exc

    def start_phase(self, job_id: str, phase_name: str) -> None:
        raise self._exc

    def complete_phase(self, job_id: str, phase_name: str) -> None:
        raise self._exc

    def fail_phase(self, job_id: str, phase_name: str, error_message: str) -> None:
        raise self._exc


@pytest.mark.parametrize(
    'exc',
    [
        PhaseNotFoundError('job-1', 'loading'),
        PhaseRepositoryError('job-1', 'loading', 'update_progress', 'db down'),
    ],
)
def test_safe_phase_repo_calls_do_not_raise_for_domain_errors(exc, caplog):
    caplog.set_level(logging.WARNING)

    orchestrator = IngestionOrchestrator(repo=_RepoStub())
    orchestrator.phase_repo = _PhaseRepoStub(exc)

    orchestrator._safe_phase_update_progress('job-1', 'loading', items_processed=1)

    assert any(
        'Phase repository operation failed (non-critical)' in record.message
        for record in caplog.records
    )


def test_safe_phase_repo_calls_raise_for_unexpected_errors():
    orchestrator = IngestionOrchestrator(repo=_RepoStub())
    orchestrator.phase_repo = _PhaseRepoStub(RuntimeError('boom'))

    with pytest.raises(RuntimeError):
        orchestrator._safe_phase_update_progress('job-1', 'loading', items_processed=1)
