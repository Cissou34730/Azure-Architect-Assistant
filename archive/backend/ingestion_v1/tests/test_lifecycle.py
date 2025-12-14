"""Tests for lifecycle manager."""

import pytest
import threading
import time
from datetime import datetime

from app.ingestion.domain.models import IngestionState, JobRuntime
from app.ingestion.application.lifecycle import LifecycleManager


def dummy_producer_worker(runtime: JobRuntime) -> None:
    """Dummy producer worker for testing."""
    for i in range(5):
        if runtime.stop_event.is_set():
            break
        time.sleep(0.1)


def dummy_consumer_worker(runtime: JobRuntime) -> None:
    """Dummy consumer worker for testing."""
    while not runtime.stop_event.is_set():
        time.sleep(0.1)


class TestLifecycleManager:
    """Test lifecycle manager."""

    def test_create_runtime(self, lifecycle_manager: LifecycleManager):
        """Test creating runtime."""
        state = IngestionState(
            kb_id="test-kb",
            job_id="test-job",
            status="running",
            created_at=datetime.utcnow(),
        )

        def dummy_target():
            pass

        runtime = lifecycle_manager.create_runtime(
            job_id="test-job",
            kb_id="test-kb",
            state=state,
            producer_target=dummy_target,
            producer_args=(),
            producer_kwargs={},
        )

        assert runtime.job_id == "test-job"
        assert runtime.kb_id == "test-kb"
        assert runtime.state == state
        assert runtime.producer_target == dummy_target

    def test_start_and_stop_threads(self, lifecycle_manager: LifecycleManager):
        """Test starting and stopping threads."""
        state = IngestionState(
            kb_id="test-kb",
            job_id="test-job",
            status="running",
            created_at=datetime.utcnow(),
        )

        runtime = lifecycle_manager.create_runtime(
            job_id="test-job",
            kb_id="test-kb",
            state=state,
            producer_target=lambda: None,
            producer_args=(),
            producer_kwargs={},
        )

        # Start threads
        lifecycle_manager.start_threads(
            runtime,
            dummy_producer_worker,
            dummy_consumer_worker,
        )

        # Verify threads are alive
        assert lifecycle_manager.is_running(runtime)
        assert runtime.producer_thread.is_alive()
        assert runtime.consumer_thread.is_alive()

        # Stop threads
        lifecycle_manager.stop_threads(runtime, timeout=2.0)

        # Verify threads exited
        time.sleep(0.5)
        assert not runtime.producer_thread.is_alive()
        assert not runtime.consumer_thread.is_alive()

    def test_is_running(self, lifecycle_manager: LifecycleManager):
        """Test is_running check."""
        state = IngestionState(
            kb_id="test-kb",
            job_id="test-job",
            status="running",
            created_at=datetime.utcnow(),
        )

        runtime = lifecycle_manager.create_runtime(
            job_id="test-job",
            kb_id="test-kb",
            state=state,
            producer_target=lambda: None,
            producer_args=(),
            producer_kwargs={},
        )

        # Not running initially
        assert not lifecycle_manager.is_running(runtime)

        # Start threads
        lifecycle_manager.start_threads(
            runtime,
            dummy_producer_worker,
            dummy_consumer_worker,
        )

        # Running now
        assert lifecycle_manager.is_running(runtime)

        # Stop and verify not running
        lifecycle_manager.stop_threads(runtime, timeout=2.0)
        time.sleep(0.5)
        assert not lifecycle_manager.is_running(runtime)

    def test_cooperative_shutdown(self, lifecycle_manager: LifecycleManager):
        """Test cooperative shutdown with stop_event."""
        state = IngestionState(
            kb_id="test-kb",
            job_id="test-job",
            status="running",
            created_at=datetime.utcnow(),
        )

        runtime = lifecycle_manager.create_runtime(
            job_id="test-job",
            kb_id="test-kb",
            state=state,
            producer_target=lambda: None,
            producer_args=(),
            producer_kwargs={},
        )

        shutdown_detected = threading.Event()

        def cooperative_worker(runtime: JobRuntime):
            while not runtime.stop_event.is_set():
                time.sleep(0.05)
            shutdown_detected.set()

        lifecycle_manager.start_threads(
            runtime,
            cooperative_worker,
            cooperative_worker,
        )

        # Signal shutdown
        lifecycle_manager.stop_threads(runtime, timeout=2.0)

        # Verify shutdown was detected
        assert shutdown_detected.wait(timeout=1.0)
