import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents_system.services.project_context import read_project_state
from app.models import ConversationMessage, Project, ProjectState
from app.service_registry import get_multi_query_service
from app.services.kb import QueryProfile
from app.services.llm_service import get_llm_service

logger = logging.getLogger(__name__)


class ChatService:
    """Handles chat operations and state updates for projects."""

    async def _get_project_context(
        self, project_id: str, db: AsyncSession
    ) -> tuple[Project, dict[str, Any]]:
        """Load project and its current state record from DB."""
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        result = await db.execute(
            select(ProjectState).where(ProjectState.project_id == project_id)
        )
        state_record = result.scalar_one_or_none()
        if not state_record:
            raise ValueError(
                "Project state not initialized. Please analyze documents first."
            )

        return project, json.loads(state_record.state)

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
            multi_query_service = get_multi_query_service()
            kb_res = multi_query_service.query_profile(
                question=message, profile=QueryProfile.CHAT, top_k_per_kb=3
            )
            return kb_res.get("sources", []) if kb_res.get("has_results") else []
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

        state_record, current_state = await self._get_project_context(project_id, db)
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

        state_record.state = json.dumps(response["projectState"])
        state_record.updated_at = datetime.now(timezone.utc).isoformat()

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

