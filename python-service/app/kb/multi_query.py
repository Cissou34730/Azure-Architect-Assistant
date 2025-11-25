"""
Multi-Source Query Service
Handles querying multiple knowledge bases with profile-based selection.
"""

import logging
from typing import Dict, List, Optional
from enum import Enum
import asyncio

from .manager import KBManager, KBConfig
from .service import KnowledgeBaseService

logger = logging.getLogger(__name__)


class QueryProfile(str, Enum):
    """Query profiles for different use cases."""
    CHAT = "chat"
    PROPOSAL = "proposal"


class MultiSourceQueryService:
    """Service for querying multiple knowledge bases."""
    
    def __init__(self, kb_manager: KBManager):
        """
        Initialize multi-source query service.
        
        Args:
            kb_manager: Knowledge base manager
        """
        self.kb_manager = kb_manager
        self._kb_services: Dict[str, KnowledgeBaseService] = {}
        logger.info("MultiSourceQueryService initialized")
    
    def _get_kb_service(self, kb_config: KBConfig) -> KnowledgeBaseService:
        """Get or create KB service instance (cached)."""
        if kb_config.id not in self._kb_services:
            self._kb_services[kb_config.id] = KnowledgeBaseService(kb_config)
        return self._kb_services[kb_config.id]
    
    def query_profile(
        self,
        question: str,
        profile: QueryProfile,
        top_k_per_kb: int = 3,
        metadata_filters: Optional[Dict] = None
    ) -> Dict:
        """
        Query using a profile (chat or proposal).
        
        Args:
            question: Question to ask
            profile: QueryProfile.CHAT or QueryProfile.PROPOSAL
            top_k_per_kb: Results per KB (chat: 3, proposal: 5)
            metadata_filters: Optional filters
            
        Returns:
            Merged results from all KBs in profile
        """
        logger.info(f"Query with profile: {profile.value}")
        
        # Get KBs for profile
        kb_configs = self.kb_manager.get_kbs_for_profile(profile.value)
        
        if not kb_configs:
            logger.warning(f"No KBs found for profile: {profile.value}")
            return {
                'answer': f"No knowledge bases available for {profile.value} profile.",
                'sources': [],
                'has_results': False,
                'kbs_queried': []
            }
        
        logger.info(f"Querying {len(kb_configs)} KBs: {[kb.id for kb in kb_configs]}")
        
        # Query each KB
        all_results = []
        for kb_config in kb_configs:
            try:
                kb_service = self._get_kb_service(kb_config)
                result = kb_service.query(
                    question=question,
                    top_k=top_k_per_kb,
                    metadata_filters=metadata_filters
                )
                if result['has_results']:
                    all_results.append(result)
            except Exception as e:
                logger.error(f"Failed to query KB {kb_config.id}: {e}")
        
        if not all_results:
            return {
                'answer': "No relevant information found across knowledge bases.",
                'sources': [],
                'has_results': False,
                'kbs_queried': [kb.id for kb in kb_configs]
            }
        
        # Merge results
        return self._merge_results(all_results, question, profile)
    
    def _merge_results(
        self,
        all_results: List[Dict],
        question: str,
        profile: QueryProfile
    ) -> Dict:
        """
        Merge results from multiple KBs.
        
        Strategy:
        - Chat: Top 3 from each KB, simple concatenation
        - Proposal: Top 5 from each KB, comprehensive context
        """
        # Collect all sources
        all_sources = []
        for result in all_results:
            all_sources.extend(result['sources'])
        
        # Sort by score
        all_sources.sort(key=lambda s: s['score'], reverse=True)
        
        # Limit based on profile
        if profile == QueryProfile.CHAT:
            # Chat: Keep top 6 overall (2 per KB for 3 KBs)
            merged_sources = all_sources[:6]
        else:
            # Proposal: Keep top 15 (5 per KB for 3 KBs)
            merged_sources = all_sources[:15]
        
        # Build consolidated answer
        kb_names = list(set(r['kb_name'] for r in all_results))
        
        if profile == QueryProfile.CHAT:
            # Chat: Quick combined answer
            answer_parts = [f"Based on {', '.join(kb_names)}:\n"]
            for result in all_results:
                if result['answer']:
                    answer_parts.append(f"\n**{result['kb_name']}**: {result['answer']}")
            consolidated_answer = "\n".join(answer_parts)
        else:
            # Proposal: Comprehensive context (LLM will synthesize)
            contexts = []
            for i, result in enumerate(all_results, 1):
                contexts.append(f"### Context from {result['kb_name']}:\n{result['answer']}")
            consolidated_answer = "\n\n".join(contexts)
        
        return {
            'answer': consolidated_answer,
            'sources': merged_sources,
            'has_results': True,
            'kbs_queried': [r['kb_id'] for r in all_results],
            'kb_count': len(all_results)
        }
    
    def query_specific_kbs(
        self,
        question: str,
        kb_ids: List[str],
        top_k: int = 5,
        metadata_filters: Optional[Dict] = None
    ) -> Dict:
        """
        Query specific KBs by ID (for advanced use).
        
        Args:
            question: Question to ask
            kb_ids: List of KB IDs to query
            top_k: Results per KB
            metadata_filters: Optional filters
            
        Returns:
            Merged results from specified KBs
        """
        logger.info(f"Query specific KBs: {kb_ids}")
        
        all_results = []
        for kb_id in kb_ids:
            kb_config = self.kb_manager.get_kb(kb_id)
            if not kb_config or not kb_config.is_active:
                logger.warning(f"KB not found or inactive: {kb_id}")
                continue
            
            try:
                kb_service = self._get_kb_service(kb_config)
                result = kb_service.query(
                    question=question,
                    top_k=top_k,
                    metadata_filters=metadata_filters
                )
                if result['has_results']:
                    all_results.append(result)
            except Exception as e:
                logger.error(f"Failed to query KB {kb_id}: {e}")
        
        if not all_results:
            return {
                'answer': "No relevant information found.",
                'sources': [],
                'has_results': False,
                'kbs_queried': kb_ids
            }
        
        # Use chat profile strategy for specific queries
        return self._merge_results(all_results, question, QueryProfile.CHAT)
    
    def get_kb_health(self) -> Dict:
        """Get health status of all KBs."""
        kbs = self.kb_manager.get_active_kbs()
        health = {}
        
        for kb in kbs:
            try:
                service = self._get_kb_service(kb)
                health[kb.id] = {
                    'name': kb.name,
                    'status': 'ready' if service.is_index_ready() else 'not_indexed',
                    'profiles': kb.profiles,
                    'index_path': kb.index_path
                }
            except Exception as e:
                health[kb.id] = {
                    'name': kb.name,
                    'status': 'error',
                    'error': str(e)
                }
        
        return health
