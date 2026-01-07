"""
Request/Response Models for Project Management API
"""

from pydantic import BaseModel
from typing import List, Dict, Any


class CreateProjectRequest(BaseModel):
    """Request to create a new project"""

    name: str


class UpdateRequirementsRequest(BaseModel):
    """Request to update project requirements"""

    textRequirements: str


class ChatMessageRequest(BaseModel):
    """Request to send a chat message"""

    message: str


class ProjectResponse(BaseModel):
    """Single project response"""

    project: Dict[str, Any]


class ProjectsListResponse(BaseModel):
    """List of projects response"""

    projects: List[Dict[str, Any]]


class DocumentsResponse(BaseModel):
    """List of documents response"""

    documents: List[Dict[str, Any]]


class StateResponse(BaseModel):
    """Project state response"""

    projectState: Dict[str, Any]


class MessagesResponse(BaseModel):
    """Conversation messages response"""

    messages: List[Dict[str, Any]]


class ChatResponse(BaseModel):
    """Chat response with updated state"""

    message: str
    projectState: Dict[str, Any]
    wafSources: List[Dict[str, Any]] = []
