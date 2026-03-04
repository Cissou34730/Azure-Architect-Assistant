"""
Routers package
Exports all top-level API routers.
"""

from .agents import agent_router
from .checklists import checklist_router
from .diagram_generation import diagram_generation_router
from .ingestion import cleanup_running_tasks, ingestion_router
from .kb_management import kb_management_router
from .kb_query import kb_query_router
from .project_management import project_router
from .settings import settings_router

__all__ = [
    "agent_router",
    "checklist_router",
    "cleanup_running_tasks",
    "diagram_generation_router",
    "ingestion_router",
    "kb_management_router",
    "kb_query_router",
    "project_router",
    "settings_router",
]
