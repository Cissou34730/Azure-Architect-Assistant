"""Test fixtures for ingestion tests."""

import pytest
import tempfile
from pathlib import Path
from typing import Generator

from config import IngestionSettings, set_settings
from app.ingestion.infrastructure.repository import DatabaseRepository
from app.ingestion.application.lifecycle import LifecycleManager


@pytest.fixture
def temp_data_dir() -> Generator[Path, None, None]:
    """Provide temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def test_settings(temp_data_dir: Path) -> IngestionSettings:
    """Provide test settings with temp directory."""
    settings = IngestionSettings(
        batch_size=10,
        dequeue_timeout=0.01,
        consumer_poll_interval=0.01,
        thread_join_timeout=2.0,
    )
    set_settings(settings)
    return settings


@pytest.fixture
def repository() -> DatabaseRepository:
    """Provide database repository for tests."""
    return DatabaseRepository()


@pytest.fixture
def lifecycle_manager() -> LifecycleManager:
    """Provide lifecycle manager for tests."""
    return LifecycleManager()
