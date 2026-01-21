"""
Integration tests for orchestrator flows.
Tests: start/pause/resume/cancel with cleanup, checkpoint resume, idempotency
"""

from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Legacy orchestrator tests; skip until rebuilt for new orchestrator
pytest.skip(
    "Legacy orchestrator tests - to be rebuilt for new orchestrator",
    allow_module_level=True,
)


# Mock placeholder for linting purposes since tests are skipped
class IngestionOrchestrator:
    """Placeholder for legacy orchestrator."""

    def __init__(self, **kwargs):
        pass


# Minimal stand-in for job view object
@dataclass
class JobView:
    id: str
    kb_id: str
    status: str
    checkpoint: dict | None
    counters: dict | None


class TestOrchestratorGates:
    """Test pause/resume/cancel gates."""

    @pytest.mark.asyncio
    async def test_pause_and_resume(self):
        """Orchestrator pauses when status=paused, resumes on running."""
        # Mock repository with pause → resume sequence
        mock_repo = MagicMock()
        mock_repo.get_job_status = MagicMock(
            side_effect=[
                "running",  # Initial check
                "paused",  # First gate check → pause
                "paused",  # Loop while paused
                "running",  # Resume
                "running",  # Continue
            ]
        )
        mock_repo.update_job = MagicMock()
        mock_repo.update_heartbeat = MagicMock()
        mock_repo.get_job = MagicMock(
            return_value=JobView(
                id="job-1",
                kb_id="kb-1",
                status="running",
                checkpoint=None,
                counters=None,
            )
        )

        # Mock domain adapters to yield one batch
        mock_loader = AsyncMock(
            return_value=iter([[MagicMock(id="doc-1", text="content")]])
        )
        mock_chunker = MagicMock(
            return_value=[MagicMock(content_hash="hash1", text="chunk")]
        )
        mock_embedder = AsyncMock()
        mock_indexer = MagicMock()
        mock_indexer.exists = MagicMock(return_value=False)
        mock_indexer.index = MagicMock()

        orchestrator = IngestionOrchestrator(
            repository=mock_repo,
            loader=mock_loader,
            chunker=mock_chunker,
            embedder=mock_embedder,
            indexer=mock_indexer,
        )

        # Run orchestrator (should pause then resume)
        with patch("asyncio.sleep", new_callable=AsyncMock):  # Skip actual sleep
            await orchestrator.run("job-1", "kb-1", {})

        # Verify pause behavior: status checked multiple times
        assert mock_repo.get_job_status.call_count >= 3
        assert mock_repo.update_heartbeat.called

    @pytest.mark.asyncio
    async def test_cancel_triggers_cleanup(self):
        """Cancel status triggers cleanup: delete vectors + reset state."""
        mock_repo = MagicMock()
        mock_repo.get_job_status = MagicMock(
            side_effect=[
                "running",  # Initial
                "canceled",  # Gate check → cancel
            ]
        )
        mock_repo.get_job = MagicMock(
            return_value=JobView(
                id="job-1",
                kb_id="kb-1",
                status="running",
                checkpoint=None,
                counters=None,
            )
        )
        mock_repo.update_job = MagicMock()

        mock_indexer = MagicMock()
        mock_indexer.delete_by_job = MagicMock()

        orchestrator = IngestionOrchestrator(
            repository=mock_repo,
            loader=AsyncMock(),
            chunker=MagicMock(),
            embedder=AsyncMock(),
            indexer=mock_indexer,
        )

        await orchestrator.run("job-1", "kb-1", {})

        # Verify cleanup called
        mock_indexer.delete_by_job.assert_called_once_with("job-1", "kb-1")

        # Verify state reset
        mock_repo.update_job.assert_called()
        args = mock_repo.update_job.call_args
        assert args[1]["status"] == "not_started"
        assert args[1]["checkpoint"] is None
        assert args[1]["counters"] is None


class TestOrchestratorCheckpoint:
    """Test checkpoint resume."""

    @pytest.mark.asyncio
    async def test_resume_from_checkpoint(self):
        """Orchestrator resumes from last_batch_id checkpoint."""
        checkpoint = {"last_batch_id": 5, "cursor": None}
        counters = {"docs_seen": 10, "chunks_seen": 20, "chunks_processed": 15}

        mock_repo = MagicMock()
        mock_repo.get_job = MagicMock(
            return_value=JobView(
                id="job-1",
                kb_id="kb-1",
                status="running",
                checkpoint=checkpoint,
                counters=counters,
            )
        )
        mock_repo.get_job_status = MagicMock(return_value="running")
        mock_repo.update_job = MagicMock()
        mock_repo.update_heartbeat = MagicMock()

        # Mock loader to verify checkpoint passed
        mock_loader = AsyncMock(return_value=iter([]))  # No more batches

        orchestrator = IngestionOrchestrator(
            repository=mock_repo,
            loader=mock_loader,
            chunker=MagicMock(),
            embedder=AsyncMock(),
            indexer=MagicMock(),
        )

        await orchestrator.run("job-1", "kb-1", {})

        # Verify loader received checkpoint
        mock_loader.assert_called_once()
        call_args = mock_loader.call_args
        assert call_args[1]["checkpoint"] == checkpoint


class TestOrchestratorIdempotency:
    """Test idempotency via content_hash."""

    @pytest.mark.asyncio
    async def test_skip_existing_chunk(self):
        """Chunks already indexed (exists=True) are skipped."""
        mock_repo = MagicMock()
        mock_repo.get_job = MagicMock(
            return_value=JobView(
                id="job-1",
                kb_id="kb-1",
                status="running",
                checkpoint=None,
                counters=None,
            )
        )
        mock_repo.get_job_status = MagicMock(
            return_value="completed"
        )  # Complete after one batch
        mock_repo.update_job = MagicMock()
        mock_repo.update_heartbeat = MagicMock()

        # Mock one batch with one doc → one chunk
        mock_doc = MagicMock(id="doc-1", text="content")
        mock_loader = AsyncMock(return_value=iter([[mock_doc]]))

        mock_chunk = MagicMock(content_hash="hash-exists", text="chunk")
        mock_chunker = MagicMock(return_value=[mock_chunk])

        # Indexer says chunk already exists
        mock_indexer = MagicMock()
        mock_indexer.exists = MagicMock(return_value=True)
        mock_indexer.index = MagicMock()

        mock_embedder = AsyncMock()

        orchestrator = IngestionOrchestrator(
            repository=mock_repo,
            loader=mock_loader,
            chunker=mock_chunker,
            embedder=mock_embedder,
            indexer=mock_indexer,
        )

        await orchestrator.run("job-1", "kb-1", {})

        # Verify chunk was checked for existence
        mock_indexer.exists.assert_called_once_with("kb-1", "hash-exists")

        # Verify embed and index NOT called (skipped)
        mock_embedder.assert_not_called()
        mock_indexer.index.assert_not_called()

        # Verify counters reflect skip
        update_calls = mock_repo.update_job.call_args_list
        final_call = update_calls[-1]
        counters = final_call[1]["counters"]
        assert counters["chunks_skipped"] == 1
        assert counters["chunks_processed"] == 0

