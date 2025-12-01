"""
Business Logic for KB Query Operations
Service layer handling query orchestration.
"""

import logging
from typing import Dict, Any, List, Optional

from app.kb import MultiSourceQueryService, QueryProfile

logger = logging.getLogger(__name__)


class KBQueryService:
    """Service layer for KB query operations"""
    
    @staticmethod
    def query_with_profile(
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
    
    @staticmethod
    def query_specific_kbs(
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
