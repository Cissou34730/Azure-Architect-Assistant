"""Tests for persistence store implementations."""

import pytest
from datetime import datetime

from app.ingestion.domain.models import IngestionState
from app.ingestion.infrastructure.persistence import LocalDiskPersistenceStore


class TestLocalDiskPersistenceStore:
    """Test local disk persistence store."""

    def test_save_and_load_state(self, persistence_store: LocalDiskPersistenceStore):
        """Test saving and loading state."""
        state = IngestionState(
            kb_id="test-kb-1",
            job_id="job-123",
            status="running",
            phase="crawling",
            progress=50,
            message="Test message",
            created_at=datetime.utcnow(),
        )

        # Save state
        persistence_store.save_state(state)

        # Load state
        loaded = persistence_store.load_state("test-kb-1")
        assert loaded is not None
        assert loaded.kb_id == "test-kb-1"
        assert loaded.job_id == "job-123"
        assert loaded.status == "running"
        assert loaded.phase == "crawling"
        assert loaded.progress == 50
        assert loaded.message == "Test message"

    def test_load_nonexistent_state(self, persistence_store: LocalDiskPersistenceStore):
        """Test loading non-existent state returns None."""
        loaded = persistence_store.load_state("nonexistent-kb")
        assert loaded is None

    def test_load_all_states(self, persistence_store: LocalDiskPersistenceStore):
        """Test loading all states."""
        # Save multiple states
        for i in range(3):
            state = IngestionState(
                kb_id=f"test-kb-{i}",
                job_id=f"job-{i}",
                status="running",
                created_at=datetime.utcnow(),
            )
            persistence_store.save_state(state)

        # Load all
        all_states = persistence_store.load_all_states()
        assert len(all_states) == 3
        assert "test-kb-0" in all_states
        assert "test-kb-1" in all_states
        assert "test-kb-2" in all_states

    def test_delete_state(self, persistence_store: LocalDiskPersistenceStore):
        """Test deleting state."""
        state = IngestionState(
            kb_id="test-kb-delete",
            job_id="job-delete",
            status="completed",
            created_at=datetime.utcnow(),
        )

        # Save and verify
        persistence_store.save_state(state)
        assert persistence_store.load_state("test-kb-delete") is not None

        # Delete and verify
        persistence_store.delete_state("test-kb-delete")
        assert persistence_store.load_state("test-kb-delete") is None

    def test_update_state(self, persistence_store: LocalDiskPersistenceStore):
        """Test updating existing state."""
        # Save initial state
        state = IngestionState(
            kb_id="test-kb-update",
            job_id="job-update",
            status="running",
            progress=25,
            created_at=datetime.utcnow(),
        )
        persistence_store.save_state(state)

        # Update state
        state.progress = 75
        state.message = "Updated message"
        persistence_store.save_state(state)

        # Load and verify
        loaded = persistence_store.load_state("test-kb-update")
        assert loaded is not None
        assert loaded.progress == 75
        assert loaded.message == "Updated message"

    def test_state_with_metrics(self, persistence_store: LocalDiskPersistenceStore):
        """Test state with metrics dict."""
        state = IngestionState(
            kb_id="test-kb-metrics",
            job_id="job-metrics",
            status="running",
            metrics={'chunks_queued': 100, 'chunks_embedded': 50},
            created_at=datetime.utcnow(),
        )

        persistence_store.save_state(state)
        loaded = persistence_store.load_state("test-kb-metrics")
        assert loaded is not None
        assert loaded.metrics['chunks_queued'] == 100
        assert loaded.metrics['chunks_embedded'] == 50
