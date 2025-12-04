"""
Business Logic for KB Query Operations
Service layer handling query orchestration.
"""

import logging
from typing import Dict, Any, List, Optional

from services.kb_query import MultiSourceQueryService, QueryProfile

logger = logging.getLogger(__name__)


class KBQueryService:
    """Service layer for KB query operations"""
    
    def __init__(self):
        pass
    
    def query_with_profile(
        self,
        service: MultiSourceQueryService,
        question: str,
        profile: QueryProfile,
        top_k_per_kb: Optional[int] = None
    ) -> Dict[str, Any]:
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
            question=question,
            profile=profile,
            top_k_per_kb=top_k_per_kb
        )
        return result
    
    def query_specific_kbs(
        self,
        service: MultiSourceQueryService,
        question: str,
        kb_ids: List[str],
        top_k_per_kb: int = 5
    ) -> Dict[str, Any]:
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
            question=question,
            kb_ids=kb_ids,
            top_k_per_kb=top_k_per_kb
        )
        return result


# Singleton instance
_query_service = None


def get_query_service() -> KBQueryService:
    """Get singleton query service instance"""
    global _query_service
    if _query_service is None:
        _query_service = KBQueryService()
    return _query_service
