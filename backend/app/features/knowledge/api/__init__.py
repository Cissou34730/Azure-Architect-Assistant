"""Knowledge API package."""

from .management_router import router as kb_management_router
from .query_router import router as kb_query_router

management_router = kb_management_router
query_router = kb_query_router

__all__ = [
    "kb_management_router",
    "kb_query_router",
    "management_router",
    "query_router",
]
