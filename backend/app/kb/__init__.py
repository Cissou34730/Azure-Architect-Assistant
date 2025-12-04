"""
Knowledge Base Module
Generic RAG pipeline supporting multiple knowledge bases with profile-based querying.
"""

from .knowledge_base_manager import KBManager
from .service import KnowledgeBaseService

__all__ = [
    'KBManager',
    'KnowledgeBaseService', 
    'MultiSourceQueryService',
    'QueryProfile'
]
