# Backward-compatible re-exports — canonical location: app.services.project
from app.services.project.chat_service import ChatService
from app.services.project.document_service import DocumentService
from app.services.project.project_service import ProjectService

__all__ = ["ChatService", "DocumentService", "ProjectService"]

