"""Helpers for recording sources (reference docs + MCP queries) in ProjectState.

Phase 2 scope (T009): provide low-level helpers that create typed source records
and return update payloads suitable for merge-based state updates.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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
    url: Optional[str] = None,
    accessed_at: Optional[str] = None,
    document_id: Optional[str] = None,
) -> ReferenceDocument:
    return ReferenceDocument(
        id=document_id or str(uuid.uuid4()),
        category=category,
        title=title,
        url=url,
        accessedAt=accessed_at or _now_iso(),
    )


def new_mcp_query(
    *,
    query_text: str,
    phase: MCPQueryPhase,
    result_urls: Optional[List[str]] = None,
    selected_snippets: Optional[List[str]] = None,
    executed_at: Optional[str] = None,
    query_id: Optional[str] = None,
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
    url: Optional[str] = None,
    note: Optional[str] = None,
    citation_id: Optional[str] = None,
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
    url: Optional[str] = None,
    note: Optional[str] = None,
    citation_id: Optional[str] = None,
) -> SourceCitation:
    return SourceCitation(
        id=citation_id or str(uuid.uuid4()),
        kind=SourceCitationKind.mcp,
        mcpQueryId=mcp_query_id,
        url=url,
        note=note,
    )


def append_reference_document_update(doc: ReferenceDocument) -> Dict[str, Any]:
    """Return a state update payload that appends a reference document."""
    return {"referenceDocuments": [doc.model_dump()]}


def append_mcp_query_update(query: MCPQuery) -> Dict[str, Any]:
    """Return a state update payload that appends an MCP query."""
    return {"mcpQueries": [query.model_dump()]}
