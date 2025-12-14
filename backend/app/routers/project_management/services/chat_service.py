import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Project, ProjectState, ConversationMessage
from app.services.llm_service import get_llm_service
from app.service_registry import get_multi_query_service
from app.services.kb import QueryProfile

logger = logging.getLogger(__name__)


class ChatService:
    """Handles chat operations and state updates for projects."""

    async def process_chat_message(
        self,
        project_id: str,
        message: str,
        db: AsyncSession,
    ) -> Dict[str, Any]:
        if not message or not message.strip():
            raise ValueError("Message is required")

        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        result = await db.execute(select(ProjectState).where(ProjectState.project_id == project_id))
        state_record = result.scalar_one_or_none()
        if not state_record:
            raise ValueError("Project state not initialized. Please analyze documents first.")

        current_state = json.loads(state_record.state)

        user_message = ConversationMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            role="user",
            content=message,
            timestamp=datetime.utcnow().isoformat(),
        )
        db.add(user_message)
        await db.commit()

        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.project_id == project_id)
            .order_by(ConversationMessage.timestamp.desc())
            .limit(10)
        )
        recent_messages = list(reversed(result.scalars().all()))
        recent_message_dicts = [msg.to_dict() for msg in recent_messages]

        logger.info(f"Processing chat for project: {project_id}")

        is_architecture_related = any(
            keyword in message.lower()
            for keyword in ["azure", "architecture", "service", "security", "availability", "performance"]
        )

        kb_sources = []
        if is_architecture_related:
            logger.info("Architecture question detected, querying KB")
            try:
                multi_query_service = get_multi_query_service()
                kb_result = multi_query_service.query_profile(
                    question=message, profile=QueryProfile.CHAT, top_k_per_kb=3
                )
                if kb_result.get("has_results"):
                    kb_sources = kb_result.get("sources", [])
            except Exception as exc:
                logger.error(f"KB query failed: {exc}")

        llm_service = get_llm_service()
        response = await llm_service.process_chat_message(
            message,
            current_state,
            recent_message_dicts,
            kb_sources if kb_sources else None,
        )

        assistant_message = ConversationMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            role="assistant",
            content=response["assistantMessage"],
            timestamp=datetime.utcnow().isoformat(),
            waf_sources=json.dumps(response.get("sources", [])) if response.get("sources") else None,
        )
        db.add(assistant_message)

        state_record.state = json.dumps(response["projectState"])
        state_record.updated_at = datetime.utcnow().isoformat()

        await db.commit()

        logger.info(f"Chat response generated for project: {project_id}")

        return {
            "message": response["assistantMessage"],
            "projectState": response["projectState"],
            "wafSources": response.get("sources", []),
        }

    async def get_project_state(self, project_id: str, db: AsyncSession) -> Dict[str, Any]:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        result = await db.execute(select(ProjectState).where(ProjectState.project_id == project_id))
        state_record = result.scalar_one_or_none()
        if not state_record:
            raise ValueError("Project state not found. Please analyze documents first.")

        state_data = json.loads(state_record.state)
        state_data["projectId"] = project_id
        state_data["lastUpdated"] = state_record.updated_at

        return state_data

    async def get_conversation_messages(self, project_id: str, db: AsyncSession) -> List[Dict[str, Any]]:
        result = await db.execute(select(Project).where(Project.id == project_id))
        project = result.scalar_one_or_none()
        if not project:
            raise ValueError("Project not found")

        result = await db.execute(
            select(ConversationMessage)
            .where(ConversationMessage.project_id == project_id)
            .order_by(ConversationMessage.timestamp.asc())
        )
        messages = result.scalars().all()
        return [msg.to_dict() for msg in messages]
