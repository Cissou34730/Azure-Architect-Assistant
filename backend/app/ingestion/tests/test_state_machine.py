"""Tests for domain state machine and transitions."""

import pytest

from app.ingestion.domain.enums import (
    JobStatus,
    validate_transition,
    transition_or_raise,
    StateTransitionError,
    get_allowed_transitions,
    is_terminal_status,
)


class TestJobStatusTransitions:
    """Test state machine transitions."""

    def test_pending_to_running(self):
        """Test valid transition from pending to running."""
        assert validate_transition(JobStatus.PENDING, JobStatus.RUNNING)

    def test_running_to_paused(self):
        """Test valid transition from running to paused."""
        assert validate_transition(JobStatus.RUNNING, JobStatus.PAUSED)

    def test_paused_to_running(self):
        """Test valid transition from paused to running (resume)."""
        assert validate_transition(JobStatus.PAUSED, JobStatus.RUNNING)

    def test_running_to_completed(self):
        """Test valid transition from running to completed."""
        assert validate_transition(JobStatus.RUNNING, JobStatus.COMPLETED)

    def test_invalid_completed_to_running(self):
        """Test invalid transition from completed to running."""
        assert not validate_transition(JobStatus.COMPLETED, JobStatus.RUNNING)

    def test_invalid_pending_to_paused(self):
        """Test invalid transition from pending to paused."""
        assert not validate_transition(JobStatus.PENDING, JobStatus.PAUSED)

    def test_transition_or_raise_valid(self):
        """Test transition_or_raise with valid transition."""
        transition_or_raise(JobStatus.RUNNING, JobStatus.PAUSED)  # Should not raise

    def test_transition_or_raise_invalid(self):
        """Test transition_or_raise with invalid transition."""
        with pytest.raises(StateTransitionError) as exc_info:
            transition_or_raise(JobStatus.COMPLETED, JobStatus.RUNNING)
        assert exc_info.value.current == JobStatus.COMPLETED
        assert exc_info.value.target == JobStatus.RUNNING

    def test_get_allowed_transitions(self):
        """Test getting allowed transitions."""
        allowed = get_allowed_transitions(JobStatus.RUNNING)
        assert JobStatus.PAUSED in allowed
        assert JobStatus.COMPLETED in allowed
        assert JobStatus.FAILED in allowed
        assert JobStatus.CANCELED in allowed

    def test_terminal_statuses(self):
        """Test terminal status detection."""
        assert is_terminal_status(JobStatus.COMPLETED)
        assert is_terminal_status(JobStatus.FAILED)
        assert is_terminal_status(JobStatus.CANCELED)
        assert not is_terminal_status(JobStatus.RUNNING)
        assert not is_terminal_status(JobStatus.PAUSED)

    def test_cancel_from_any_status(self):
        """Test that cancellation is allowed from most statuses."""
        assert validate_transition(JobStatus.PENDING, JobStatus.CANCELED)
        assert validate_transition(JobStatus.RUNNING, JobStatus.CANCELED)
        assert validate_transition(JobStatus.PAUSED, JobStatus.CANCELED)
