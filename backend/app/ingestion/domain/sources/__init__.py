"""
Source Handlers Package
Modular source handlers for knowledge base ingestion.
Uses lazy imports - handlers are only loaded when factory creates them.
"""

from .factory import SourceHandlerFactory

__all__ = ['SourceHandlerFactory']

