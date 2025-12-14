"""Tests for phase status database persistence."""

import pytest
from datetime import datetime

from app.ingestion.infrastructure.repository import DatabaseRepository
from app.ingestion.domain.enums import JobPhase, PhaseStatus
from app.ingestion.domain.models import PhaseState
from app.ingestion.ingestion_database import init_ingestion_database


class TestPhasePersistence:
    """Test phase status persistence in database."""

    @pytest.fixture(scope="class", autouse=True)
    def setup_database(self):
        """Initialize database schema before all tests."""
        init_ingestion_database()
        yield

    @pytest.fixture
    def repository(self):
        """Create repository instance."""
        return DatabaseRepository()

    @pytest.fixture
    def job_id(self, repository):
        """Create a test job."""
        job_id = repository.create_job(
            kb_id="test-kb",
            source_type="website",
            source_config={"urls": ["https://example.com"]},
        )
        return job_id

    def test_initialize_phase_statuses(self, repository, job_id):
        """Test phase status initialization creates all phases."""
        phases = repository.get_all_phase_statuses(job_id)
        
        assert len(phases) == 4
        assert JobPhase.LOADING.value in phases
        assert JobPhase.CHUNKING.value in phases
        assert JobPhase.EMBEDDING.value in phases
        assert JobPhase.INDEXING.value in phases
        
        # All should start as NOT_STARTED
        for phase_state in phases.values():
            assert phase_state.status == PhaseStatus.NOT_STARTED
            assert phase_state.progress == 0
            assert phase_state.items_processed == 0

    def test_get_phase_status(self, repository, job_id):
        """Test retrieving a specific phase status."""
        phase_state = repository.get_phase_status(job_id, JobPhase.LOADING.value)
        
        assert phase_state is not None
        assert phase_state.status == PhaseStatus.NOT_STARTED
        assert phase_state.progress == 0

    def test_update_phase_status(self, repository, job_id):
        """Test updating phase status."""
        repository.update_phase_status(
            job_id=job_id,
            phase_name=JobPhase.LOADING.value,
            status=PhaseStatus.RUNNING.value,
            progress_percent=50,
            items_processed=10,
            items_total=20,
        )
        
        phase_state = repository.get_phase_status(job_id, JobPhase.LOADING.value)
        
        assert phase_state.status == PhaseStatus.RUNNING
        assert phase_state.progress == 50
        assert phase_state.items_processed == 10
        assert phase_state.items_total == 20
        assert phase_state.started_at is not None

    def test_save_phase_state(self, repository, job_id):
        """Test saving a PhaseState domain object."""
        phase_state = PhaseState(
            phase_name=JobPhase.LOADING.value,
            status=PhaseStatus.COMPLETED,
            progress=100,
            items_processed=20,
            items_total=20,
        )
        
        repository.save_phase_state(
            job_id=job_id,
            phase_name=JobPhase.LOADING.value,
            phase_state=phase_state,
        )
        
        loaded_state = repository.get_phase_status(job_id, JobPhase.LOADING.value)
        
        assert loaded_state.status == PhaseStatus.COMPLETED
        assert loaded_state.progress == 100
        assert loaded_state.items_processed == 20
        assert loaded_state.items_total == 20

    def test_phase_lifecycle(self, repository, job_id):
        """Test complete phase lifecycle: start -> progress -> complete."""
        phase_name = JobPhase.CHUNKING.value
        
        # Start phase
        repository.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=PhaseStatus.RUNNING.value,
        )
        state = repository.get_phase_status(job_id, phase_name)
        assert state.status == PhaseStatus.RUNNING
        assert state.started_at is not None
        
        # Update progress
        repository.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=PhaseStatus.RUNNING.value,
            progress_percent=75,
            items_processed=15,
            items_total=20,
        )
        state = repository.get_phase_status(job_id, phase_name)
        assert state.progress == 75
        assert state.items_processed == 15
        
        # Complete phase
        repository.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=PhaseStatus.COMPLETED.value,
            progress_percent=100,
            items_processed=20,
        )
        state = repository.get_phase_status(job_id, phase_name)
        assert state.status == PhaseStatus.COMPLETED
        assert state.completed_at is not None

    def test_phase_pause_resume(self, repository, job_id):
        """Test pausing and resuming a phase."""
        phase_name = JobPhase.EMBEDDING.value
        
        # Start
        repository.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=PhaseStatus.RUNNING.value,
            items_processed=5,
        )
        
        # Pause
        repository.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=PhaseStatus.PAUSED.value,
        )
        state = repository.get_phase_status(job_id, phase_name)
        assert state.status == PhaseStatus.PAUSED
        assert state.items_processed == 5  # Progress preserved
        
        # Resume
        repository.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=PhaseStatus.RUNNING.value,
        )
        state = repository.get_phase_status(job_id, phase_name)
        assert state.status == PhaseStatus.RUNNING
        assert state.items_processed == 5  # Progress still preserved

    def test_phase_failure(self, repository, job_id):
        """Test recording phase failure with error message."""
        phase_name = JobPhase.INDEXING.value
        error_msg = "Connection timeout to vector database"
        
        repository.update_phase_status(
            job_id=job_id,
            phase_name=phase_name,
            status=PhaseStatus.FAILED.value,
            error_message=error_msg,
        )
        
        state = repository.get_phase_status(job_id, phase_name)
        assert state.status == PhaseStatus.FAILED
        assert state.error == error_msg
        assert state.completed_at is not None

    def test_job_to_state_loads_phases(self, repository, job_id):
        """Test that _job_to_state loads phase statuses."""
        # Update some phase statuses
        repository.update_phase_status(
            job_id=job_id,
            phase_name=JobPhase.LOADING.value,
            status=PhaseStatus.COMPLETED.value,
            progress_percent=100,
        )
        repository.update_phase_status(
            job_id=job_id,
            phase_name=JobPhase.CHUNKING.value,
            status=PhaseStatus.RUNNING.value,
            progress_percent=60,
        )
        
        # Load job state
        state = repository.get_latest_job("test-kb")
        
        assert state is not None
        assert state.phases is not None
        assert len(state.phases) == 4
        
        # Check loaded phases
        assert state.phases[JobPhase.LOADING.value].status == PhaseStatus.COMPLETED
        assert state.phases[JobPhase.LOADING.value].progress == 100
        assert state.phases[JobPhase.CHUNKING.value].status == PhaseStatus.RUNNING
        assert state.phases[JobPhase.CHUNKING.value].progress == 60
