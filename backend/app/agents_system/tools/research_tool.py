"""Unified research facade and typed contracts for grounded runtime evidence."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from enum import Enum
from typing import Any, Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.agents_system.agents.rag_agent import RAGAgent
from app.shared.mcp.learn_mcp_client import MicrosoftLearnMCPClient
from app.shared.mcp.operations.learn_operations import (
    fetch_documentation,
    search_microsoft_docs,
)

from .project_document_tool import search_project_documents

_EVIDENCE_MODEL_CONFIG = ConfigDict(
    populate_by_name=True,
    alias_generator=to_camel,
    extra="forbid",
)
_PACKET_MODEL_CONFIG = ConfigDict(
    populate_by_name=True,
    extra="forbid",
)
_RESEARCH_QUERY_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{2,}")
_SOURCE_PRIORITY = {
    "project_document": 0,
    "microsoft_docs": 1,
    "kb": 2,
}


class ResearchScope(str, Enum):
    PROJECT = "project"
    KB = "kb"
    MICROSOFT_DOCS = "microsoft_docs"
    ALL = "all"


class EvidencePacket(BaseModel):
    """Typed evidence item used across runtime research consumers."""

    model_config = _EVIDENCE_MODEL_CONFIG

    id: str
    source: str
    title: str
    excerpt: str
    url: str | None = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    source_document: str | None = None


class GroundedResearchPacket(BaseModel):
    """Typed packet passed from research planning into synthesis/runtime consumers."""

    model_config = _PACKET_MODEL_CONFIG

    packet_id: str
    focus: str
    query: str
    stage: str
    requirement_targets: list[str] = Field(default_factory=list)
    mindmap_topics: list[str] = Field(default_factory=list)
    recommended_sources: list[str] = Field(default_factory=list)
    expected_evidence: list[str] = Field(default_factory=list)
    consumer_guidance: str
    evidence: list[EvidencePacket] = Field(default_factory=list)
    consulted_sources: list[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("consultedSources", "consulted_sources"),
        serialization_alias="consultedSources",
    )
    grounding_status: Literal["planned", "grounded"] = Field(
        default="planned",
        validation_alias=AliasChoices("groundingStatus", "grounding_status"),
        serialization_alias="groundingStatus",
    )


class ResearchExecutionArtifact(BaseModel):
    """Typed metadata emitted by the research worker."""

    model_config = _PACKET_MODEL_CONFIG

    status: Literal["completed", "skipped"]
    stage: str
    packets_created: int
    plan_items: int | None = None
    reason: str | None = None
    grounded_packets: int | None = Field(
        default=None,
        validation_alias=AliasChoices("groundedPackets", "grounded_packets"),
        serialization_alias="groundedPackets",
    )


class ResearchResult(BaseModel):
    """Unified research result returned by the facade."""

    model_config = _EVIDENCE_MODEL_CONFIG

    query: str
    scope: ResearchScope
    consulted_sources: list[str] = Field(default_factory=list)
    evidence: list[dict[str, Any]] = Field(default_factory=list)


ProjectSearchFn = Callable[[str], Awaitable[list[dict[str, Any]]]]
KBSearchFn = Callable[[str], Awaitable[dict[str, Any]]]
MicrosoftDocsSearchFn = Callable[[str], Awaitable[dict[str, Any]]]
MicrosoftDocsFetchFn = Callable[[str], Awaitable[dict[str, Any]]]


class ResearchFacade:
    """Deterministic facade that unifies project, KB, and Microsoft docs research."""

    def __init__(
        self,
        *,
        project_search: ProjectSearchFn | None = None,
        kb_search: KBSearchFn | None = None,
        microsoft_docs_search: MicrosoftDocsSearchFn | None = None,
        microsoft_docs_fetch: MicrosoftDocsFetchFn | None = None,
    ) -> None:
        self._project_search = project_search
        self._kb_search = kb_search
        self._microsoft_docs_search = microsoft_docs_search
        self._microsoft_docs_fetch = microsoft_docs_fetch

    async def research(
        self,
        query: str,
        scope: ResearchScope = ResearchScope.ALL,
    ) -> ResearchResult:
        consulted_sources: list[str] = []
        evidence_packets: list[EvidencePacket] = []

        if scope in {ResearchScope.ALL, ResearchScope.PROJECT} and self._project_search is not None:
            consulted_sources.append("project_document")
            evidence_packets.extend(await self._search_project_documents(query))

        if scope in {ResearchScope.ALL, ResearchScope.KB} and self._kb_search is not None:
            consulted_sources.append("kb")
            evidence_packets.extend(await self._search_kb(query))

        if scope in {ResearchScope.ALL, ResearchScope.MICROSOFT_DOCS} and self._microsoft_docs_search is not None:
            consulted_sources.append("microsoft_docs")
            evidence_packets.extend(await self._search_microsoft_docs(query))

        ranked_packets = sorted(
            evidence_packets,
            key=lambda packet: (
                _SOURCE_PRIORITY.get(packet.source, 99),
                -packet.relevance_score,
                packet.title.lower(),
            ),
        )
        return ResearchResult(
            query=query,
            scope=scope,
            consulted_sources=consulted_sources,
            evidence=[packet.model_dump(mode="json", by_alias=True) for packet in ranked_packets],
        )

    async def _search_project_documents(self, query: str) -> list[EvidencePacket]:
        if self._project_search is None:
            return []
        results = await self._project_search(query)
        packets: list[EvidencePacket] = []
        for index, item in enumerate(results, start=1):
            excerpt = str(item.get("excerpt") or "").strip()
            if not excerpt:
                continue
            source_document = str(item.get("fileName") or "").strip() or None
            packets.append(
                self._build_packet(
                    query=query,
                    payload={
                        "id": f"project-{item.get('documentId') or index}",
                        "source": "project_document",
                        "title": source_document or f"Project document {index}",
                        "excerpt": excerpt,
                        "url": None,
                        "source_document": source_document,
                    },
                )
            )
        return packets

    async def _search_kb(self, query: str) -> list[EvidencePacket]:
        if self._kb_search is None:
            return []
        result = await self._kb_search(query)
        raw_sources = result.get("sources") if isinstance(result, dict) else None
        if not isinstance(raw_sources, list):
            return []

        packets: list[EvidencePacket] = []
        for index, item in enumerate(raw_sources, start=1):
            if not isinstance(item, dict):
                continue
            title = str(item.get("title") or item.get("section") or f"KB result {index}").strip()
            excerpt = str(item.get("content") or item.get("excerpt") or "").strip()
            if not excerpt:
                continue
            packets.append(
                self._build_packet(
                    query=query,
                    payload={
                        "id": f"kb-{index}",
                        "source": "kb",
                        "title": title,
                        "excerpt": excerpt,
                        "url": _normalize_optional_text(item.get("url")),
                        "source_document": _normalize_optional_text(item.get("kb_name")),
                    },
                )
            )
        return packets

    async def _search_microsoft_docs(self, query: str) -> list[EvidencePacket]:
        if self._microsoft_docs_search is None:
            return []
        result = await self._microsoft_docs_search(query)
        raw_results = result.get("results") if isinstance(result, dict) else None
        if not isinstance(raw_results, list):
            return []

        packets: list[EvidencePacket] = []
        for index, item in enumerate(raw_results, start=1):
            if not isinstance(item, dict):
                continue
            url = _normalize_optional_text(item.get("contentUrl") or item.get("url"))
            excerpt = str(item.get("content") or item.get("excerpt") or "").strip()
            if url and self._microsoft_docs_fetch is not None:
                fetched = await self._microsoft_docs_fetch(url)
                if isinstance(fetched, dict):
                    fetched_content = str(fetched.get("content") or "").strip()
                    if fetched_content:
                        excerpt = fetched_content
            if not excerpt:
                continue
            packets.append(
                self._build_packet(
                    query=query,
                    payload={
                        "id": f"microsoft-docs-{index}",
                        "source": "microsoft_docs",
                        "title": str(item.get("title") or f"Microsoft Learn result {index}").strip(),
                        "excerpt": excerpt,
                        "url": url,
                        "source_document": None,
                    },
                )
            )
        return packets

    def _build_packet(self, *, query: str, payload: dict[str, Any]) -> EvidencePacket:
        return EvidencePacket(
            **payload,
            relevance_score=_calculate_relevance_score(
                query=query,
                title=str(payload.get("title") or ""),
                excerpt=str(payload.get("excerpt") or ""),
            ),
        )


def build_research_facade(
    *,
    project_id: str | None = None,
    db_session: AsyncSession | None = None,
    db_factory: async_sessionmaker[AsyncSession] | None = None,
    mcp_client: MicrosoftLearnMCPClient | None = None,
) -> ResearchFacade:
    return ResearchFacade(
        project_search=_build_project_search(
            project_id=project_id,
            db_session=db_session,
            db_factory=db_factory,
        ),
        kb_search=_build_kb_search(),
        microsoft_docs_search=_build_microsoft_docs_search(mcp_client),
        microsoft_docs_fetch=_build_microsoft_docs_fetch(mcp_client),
    )


def normalize_grounded_research_packet(observation: Any) -> GroundedResearchPacket | None:
    if isinstance(observation, GroundedResearchPacket):
        return observation
    if isinstance(observation, dict):
        try:
            return GroundedResearchPacket.model_validate(observation)
        except Exception:  # noqa: BLE001
            return None
    return None


def _build_project_search(
    *,
    project_id: str | None,
    db_session: AsyncSession | None,
    db_factory: async_sessionmaker[AsyncSession] | None,
) -> ProjectSearchFn | None:
    if not project_id:
        return None

    if db_session is not None:

        async def _search_with_session(query: str) -> list[dict[str, Any]]:
            return await search_project_documents(project_id, query, db_session)

        return _search_with_session

    if db_factory is None:
        return None

    async def _search_with_factory(query: str) -> list[dict[str, Any]]:
        async with db_factory() as db:
            return await search_project_documents(project_id, query, db)

    return _search_with_factory


def _build_kb_search() -> KBSearchFn:
    rag_agent = RAGAgent()

    async def _search(query: str) -> dict[str, Any]:
        return await asyncio.to_thread(rag_agent.execute, query, "chat")

    return _search


def _build_microsoft_docs_search(
    mcp_client: MicrosoftLearnMCPClient | None,
) -> MicrosoftDocsSearchFn | None:
    if mcp_client is None:
        return None

    async def _search(query: str) -> dict[str, Any]:
        return await search_microsoft_docs(mcp_client, query, 3)

    return _search


def _build_microsoft_docs_fetch(
    mcp_client: MicrosoftLearnMCPClient | None,
) -> MicrosoftDocsFetchFn | None:
    if mcp_client is None:
        return None

    async def _fetch(url: str) -> dict[str, Any]:
        return await fetch_documentation(mcp_client, url)

    return _fetch


def _normalize_optional_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _extract_query_terms(query: str) -> set[str]:
    return {token.lower() for token in _RESEARCH_QUERY_TOKEN_PATTERN.findall(query)}


def _calculate_relevance_score(*, query: str, title: str, excerpt: str) -> float:
    query_terms = _extract_query_terms(query)
    if not query_terms:
        return 0.0

    title_terms = _extract_query_terms(title)
    excerpt_terms = _extract_query_terms(excerpt)
    matched_title_terms = len(query_terms & title_terms)
    matched_excerpt_terms = len(query_terms & excerpt_terms)
    raw_score = (matched_title_terms * 2 + matched_excerpt_terms) / max(len(query_terms) * 3, 1)
    return round(min(max(raw_score, 0.0), 1.0), 3)


__all__ = [
    "EvidencePacket",
    "GroundedResearchPacket",
    "ResearchExecutionArtifact",
    "ResearchFacade",
    "ResearchResult",
    "ResearchScope",
    "build_research_facade",
    "normalize_grounded_research_packet",
]
