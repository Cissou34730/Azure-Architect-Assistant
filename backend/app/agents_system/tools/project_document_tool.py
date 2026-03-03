"""Project document search tool for agents.

Allows the agent to query uploaded project document contents by keyword,
so it can recall specific information from the original documents
during the conversation.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import BaseTool
from pydantic import PrivateAttr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import ProjectDocument

logger = logging.getLogger(__name__)

# Maximum excerpt length returned per match
_EXCERPT_CONTEXT_CHARS = 500


def _find_keyword_excerpts(
    text: str, query: str, max_excerpts: int = 3
) -> list[str]:
    """Find excerpts around keyword matches in text.

    Uses case-insensitive search for each query word.
    Returns up to max_excerpts context windows around matches.
    """
    if not text or not query:
        return []

    query_words = [w for w in query.lower().split() if len(w) >= 3]
    if not query_words:
        query_words = query.lower().split()

    excerpts: list[str] = []
    text_lower = text.lower()
    seen_positions: set[int] = set()

    for word in query_words:
        start = 0
        while start < len(text_lower) and len(excerpts) < max_excerpts:
            pos = text_lower.find(word, start)
            if pos < 0:
                break

            # Avoid overlapping excerpts
            bucket = pos // _EXCERPT_CONTEXT_CHARS
            if bucket in seen_positions:
                start = pos + len(word)
                continue
            seen_positions.add(bucket)

            # Extract context window around match
            excerpt_start = max(0, pos - _EXCERPT_CONTEXT_CHARS // 2)
            excerpt_end = min(len(text), pos + len(word) + _EXCERPT_CONTEXT_CHARS // 2)
            excerpt = text[excerpt_start:excerpt_end].strip()

            if excerpt_start > 0:
                excerpt = "..." + excerpt
            if excerpt_end < len(text):
                excerpt = excerpt + "..."

            excerpts.append(excerpt)
            start = pos + len(word)

    return excerpts


async def search_project_documents(
    project_id: str,
    query: str,
    db: AsyncSession,
    max_results: int = 5,
) -> list[dict[str, Any]]:
    """Search uploaded project documents by keyword.

    Performs case-insensitive keyword matching on parsed document text.
    Returns matching excerpts with document metadata.

    Args:
        project_id: Project to search in
        query: Search keywords
        db: Database session
        max_results: Maximum number of results to return

    Returns:
        List of dicts with documentId, fileName, excerpt
    """
    result = await db.execute(
        select(ProjectDocument).where(
            ProjectDocument.project_id == project_id,
            ProjectDocument.parse_status == "parsed",
        )
    )
    documents = result.scalars().all()

    if not documents:
        return []

    results: list[dict[str, Any]] = []
    for doc in documents:
        text = (doc.raw_text or "").strip()
        if not text:
            continue

        excerpts = _find_keyword_excerpts(text, query)
        if excerpts:
            for excerpt in excerpts:
                results.append(
                    {
                        "documentId": doc.id,
                        "fileName": doc.file_name,
                        "excerpt": excerpt,
                    }
                )
                if len(results) >= max_results:
                    return results

    return results


class ProjectDocumentSearchTool(BaseTool):
    """Tool for agents to search uploaded project documents by keyword.

    This enables the agent to recall specific content from project documents
    that were uploaded and parsed, even if that content wasn't captured
    in the extracted project state.

    The project_id is pre-bound at construction, so the LLM only needs
    to supply the search query.
    """

    name: str = "project_document_search"
    description: str = (
        "Search the uploaded project documents by keyword to find specific content. "
        "Use this tool when you need to recall details from the original project documents "
        "(RFP, specifications, architecture docs) that may not be fully captured in the "
        "project state summary. "
        'Input: a search query string (e.g., "authentication requirements" or "data residency"). '
        "Output: List of matching excerpts with document names."
    )

    _db_factory: Any = PrivateAttr(default=None)
    _project_id: str = PrivateAttr(default="")

    def __init__(
        self,
        db_factory: Any = None,
        project_id: str = "",
        **kwargs: Any,
    ):
        super().__init__(**kwargs)
        self._db_factory = db_factory
        self._project_id = project_id

    def _run(self, payload: str | dict | Any) -> str:
        """Sync wrapper — delegates to async."""
        import asyncio

        return asyncio.run(self._arun(payload))

    async def _arun(self, payload: str | dict | Any) -> str:
        """Search project documents asynchronously."""
        import json as _json

        # Parse input — accept plain string or dict
        if isinstance(payload, str):
            try:
                parsed = _json.loads(payload)
                query = parsed.get("query", payload) if isinstance(parsed, dict) else payload
            except _json.JSONDecodeError:
                query = payload
        elif isinstance(payload, dict):
            query = payload.get("query", "")
        else:
            query = str(payload)

        project_id = self._project_id
        if not project_id or not query:
            return "Error: Both project context and query are required."

        if self._db_factory is None:
            return "Error: Database session not configured for document search tool."

        async with self._db_factory() as db:
            results = await search_project_documents(project_id, query, db)

        if not results:
            return f"No matches found in project documents for: {query}"

        # Format results for agent consumption
        lines = [f"Found {len(results)} match(es) in project documents:\n"]
        for r in results:
            lines.append(f"**{r['fileName']}** (id: {r['documentId']})")
            lines.append(f"   {r['excerpt']}\n")

        return "\n".join(lines)
