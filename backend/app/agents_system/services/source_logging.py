"""Helpers for recording sources (reference docs + MCP queries) in ProjectState.

Phase 2 scope (T009): provide low-level helpers that create typed source records
and return update payloads suitable for merge-based state updates.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from .aaa_state_models import (
    MCPQuery,
    MCPQueryPhase,
    ReferenceDocument,
    SourceCitation,
    SourceCitationKind,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_reference_document(
    *,
    category: str,
    title: str,
    url: str | None = None,
    accessed_at: str | None = None,
    document_id: str | None = None,
) -> ReferenceDocument:
    return ReferenceDocument(
        id=document_id or str(uuid.uuid4()),
        category=category,
        title=title,
        url=url,
        accessedAt=accessed_at or _now_iso(),
    )


def new_mcp_query(  # noqa: PLR0913
    *,
    query_text: str,
    phase: MCPQueryPhase,
    result_urls: list[str] | None = None,
    selected_snippets: list[str] | None = None,
    executed_at: str | None = None,
    query_id: str | None = None,
) -> MCPQuery:
    return MCPQuery(
        id=query_id or str(uuid.uuid4()),
        queryText=query_text,
        phase=phase,
        resultUrls=result_urls or [],
        selectedSnippets=selected_snippets,
        executedAt=executed_at or _now_iso(),
    )


def new_reference_citation(
    *,
    reference_document_id: str,
    url: str | None = None,
    note: str | None = None,
    citation_id: str | None = None,
) -> SourceCitation:
    return SourceCitation(
        id=citation_id or str(uuid.uuid4()),
        kind=SourceCitationKind.reference_document,
        referenceDocumentId=reference_document_id,
        url=url,
        note=note,
    )


def new_mcp_citation(
    *,
    mcp_query_id: str,
    url: str | None = None,
    note: str | None = None,
    citation_id: str | None = None,
) -> SourceCitation:
    return SourceCitation(
        id=citation_id or str(uuid.uuid4()),
        kind=SourceCitationKind.mcp,
        mcpQueryId=mcp_query_id,
        url=url,
        note=note,
    )


def append_reference_document_update(doc: ReferenceDocument) -> dict[str, Any]:
    """Return a state update payload that appends a reference document."""
    return {"referenceDocuments": [doc.model_dump()]}


def append_mcp_query_update(query: MCPQuery) -> dict[str, Any]:
    """Return a state update payload that appends an MCP query."""
    return {"mcpQueries": [query.model_dump()]}

