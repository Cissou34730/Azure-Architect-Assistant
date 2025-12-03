"""
Business Logic for KB Management Operations
Service layer handling KB listing, health checks, and KB CRUD.
"""

import logging
from typing import List, Dict, Any
from pathlib import Path

from app.kb import KBManager, MultiSourceQueryService
from .management_models import CreateKBRequest

logger = logging.getLogger(__name__)


class KBManagementService:
    """Service layer for KB management operations"""
    
    def __init__(self):
        pass
    
    def create_knowledge_base(self, request: CreateKBRequest, manager: KBManager) -> Dict[str, str]:
        """
        Create a new knowledge base.
        
        Args:
            request: KB creation request
            manager: KB manager instance
            
        Returns:
            Dict with kb_id, kb_name, message
            
        Raises:
            ValueError: If KB already exists or validation fails
        """
        # Check if KB already exists
        if manager.kb_exists(request.kb_id):
            raise ValueError(f"Knowledge base '{request.kb_id}' already exists")
        
        # Build KB configuration
        kb_config = {
            'id': request.kb_id,
            'name': request.name,
            'description': request.description or '',
            'status': 'active',
            'source_type': request.source_type.value,
            'source_config': request.source_config,
            'embedding_model': request.embedding_model,
            'chunk_size': request.chunk_size,
            'chunk_overlap': request.chunk_overlap,
            'profiles': request.profiles or ['chat', 'kb-query'],
            'priority': request.priority,
            'indexed': False
        }
        
        # Create KB
        manager.create_kb(request.kb_id, kb_config)
        
        logger.info(f"KB created id={request.kb_id} name='{request.name}'")
        
        return {
            "message": f"Knowledge base '{request.name}' created successfully",
            "kb_id": request.kb_id,
            "kb_name": request.name
        }
    
    def list_knowledge_bases(self, manager: KBManager) -> List[Dict[str, Any]]:
        """
        List all available knowledge bases.
        
        Args:
            manager: KB manager instance
            
        Returns:
            List of KB information dictionaries
        """
        kbs_info = manager.list_kbs()
        return kbs_info  # Listing log suppressed
    
    def check_health(self, service: MultiSourceQueryService) -> Dict[str, Any]:
        """
        Check health status of all knowledge bases.
        
        Args:
            service: Multi-source query service instance
            
        Returns:
            Dictionary with overall status and per-KB health info
        """
        health_dict = service.get_kb_health()
        
        # Process health information
        kb_health = []
        all_ready = True
        
        for kb_id, kb_info in health_dict.items():
            index_ready = kb_info.get('status') == 'ready'
            if not index_ready:
                all_ready = False
                
            kb_health.append({
                'kb_id': kb_id,
                'kb_name': kb_info['name'],
                'status': kb_info['status'],
                'index_ready': index_ready,
                'error': kb_info.get('error')
            })
        
        overall_status = (
            'healthy' if all_ready 
            else 'degraded' if len(kb_health) > 0 
            else 'unavailable'
        )
        
        logger.info(f"KB health status={overall_status}")
        return {
            'overall_status': overall_status,
            'knowledge_bases': kb_health
        }


# Singleton instance
_management_service = None


def get_management_service() -> KBManagementService:
    """Get singleton management service instance"""
    global _management_service
    if _management_service is None:
        _management_service = KBManagementService()
    return _management_service
