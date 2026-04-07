"""Orchestration layer for KB query API endpoints."""

import logging
from typing import Any, cast

from app.features.knowledge.infrastructure import KBManager, KnowledgeBaseService

from .query_service import MultiKBQueryService, QueryProfile

logger = logging.getLogger(__name__)


class KBQueryService:
    """Stateless orchestration for profile and manual KB query flows."""

    def get_ready_kbs_for_profile(self, kb_manager: KBManager, profile: QueryProfile) -> list[object]:
        return [
            kb
            for kb in kb_manager.get_kbs_for_profile(profile.value)
            if KnowledgeBaseService(kb).is_index_ready()
        ]

    def get_ready_selected_kb_ids(self, kb_manager: KBManager, kb_ids: list[str]) -> list[str]:
        return [
            kb_id
            for kb_id in kb_ids
            if (kb_config := kb_manager.get_kb(kb_id))
            and KnowledgeBaseService(kb_config).is_index_ready()
        ]

    def query_with_profile(
        self,
        service: MultiKBQueryService,
        question: str,
        profile: QueryProfile,
        top_k_per_kb: int | None = None,
    ) -> dict[str, Any]:
        logger.info("%s query: %s", profile.value, question[:100])
        effective_top_k = top_k_per_kb if top_k_per_kb is not None else 3
        result = service.query_profile(
            question=question,
            profile=profile,
            top_k_per_kb=effective_top_k,
        )
        return cast(dict[str, Any], result)

    def query_specific_kbs(
        self,
        service: MultiKBQueryService,
        question: str,
        kb_ids: list[str],
        top_k_per_kb: int = 5,
    ) -> dict[str, Any]:
        logger.info("KB Query for KBs: %s, question: %s", kb_ids, question[:100])
        result = service.query_kbs(
            question=question,
            kb_ids=kb_ids,
            top_k_per_kb=top_k_per_kb,
        )
        return cast(dict[str, Any], result)


_query_service = KBQueryService()


def get_query_service() -> KBQueryService:
    """Get query orchestration service instance."""
    return _query_service
