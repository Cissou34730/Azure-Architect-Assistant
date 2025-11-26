"""
Knowledge Base Module
Generic RAG pipeline supporting multiple knowledge bases with profile-based querying.
"""

from .manager import KBManager
from .service import KnowledgeBaseService
from .multi_query import MultiSourceQueryService, QueryProfile

__all__ = [
    'KBManager',
    'KnowledgeBaseService', 
    'MultiSourceQueryService',
    'QueryProfile'
]
