from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from app.ingestion.application.pipeline_stage import PipelineContext
from app.ingestion.application.policies import RetryPolicy
from app.ingestion.application.stages.chunking_stage import ChunkingStage
from app.ingestion.application.stages.embedding_stage import EmbeddingStage
from app.ingestion.application.stages.loading_stage import LoadingStage


class FakePhaseRepo:
    def __init__(self) -> None:
        self.started: list[tuple[str, str]] = []
        self.progress: list[tuple[str, str, dict[str, Any]]] = []

    def start_phase(self, job_id: str, phase_name: str) -> None:
        self.started.append((job_id, phase_name))

    def update_progress(self, job_id: str, phase_name: str, **kwargs: Any) -> None:
        self.progress.append((job_id, phase_name, dict(kwargs)))

    def complete_phase(self, job_id: str, phase_name: str) -> None:  # pragma: no cover
        raise AssertionError('not used in these unit tests')

    def fail_phase(self, job_id: str, phase_name: str, *, error_message: str) -> None:  # pragma: no cover
        raise AssertionError('not used in these unit tests')


class FakeJobRepo:
    def __init__(self) -> None:
        self.status_updates: list[tuple[str, str]] = []
        self.job_updates: list[tuple[str, dict[str, Any], dict[str, int]]] = []

    def set_job_status(self, job_id: str, *, status: str) -> None:
        self.status_updates.append((job_id, status))

    def update_job(self, job_id: str, *, checkpoint: dict[str, Any], counters: dict[str, int]) -> None:
        self.job_updates.append((job_id, dict(checkpoint), dict(counters)))


@dataclass(frozen=True)
class FakeChunk:
    content_hash: str


class FakeEmbedder:
    async def embed(self, chunk: FakeChunk) -> dict[str, Any]:
        return {'hash': chunk.content_hash}


class FakeIndexer:
    def __init__(self, existing: set[str] | None = None) -> None:
        self._existing = existing or set()
        self.indexed: list[tuple[str, dict[str, Any]]] = []

    def exists(self, kb_id: str, content_hash: str) -> bool:
        return content_hash in self._existing

    def index(self, kb_id: str, embedding: dict[str, Any]) -> None:
        self.indexed.append((kb_id, embedding))


@pytest.mark.asyncio
async def test_loading_stage_increments_docs_and_updates_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, list[int]]] = []

    def fake_save_documents_to_disk(kb_id: str, batch: list[int]) -> None:
        calls.append((kb_id, list(batch)))

    monkeypatch.setattr(
        'app.ingestion.application.stages.loading_stage.save_documents_to_disk',
        fake_save_documents_to_disk,
    )

    phase_repo = FakePhaseRepo()
    stage = LoadingStage(phase_repo)

    context = PipelineContext(
        kb_id='kb1',
        job_id='job1',
        config={},
        checkpoint={},
        counters={'docs_seen': 0},
        results={'batch': [1, 2, 3]},
    )

    await stage.execute(context)

    assert calls == [('kb1', [1, 2, 3])]
    assert context.counters['docs_seen'] == 3
    assert phase_repo.progress[-1][1] == 'loading'
    assert phase_repo.progress[-1][2]['items_processed'] == 3


@pytest.mark.asyncio
async def test_chunking_stage_sets_chunks_and_updates_progress(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_chunk_documents_to_chunks(batch: list[str], chunker: Any, kb_id: str) -> list[FakeChunk]:
        assert chunker == 'chunker'
        assert kb_id == 'kb1'
        return [FakeChunk('a'), FakeChunk('b')]

    monkeypatch.setattr(
        'app.ingestion.application.stages.chunking_stage.chunk_documents_to_chunks',
        fake_chunk_documents_to_chunks,
    )

    phase_repo = FakePhaseRepo()
    stage = ChunkingStage(phase_repo, chunker='chunker')

    context = PipelineContext(
        kb_id='kb1',
        job_id='job1',
        config={},
        checkpoint={},
        counters={'chunks_seen': 0},
        results={'batch': ['doc1']},
    )

    await stage.execute(context)

    chunks = context.results['chunks']
    assert isinstance(chunks, list)
    assert [c.content_hash for c in chunks] == ['a', 'b']
    assert context.counters['chunks_seen'] == 2
    assert ('job1', 'chunking') in phase_repo.started


@pytest.mark.asyncio
async def test_embedding_stage_processes_and_counts(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = FakeJobRepo()
    phase_repo = FakePhaseRepo()
    indexer = FakeIndexer()

    async def gate_check(job_id: str, kb_id: str, _indexer: FakeIndexer) -> bool:
        assert job_id == 'job1'
        assert kb_id == 'kb1'
        return True

    def is_shutdown_requested() -> bool:
        return False

    stage = EmbeddingStage(
        repo=repo,
        phase_repo=phase_repo,
        retry_policy=RetryPolicy(max_attempts=1),
        embedder=FakeEmbedder(),
        indexer=indexer,
        gate_check=gate_check,
        is_shutdown_requested=is_shutdown_requested,
    )

    context = PipelineContext(
        kb_id='kb1',
        job_id='job1',
        config={},
        checkpoint={},
        counters={'chunks_processed': 0, 'chunks_skipped': 0, 'chunks_error': 0},
        results={'chunks': [FakeChunk('a'), FakeChunk('b')], 'batch_id': 7},
    )

    await stage.execute(context)

    assert context.counters['chunks_processed'] == 2
    assert context.results['continue'] is True
    assert len(indexer.indexed) == 2
    assert ('job1', 'embedding') in phase_repo.started
    assert ('job1', 'indexing') in phase_repo.started


@pytest.mark.asyncio
async def test_embedding_stage_skips_existing_chunks() -> None:
    repo = FakeJobRepo()
    phase_repo = FakePhaseRepo()
    indexer = FakeIndexer(existing={'a'})

    async def gate_check(_job_id: str, _kb_id: str, _indexer: FakeIndexer) -> bool:
        return True

    stage = EmbeddingStage(
        repo=repo,
        phase_repo=phase_repo,
        retry_policy=RetryPolicy(max_attempts=1),
        embedder=FakeEmbedder(),
        indexer=indexer,
        gate_check=gate_check,
        is_shutdown_requested=lambda: False,
    )

    context = PipelineContext(
        kb_id='kb1',
        job_id='job1',
        config={},
        checkpoint={},
        counters={'chunks_processed': 0, 'chunks_skipped': 0, 'chunks_error': 0},
        results={'chunks': [FakeChunk('a'), FakeChunk('b')], 'batch_id': 7},
    )

    await stage.execute(context)

    assert context.counters['chunks_skipped'] == 1
    assert context.counters['chunks_processed'] == 1
    assert len(indexer.indexed) == 1
