"""Tests for phase state domain model."""

import pytest
from datetime import datetime

from app.ingestion.domain.models.phase_state import PhaseState
from app.ingestion.domain.enums import PhaseStatus, JobPhase


class TestPhaseState:
    """Test PhaseState model and methods."""

    def test_phase_state_initialization(self):
        """Test phase state is properly initialized."""
        phase = PhaseState(phase_name=JobPhase.LOADING.value)
        
        assert phase.phase_name == JobPhase.LOADING.value
        assert phase.status == PhaseStatus.NOT_STARTED
        assert phase.progress == 0
        assert phase.items_processed == 0
        assert phase.items_total is None
        assert phase.started_at is None
        assert phase.completed_at is None
        assert phase.error is None

    def test_start_phase(self):
        """Test starting a phase."""
        phase = PhaseState(phase_name=JobPhase.CHUNKING.value)
        phase.start()
        
        assert phase.status == PhaseStatus.RUNNING
        assert phase.started_at is not None
        assert isinstance(phase.started_at, datetime)

    def test_pause_phase(self):
        """Test pausing a phase."""
        phase = PhaseState(phase_name=JobPhase.EMBEDDING.value)
        phase.start()
        phase.pause()
        
        assert phase.status == PhaseStatus.PAUSED

    def test_resume_phase(self):
        """Test resuming a paused phase."""
        phase = PhaseState(phase_name=JobPhase.INDEXING.value)
        phase.start()
        phase.pause()
        phase.resume()
        
        assert phase.status == PhaseStatus.RUNNING

    def test_complete_phase(self):
        """Test completing a phase."""
        phase = PhaseState(phase_name=JobPhase.LOADING.value)
        phase.start()
        phase.complete()
        
        assert phase.status == PhaseStatus.COMPLETED
        assert phase.completed_at is not None
        assert phase.progress == 100

    def test_fail_phase(self):
        """Test failing a phase."""
        phase = PhaseState(phase_name=JobPhase.CHUNKING.value)
        phase.start()
        phase.fail("Test error message")
        
        assert phase.status == PhaseStatus.FAILED
        assert phase.completed_at is not None
        assert phase.error == "Test error message"

    def test_update_progress_with_total(self):
        """Test updating progress when total is known."""
        phase = PhaseState(phase_name=JobPhase.EMBEDDING.value)
        phase.update_progress(items_processed=50, items_total=100)
        
        assert phase.items_processed == 50
        assert phase.items_total == 100
        assert phase.progress == 50

    def test_update_progress_without_total(self):
        """Test updating progress when total is unknown."""
        phase = PhaseState(phase_name=JobPhase.INDEXING.value)
        phase.update_progress(items_processed=10)
        
        assert phase.items_processed == 10
        assert phase.items_total is None
        assert phase.progress == 10

    def test_update_progress_caps_at_99_without_total(self):
        """Test progress caps at 99 when total is unknown."""
        phase = PhaseState(phase_name=JobPhase.LOADING.value)
        phase.update_progress(items_processed=150)
        
        assert phase.progress == 99

    def test_update_progress_caps_at_100(self):
        """Test progress caps at 100."""
        phase = PhaseState(phase_name=JobPhase.CHUNKING.value)
        phase.update_progress(items_processed=150, items_total=100)
        
        assert phase.progress == 100

    def test_is_terminal(self):
        """Test terminal state detection."""
        phase = PhaseState(phase_name=JobPhase.EMBEDDING.value)
        
        assert not phase.is_terminal()
        
        phase.complete()
        assert phase.is_terminal()
        
        phase2 = PhaseState(phase_name=JobPhase.INDEXING.value)
        phase2.fail("error")
        assert phase2.is_terminal()

    def test_is_active(self):
        """Test active state detection."""
        phase = PhaseState(phase_name=JobPhase.LOADING.value)
        
        assert not phase.is_active()
        
        phase.start()
        assert phase.is_active()
        
        phase.pause()
        assert not phase.is_active()


class TestIngestionStateWithPhases:
    """Test IngestionState enhanced with phase tracking."""

    def test_get_overall_status_with_all_completed(self):
        """Test overall status when all phases completed."""
        from app.ingestion.domain.models.state import IngestionState
        
        state = IngestionState(kb_id="test", job_id="job1")
        state.phases = {
            JobPhase.LOADING.value: {"status": PhaseStatus.COMPLETED.value, "progress": 100},
            JobPhase.CHUNKING.value: {"status": PhaseStatus.COMPLETED.value, "progress": 100},
            JobPhase.EMBEDDING.value: {"status": PhaseStatus.COMPLETED.value, "progress": 100},
            JobPhase.INDEXING.value: {"status": PhaseStatus.COMPLETED.value, "progress": 100},
        }
        
        assert state.get_overall_status() == "completed"

    def test_get_overall_status_with_failure(self):
        """Test overall status when any phase failed."""
        from app.ingestion.domain.models.state import IngestionState
        
        state = IngestionState(kb_id="test", job_id="job1")
        state.phases = {
            JobPhase.LOADING.value: {"status": PhaseStatus.COMPLETED.value, "progress": 100},
            JobPhase.CHUNKING.value: {"status": PhaseStatus.FAILED.value, "progress": 50},
            JobPhase.EMBEDDING.value: {"status": PhaseStatus.NOT_STARTED.value, "progress": 0},
            JobPhase.INDEXING.value: {"status": PhaseStatus.NOT_STARTED.value, "progress": 0},
        }
        
        assert state.get_overall_status() == "failed"

    def test_get_overall_status_with_running(self):
        """Test overall status when any phase is running."""
        from app.ingestion.domain.models.state import IngestionState
        
        state = IngestionState(kb_id="test", job_id="job1")
        state.phases = {
            JobPhase.LOADING.value: {"status": PhaseStatus.COMPLETED.value, "progress": 100},
            JobPhase.CHUNKING.value: {"status": PhaseStatus.RUNNING.value, "progress": 50},
            JobPhase.EMBEDDING.value: {"status": PhaseStatus.NOT_STARTED.value, "progress": 0},
            JobPhase.INDEXING.value: {"status": PhaseStatus.NOT_STARTED.value, "progress": 0},
        }
        
        assert state.get_overall_status() == "running"

    def test_get_current_phase(self):
        """Test getting current active phase."""
        from app.ingestion.domain.models.state import IngestionState
        
        state = IngestionState(kb_id="test", job_id="job1")
        state.phases = {
            JobPhase.LOADING.value: {"status": PhaseStatus.COMPLETED.value, "progress": 100},
            JobPhase.CHUNKING.value: {"status": PhaseStatus.RUNNING.value, "progress": 50},
            JobPhase.EMBEDDING.value: {"status": PhaseStatus.NOT_STARTED.value, "progress": 0},
            JobPhase.INDEXING.value: {"status": PhaseStatus.NOT_STARTED.value, "progress": 0},
        }
        
        assert state.get_current_phase() == JobPhase.CHUNKING.value

    def test_get_current_phase_paused(self):
        """Test getting current phase when paused."""
        from app.ingestion.domain.models.state import IngestionState
        
        state = IngestionState(kb_id="test", job_id="job1")
        state.phases = {
            JobPhase.LOADING.value: {"status": PhaseStatus.COMPLETED.value, "progress": 100},
            JobPhase.CHUNKING.value: {"status": PhaseStatus.PAUSED.value, "progress": 50},
            JobPhase.EMBEDDING.value: {"status": PhaseStatus.NOT_STARTED.value, "progress": 0},
            JobPhase.INDEXING.value: {"status": PhaseStatus.NOT_STARTED.value, "progress": 0},
        }
        
        assert state.get_current_phase() == JobPhase.CHUNKING.value

    def test_get_overall_progress(self):
        """Test calculating overall progress."""
        from app.ingestion.domain.models.state import IngestionState
        
        state = IngestionState(kb_id="test", job_id="job1")
        state.phases = {
            JobPhase.LOADING.value: {"status": PhaseStatus.COMPLETED.value, "progress": 100},
            JobPhase.CHUNKING.value: {"status": PhaseStatus.RUNNING.value, "progress": 50},
            JobPhase.EMBEDDING.value: {"status": PhaseStatus.NOT_STARTED.value, "progress": 0},
            JobPhase.INDEXING.value: {"status": PhaseStatus.NOT_STARTED.value, "progress": 0},
        }
        
        # (100 * 25/100) + (50 * 25/100) + (0 * 25/100) + (0 * 25/100) = 25 + 12.5 = 37
        progress = state.get_overall_progress()
        assert 37 <= progress <= 38  # Account for integer division
