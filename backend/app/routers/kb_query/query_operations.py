"""
Business Logic for KB Query Operations
Service layer handling query orchestration.
"""

import logging
from typing import Any, cast

from app.services.kb import MultiKBQueryService, QueryProfile

logger = logging.getLogger(__name__)


class KBQueryService:
    """Stateless service layer for KB query operations."""

    def __init__(self) -> None:
        """Initialize the service."""
        pass

    def query_with_profile(
        self,
        service: MultiKBQueryService,
        question: str,
        profile: QueryProfile,
        top_k_per_kb: int | None = None,
    ) -> dict[str, Any]:
        """
        Query knowledge bases using specified profile.

        Args:
            service: Multi-source query service
            question: Question to ask
            profile: Query profile (CHAT or PROPOSAL)
            top_k_per_kb: Results per KB

        Returns:
            Query result dictionary
        """
        logger.info(f"{profile.value} query: {question[:100]}")
        result = service.query_profile(
            question=question, profile=profile, top_k_per_kb=top_k_per_kb
        )
        return cast(dict[str, Any], result)

    def query_specific_kbs(
        self,
        service: MultiKBQueryService,
        question: str,
        kb_ids: list[str],
        top_k_per_kb: int = 5,
    ) -> dict[str, Any]:
        """
        Query specific knowledge bases manually.

        Args:
            service: Multi-source query service
            question: Question to ask
            kb_ids: List of KB IDs to query
            top_k_per_kb: Results per KB

        Returns:
            Query result dictionary
        """
        logger.info(f"KB Query for KBs: {kb_ids}, question: {question[:100]}")
        result = service.query_kbs(
            question=question, kb_ids=kb_ids, top_k_per_kb=top_k_per_kb
        )
        return cast(dict[str, Any], result)


def get_query_service() -> KBQueryService:
    """Get singleton query service instance"""
    return KBQueryService()

