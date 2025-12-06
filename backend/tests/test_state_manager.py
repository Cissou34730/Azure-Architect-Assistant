import pytest

from app.ingestion.core.state_manager import aggregate_job_status


def test_aggregate_job_status_all_pending():
    phases = {
        "loading": {"status": "pending"},
        "chunking": {"status": "pending"},
        "embedding": {"status": "pending"},
        "indexing": {"status": "pending"},
    }
    assert aggregate_job_status(phases) == "pending"


def test_aggregate_job_status_running_overrides_pending():
    phases = {
        "loading": {"status": "running"},
        "chunking": {"status": "pending"},
    }
    assert aggregate_job_status(phases) == "running"


def test_aggregate_job_status_failed_overrides_all():
    phases = {
        "loading": {"status": "completed"},
        "chunking": {"status": "failed"},
        "embedding": {"status": "paused"},
    }
    assert aggregate_job_status(phases) == "failed"


def test_aggregate_job_status_paused_when_any_paused_and_none_running():
    phases = {
        "loading": {"status": "completed"},
        "chunking": {"status": "paused"},
        "embedding": {"status": "pending"},
    }
    assert aggregate_job_status(phases) == "paused"


def test_aggregate_job_status_completed_when_all_completed():
    phases = {
        "loading": {"status": "completed"},
        "chunking": {"status": "completed"},
        "embedding": {"status": "completed"},
    }
    assert aggregate_job_status(phases) == "completed"
