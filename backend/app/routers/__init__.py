"""
Routers package
Exports top-level API routers.
"""

from .agents import router as agent_router
from .checklists.checklist_router import router as checklist_router
from .diagram_generation import router as diagram_generation_router
from .ingestion import router as ingestion_router
from .kb_management import router as kb_management_router
from .kb_query import router as kb_query_router
from .project_management import router as project_router
from .settings import router as settings_router

__all__ = [
    "agent_router",
    "checklist_router",
    "diagram_generation_router",
    "ingestion_router",
    "kb_management_router",
    "kb_query_router",
    "project_router",
    "settings_router",
]

