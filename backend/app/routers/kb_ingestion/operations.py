"""
Business Logic for KB Ingestion Operations
Separated from routing layer for better maintainability.
This layer handles orchestration and validation only - actual work is in workers.
"""

import logging
from typing import Dict
from app.service_registry import get_kb_manager

logger = logging.getLogger(__name__)


class KBIngestionService:
    """Service layer for KB ingestion operations - orchestration only"""
    
    def __init__(self):
        pass
    
    def start_ingestion(self, kb_id: str) -> Dict[str, str]:
        """
        Start ingestion for a knowledge base.
        
        Args:
            kb_id: Knowledge base identifier
            
        Returns:
            Dict with job_id, kb_id, message
            
        Raises:
            ValueError: If KB not found or job already running
        """
        # Get fresh KB manager instance
        kb_manager = get_kb_manager()
        
        # Check if KB exists
        if not kb_manager.kb_exists(kb_id):
            raise ValueError(f"Knowledge base '{kb_id}' not found")
        
        # Get KB configuration
        kb_config = kb_manager.get_kb_config(kb_id)
        kb_name = kb_config.get('name', kb_id)
        
        logger.info(f"Starting ingestion for KB: {kb_id}")
        
        return {
            "message": f"Ingestion started for '{kb_name}'",
            "job_id": f"{kb_id}-job",
            "kb_id": kb_id
        }


# Singleton instance
_ingestion_service = None


def get_ingestion_service() -> KBIngestionService:
    """Get singleton ingestion service instance"""
    global _ingestion_service
    if _ingestion_service is None:
        _ingestion_service = KBIngestionService()
    return _ingestion_service
