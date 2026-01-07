"""
Unit tests for orchestrator components.
Tests: content_hash, idempotency, RetryPolicy, WorkflowDefinition
"""

from backend.app.ingestion.domain.chunking.adapter import compute_content_hash
from backend.app.ingestion.application.orchestrator import (
    WorkflowDefinition,
    RetryPolicy,
    StepName,
)


class TestContentHash:
    """Test content hash determinism and normalization."""

    def test_compute_content_hash_deterministic(self):
        """Same input produces same hash."""
        text = "Hello World"
        kb_id = "kb-123"
        source_id = "doc-456"

        hash1 = compute_content_hash(text, kb_id, source_id)
        hash2 = compute_content_hash(text, kb_id, source_id)

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length

    def test_compute_content_hash_strip_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        kb_id = "kb-123"
        source_id = "doc-456"

        hash1 = compute_content_hash("  Hello World  ", kb_id, source_id)
        hash2 = compute_content_hash("Hello World", kb_id, source_id)

        assert hash1 == hash2

    def test_compute_content_hash_different_kb(self):
        """Different kb_id produces different hash."""
        text = "Hello World"
        source_id = "doc-456"

        hash1 = compute_content_hash(text, "kb-123", source_id)
        hash2 = compute_content_hash(text, "kb-999", source_id)

        assert hash1 != hash2

    def test_compute_content_hash_different_source(self):
        """Different source_id produces different hash."""
        text = "Hello World"
        kb_id = "kb-123"

        hash1 = compute_content_hash(text, kb_id, "doc-456")
        hash2 = compute_content_hash(text, kb_id, "doc-999")

        assert hash1 != hash2


class TestWorkflowDefinition:
    """Test workflow step sequencing."""

    def test_get_first_step(self):
        """First step is LOAD."""
        wf = WorkflowDefinition()
        assert wf.get_first_step() == StepName.LOAD

    def test_get_next_step_sequence(self):
        """Steps follow load → chunk → embed → index → None."""
        wf = WorkflowDefinition()

        assert wf.get_next_step(StepName.LOAD) == StepName.CHUNK
        assert wf.get_next_step(StepName.CHUNK) == StepName.EMBED
        assert wf.get_next_step(StepName.EMBED) == StepName.INDEX
        assert wf.get_next_step(StepName.INDEX) is None

    def test_get_next_step_invalid(self):
        """Unknown step returns None."""
        wf = WorkflowDefinition()
        # This won't happen in practice due to enum, but tests robustness
        assert wf.get_next_step(None) is None


class TestRetryPolicy:
    """Test retry logic and backoff."""

    def test_should_retry_within_max(self):
        """Retry if attempts < max."""
        policy = RetryPolicy(max_attempts=3)
        error = Exception("test error")
        assert policy.should_retry(0, error)
        assert policy.should_retry(1, error)
        assert policy.should_retry(2, error)

    def test_should_retry_exceeds_max(self):
        """No retry if attempts >= max."""
        policy = RetryPolicy(max_attempts=3)
        error = Exception("test error")
        assert not policy.should_retry(3, error)
        assert not policy.should_retry(4, error)

    def test_get_backoff_delay_exponential(self):
        """Backoff grows exponentially: 2^attempt * multiplier."""
        policy = RetryPolicy(max_attempts=5, backoff_multiplier=2.0)

        assert policy.get_backoff_delay(0) == 2.0  # 2^0 * 2.0
        assert policy.get_backoff_delay(1) == 4.0  # 2^1 * 2.0
        assert policy.get_backoff_delay(2) == 8.0  # 2^2 * 2.0
        assert policy.get_backoff_delay(3) == 16.0  # 2^3 * 2.0

    def test_get_backoff_delay_custom_multiplier(self):
        """Custom backoff multiplier works."""
        policy = RetryPolicy(max_attempts=3, backoff_multiplier=1.0)

        assert policy.get_backoff_delay(0) == 1.0  # 2^0 * 1.0
        assert policy.get_backoff_delay(1) == 2.0  # 2^1 * 1.0
        assert policy.get_backoff_delay(2) == 4.0  # 2^2 * 1.0
