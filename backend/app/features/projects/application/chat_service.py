import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.services.project_context import read_project_state
from app.features.projects.infrastructure.project_state_store import ProjectStateStore
from app.models import ConversationMessage, Project
from app.shared.ai.llm_service import get_llm_service

from .project_service import ProjectService

logger = logging.getLogger(__name__)
_project_state_store = ProjectStateStore()


class KnowledgeQueryGateway(Protocol):
    def query_chat_sources(self, message: str, *, top_k_per_kb: int = 3) -> list[dict[str, Any]]: ...


class _NoopKnowledgeQueryGateway:
    def query_chat_sources(self, message: str, *, top_k_per_kb: int = 3) -> list[dict[str, Any]]:
        return []


class ChatService:
    """Handles chat operations and state updates for projects."""

    def __init__(
        self,
        *,
        project_service: ProjectService | None = None,
        knowledge_query_gateway: KnowledgeQueryGateway | None = None,
    ) -> None:
        self._project_service = project_service if project_service is not None else ProjectService()
        self._knowledge_query_gateway = (
            knowledge_query_gateway
            if knowledge_query_gateway is not None
            else _NoopKnowledgeQueryGateway()
        )

    async def _get_project_context(
        self, project_id: str, db: AsyncSession
    ) -> dict[str, Any]:
        """Load project and its current state record from DB."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        state_record = await _project_state_store.get_record(project_id=project_id, db=db)
        if state_record is None:
            raise ValueError(
                "Project state not initialized. Please analyze documents first."
            )

        current_state = await read_project_state(project_id, db)
        if current_state is None:
            raise ValueError(
                "Project state not initialized. Please analyze documents first."
            )

        return current_state

    def _should_query_kb(self, message: str) -> bool:
        """Heuristic to decide if message warrants a KB lookup."""
        keywords = [
            "azure",
            "architecture",
            "service",
            "security",
            "availability",
            "performance",
        ]
        return any(k in message.lower() for k in keywords)

    async def _save_message(
        self, project_id: str, role: str, content: str, db: AsyncSession, **kwargs
    ) -> ConversationMessage:
        """Persist a conversation message to the database."""
        msg = ConversationMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            role=role,
            content=content,
            timestamp=datetime.now(timezone.utc).isoformat(),
            **kwargs,
        )
        db.add(msg)
        await db.commit()
        return msg

    async def _get_kb_sources(self, message: str) -> list[dict[str, Any]]:
        """Query knowledge base if relevant to message."""
        if not self._should_query_kb(message):
            return []

        logger.info("Architecture question detected, querying KB")
        try:
            kb_res = self._knowledge_query_gateway.query_chat_sources(
                message,
                top_k_per_kb=3,
            )
            return kb_res
        except Exception as exc:  # noqa: BLE001
            logger.error(f"KB query failed: {exc}")
            return []

    async def process_chat_message(
        self,
        project_id: str,
        message: str,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Process a chat message with project context and KB augmentation."""
        if not message or not message.strip():
            raise ValueError("Message is required")

        current_state = await self._get_project_context(project_id, db)
        await self._save_message(project_id, "user", message, db)

        # Retrieve conversation history
        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.project_id == project_id)
            .order_by(ConversationMessage.timestamp.desc())
            .limit(10)
        )
        recent_msgs = [msg.to_dict() for msg in reversed(result.scalars().all())]

        kb_sources = await self._get_kb_sources(message)

        llm_service = get_llm_service()
        response = await llm_service.process_chat_message(
            message,
            current_state,
            recent_msgs,
            kb_sources if kb_sources else None,
        )

        wf_sources = (
            json.dumps(response.get("sources", [])) if response.get("sources") else None
        )
        await self._save_message(
            project_id,
            "assistant",
            response["assistantMessage"],
            db,
            waf_sources=wf_sources,
        )

        updated_at = datetime.now(timezone.utc).isoformat()
        await _project_state_store.persist_composed_state(
            project_id=project_id,
            state=response["projectState"],
            db=db,
            replace_missing=True,
            updated_at=updated_at,
        )

        await db.commit()

        logger.info(f"Chat response generated for project: {project_id}")

        return {
            "message": response["assistantMessage"],
            "projectState": response["projectState"],
            "wafSources": response.get("sources", []),
        }

    async def get_project_state(
        self, project_id: str, db: AsyncSession
    ) -> dict[str, Any]:
        # Delegate to the AAA-aware state reader to ensure stable defaults and
        # casing (camelCase aliases) across the app.
        state = await read_project_state(project_id, db)
        if not state:
            raise ValueError("Project state not found. Please analyze documents first.")
        waf_checklist = await self._project_service.get_waf_checklist_state(project_id, db)
        if waf_checklist is not None:
            state["wafChecklist"] = waf_checklist
        return cast(dict[str, Any], state)

    async def get_conversation_messages(
        self,
        project_id: str,
        db: AsyncSession,
        before_id: str | None = None,
        since_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        query = select(ConversationMessage).where(
            ConversationMessage.project_id == project_id
        )

        if before_id:
            # Find the timestamp of the message before which we want older messages
            ref_msg = await db.execute(
                select(ConversationMessage).where(ConversationMessage.id == before_id)
            )
            ref_msg_obj = ref_msg.scalar_one_or_none()
            if ref_msg_obj:
                query = query.where(ConversationMessage.timestamp < ref_msg_obj.timestamp)

        if since_id:
            # Find the timestamp of the message since which we want newer messages
            ref_msg = await db.execute(
                select(ConversationMessage).where(ConversationMessage.id == since_id)
            )
            ref_msg_obj = ref_msg.scalar_one_or_none()
            if ref_msg_obj:
                query = query.where(ConversationMessage.timestamp > ref_msg_obj.timestamp)

        if before_id:
            # Older messages: newest first (for limit/offset), then reverse for client
            query = query.order_by(ConversationMessage.timestamp.desc()).limit(limit)
        else:
            # Newer messages or full history: oldest first
            query = query.order_by(ConversationMessage.timestamp.asc())
            if since_id:
                query = query.limit(limit)

        result = await db.execute(query)
        messages = result.scalars().all()

        if before_id:
            # Reverse back to chronologic order for the client if we fetched oldest-first via desc limit
            messages = list(reversed(messages))

        return [msg.to_dict() for msg in messages]

