"""Shared service singleton factories for project management dependencies."""

from app.services.project.chat_service import ChatService
from app.services.project.document_content_service import DocumentContentService
from app.services.project.document_service import DocumentService
from app.services.project.project_analysis_service import ProjectAnalysisService
from app.services.project.project_service import ProjectService
from app.services.project.state_edit_service import ProjectStateEditService

_project_service = ProjectService()
_document_service = DocumentService()
_document_content_service = DocumentContentService()
_project_analysis_service = ProjectAnalysisService(_document_service)
_chat_service = ChatService()
_project_state_edit_service = ProjectStateEditService()


def get_project_service_dep() -> ProjectService:
    return _project_service


def get_document_service_dep() -> DocumentService:
    return _document_service


def get_document_content_service_dep() -> DocumentContentService:
    return _document_content_service


def get_project_analysis_service_dep() -> ProjectAnalysisService:
    return _project_analysis_service


def get_chat_service_dep() -> ChatService:
    return _chat_service


def get_state_edit_service_dep() -> ProjectStateEditService:
    return _project_state_edit_service
