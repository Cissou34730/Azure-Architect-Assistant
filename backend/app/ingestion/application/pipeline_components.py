from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from app.ingestion.domain.chunking.adapter import create_chunker_from_config
from app.ingestion.domain.embedding import Embedder
from app.ingestion.domain.indexing import Indexer
from app.ingestion.domain.loading import fetch_batches


@dataclass
class PipelineComponents:
    loader: Iterator[Any]
    chunker: Any
    embedder: Embedder
    indexer: Indexer


def create_pipeline_components(
    kb_id: str, kb_config: dict[str, Any], checkpoint: dict[str, Any]
) -> PipelineComponents:
    loader = fetch_batches(kb_config, checkpoint)
    chunker = create_chunker_from_config(kb_config)
    embedder = Embedder(model_name=kb_config.get('embedding_model', 'text-embedding-3-small'))
    indexer = Indexer(kb_id=kb_id)
    return PipelineComponents(loader=loader, chunker=chunker, embedder=embedder, indexer=indexer)
