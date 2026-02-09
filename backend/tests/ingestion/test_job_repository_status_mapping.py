from __future__ import annotations

import pytest

from app.ingestion.infrastructure.job_repository import JobRepository
from app.ingestion.models import JobStatus as DBJobStatus


@pytest.mark.parametrize(
    ('status', 'expected'),
    [
        ('not_started', DBJobStatus.NOT_STARTED.value),
        ('running', DBJobStatus.RUNNING.value),
        ('paused', DBJobStatus.PAUSED.value),
        ('completed', DBJobStatus.COMPLETED.value),
        ('failed', DBJobStatus.FAILED.value),
        ('canceled', DBJobStatus.CANCELED.value),
    ],
)
def test_map_status_to_db(status: str, expected: str) -> None:
    assert JobRepository._map_status_to_db(status) == expected


def test_map_status_to_db_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        JobRepository._map_status_to_db('nope')


@pytest.mark.parametrize(
    ('db_status', 'expected'),
    [
        (DBJobStatus.NOT_STARTED.value, 'not_started'),
        (DBJobStatus.RUNNING.value, 'running'),
        (DBJobStatus.PAUSED.value, 'paused'),
        (DBJobStatus.COMPLETED.value, 'completed'),
        (DBJobStatus.FAILED.value, 'failed'),
        (DBJobStatus.CANCELED.value, 'canceled'),
    ],
)
def test_map_status_from_db(db_status: str, expected: str) -> None:
    assert JobRepository._map_status_from_db(db_status) == expected
