"""
Business Logic for KB Management Operations
Service layer handling KB listing and health checks.
"""

import logging
from typing import List, Dict, Any

from app.kb import KBManager, MultiSourceQueryService

logger = logging.getLogger(__name__)


class KBManagementService:
    """Service layer for KB management operations"""
    
    @staticmethod
    def list_knowledge_bases(manager: KBManager) -> List[Dict[str, Any]]:
        """
        List all available knowledge bases.
        
        Args:
            manager: KB manager instance
            
        Returns:
            List of KB information dictionaries
        """
        kbs_info = manager.list_kbs()
        logger.info(f"Listed {len(kbs_info)} knowledge bases")
        return kbs_info
    
    @staticmethod
    def check_health(service: MultiSourceQueryService) -> Dict[str, Any]:
        """
        Check health status of all knowledge bases.
        
        Args:
            service: Multi-source query service instance
            
        Returns:
            Dictionary with overall status and per-KB health info
        """
        logger.info("Starting KB health check...")
        health_dict = service.get_kb_health()
        logger.info(f"Got health_dict with {len(health_dict)} KBs")
        
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
        
        logger.info(f"Health check complete: {overall_status}")
        return {
            'overall_status': overall_status,
            'knowledge_bases': kb_health
        }
