"""
LLM Service for document analysis, chat, and proposal generation.
Uses unified AI service layer for provider abstraction.
"""

import json
import logging
import re
from collections.abc import Callable
from typing import Any

from app.services.ai import ChatMessage, get_ai_service

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM operations in project workflow."""

    def __init__(self):
        self.ai_service = get_ai_service()
        self.model = self.ai_service.get_llm_model()
        logger.info(f"LLMService ready with model: {self.model}")

    async def analyze_documents(self, document_texts: list[str]) -> dict[str, Any]:
        """
        Analyze documents and extract ProjectState structure.

        Args:
            document_texts: List of document text content

        Returns:
            Dictionary representing ProjectState
        """
        # Analysis document count log suppressed

        combined_text = "\n\n---\n\n".join(document_texts)

        system_prompt = """You are an Azure Architecture Assistant.

Analyze the provided project documents and extract:
1) A baseline Architecture Sheet (context/NFRs/constraints)
2) Structured requirements for the Azure Architect Assistant (AAA)
3) Prioritized clarification questions based on gaps/ambiguities

Return JSON ONLY (no markdown, no code fences) with this structure:
{
    "context": {
        "summary": "Brief project summary",
        "objectives": ["objective1"],
        "targetUsers": "Description of target users",
        "scenarioType": "Type of scenario (e.g., web app, IoT, data analytics)"
    },
    "nfrs": {
        "availability": "Availability requirements",
        "security": "Security requirements",
        "performance": "Performance requirements",
        "costConstraints": "Cost constraints"
    },
    "applicationStructure": {
        "components": [{"name": "component name", "description": "component description"}],
        "integrations": ["integration1"]
    },
    "dataCompliance": {
        "dataTypes": ["data type1"],
        "complianceRequirements": ["requirement1"],
        "dataResidency": "Data residency requirements"
    },
    "technicalConstraints": {
        "constraints": ["constraint1"],
        "assumptions": ["assumption1"]
    },
    "openQuestions": ["question1"],

    "requirements": [
        {
            "category": "business | functional | nfr",
            "text": "Requirement text",
            "ambiguity": {"isAmbiguous": false, "notes": ""},
            "sources": [
                {"documentId": "<if present in input>", "fileName": "<if present>", "excerpt": "short quote"}
            ]
        }
    ],
    "clarificationQuestions": [
        {
            "question": "Clarification question",
            "priority": 1,
            "relatedRequirementIndexes": [0]
        }
    ]
}

Notes:
- Requirement categories must be exactly one of: business, functional, nfr
- Mark ambiguities explicitly using ambiguity.isAmbiguous + ambiguity.notes
- If you cannot determine sources, return an empty sources array
- Prioritize clarificationQuestions: priority=1 is highest
"""

        user_prompt = (
            "Analyze these project documents and extract the Architecture Sheet + AAA requirements.\n\n"
            + combined_text
        )

        try:
            project_state = await self._complete_json(
                system_prompt, user_prompt, max_tokens=3000
            )
        except Exception:  # noqa: BLE001
            # Fallback to legacy parsing if JSON mode fails for any reason
            response = await self._complete(system_prompt, user_prompt, max_tokens=3000)
            project_state = self._parse_project_state(response)

        return project_state

    async def _complete_json(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 2000
    ) -> dict[str, Any]:
        """Make an LLM call requesting JSON-only output and parse it.

        Uses OpenAI JSON mode via response_format when supported by the provider.
        """
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]

        response = await self.ai_service.chat(
            messages=messages,
            temperature=self.ai_service.config.default_temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )

        content = response.content
        if not content:
            raise ValueError("LLM returned empty response")

        return json.loads(content)

    async def process_chat_message(
        self,
        user_message: str,
        current_state: dict[str, Any],
        recent_messages: list[dict[str, Any]],
        kb_sources: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        Process chat message and update project state.

        Args:
            user_message: User's message
            current_state: Current ProjectState
            recent_messages: Recent conversation history
            kb_sources: Optional KB sources from RAG query

        Returns:
            Dictionary with assistantMessage, projectState, sources
        """
        # Chat message processing log suppressed

        # Build conversation history
        conversation_history = "\n".join(
            [
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in recent_messages[-10:]  # Last 10 messages
            ]
        )

        # Build KB context if available
        kb_context = ""
        if kb_sources:
            kb_context = "\n\n".join(
                [
                    f"[Source: {src.get('title', 'Unknown')}]\n{src.get('content', '')}"
                    for src in kb_sources
                ]
            )

        system_prompt = self._build_chat_system_prompt(
            current_state, kb_context, bool(kb_context)
        )
        user_prompt = f"Previous conversation:\n{conversation_history}\n\nUser message: {user_message}"

        response = await self._complete(system_prompt, user_prompt)
        result = self._parse_chat_response(response, current_state)

        if kb_sources:
            result["sources"] = kb_sources

        # Chat processed log suppressed
        return result

    async def generate_architecture_proposal(
        self,
        state: dict[str, Any],
        on_progress: Callable[[str, str | None], None] | None = None,
    ) -> str:
        """
        Generate comprehensive architecture proposal.

        Args:
            state: ProjectState dictionary
            on_progress: Optional callback for progress updates

        Returns:
            Markdown-formatted proposal
        """
        # Proposal generation start log suppressed

        if on_progress:
            on_progress("analyzing", "Analyzing project requirements")

        # Build comprehensive prompt
        system_prompt = """You are an expert Azure Solution Architect. Generate a comprehensive, production-ready architecture proposal in Markdown format.

The proposal should include:
1. Executive Summary
2. Requirements Analysis
3. Proposed Architecture
4. Azure Services Selection with justification
5. Security & Compliance
6. High Availability & Disaster Recovery
7. Performance & Scalability
8. Cost Estimation
9. Implementation Roadmap
10. Risks & Mitigation

Use clear headings, bullet points, and technical details. Reference Azure Well-Architected Framework pillars."""

        state_json = json.dumps(state, indent=2)
        user_prompt = f"Generate a comprehensive architecture proposal for this project:\n\n{state_json}"

        if on_progress:
            on_progress("generating", "Generating proposal content")

        proposal = await self._complete(system_prompt, user_prompt, max_tokens=4000)

        if on_progress:
            on_progress("completed", "Proposal generated successfully")

        # Proposal generated log suppressed
        return proposal

    async def _complete(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 2000
    ) -> str:
        """Make LLM API call via unified AI service."""
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]

        response = await self.ai_service.chat(
            messages=messages,
            temperature=self.ai_service.config.default_temperature,
            max_tokens=max_tokens,
        )

        return response.content

    def _parse_project_state(self, response: str) -> dict[str, Any]:
        """Parse ProjectState from LLM response."""
        # Extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            logger.error("Failed to extract JSON from LLM response")
            raise ValueError("Failed to extract JSON from LLM response")

        parsed = json.loads(json_match.group(0))
        return parsed

    def _parse_chat_response(
        self, response: str, current_state: dict[str, Any]
    ) -> dict[str, Any]:
        """Parse chat response and extract updated state if present."""
        # Try to find JSON in response
        json_match = re.search(r"\{[\s\S]*\}", response)

        if json_match:
            try:
                parsed = json.loads(json_match.group(0))
                # If it looks like a state update, use it
                if "context" in parsed or "nfrs" in parsed:
                    # Merge with current state
                    updated_state = {**current_state, **parsed}
                    # Extract assistant message (text before JSON)
                    assistant_message = response[: json_match.start()].strip()
                    return {
                        "assistantMessage": assistant_message
                        or "I've updated the architecture sheet.",
                        "projectState": updated_state,
                        "sources": [],
                    }
            except json.JSONDecodeError:
                pass

        # No state update, just return the message
        return {
            "assistantMessage": response,
            "projectState": current_state,
            "sources": [],
        }

    def _build_chat_system_prompt(
        self, state: dict[str, Any], kb_context: str, has_kb_context: bool
    ) -> str:
        """Build system prompt for chat."""
        state_json = json.dumps(state, indent=2)

        kb_section = ""
        if has_kb_context:
            kb_section = f"\n\nKNOWLEDGE BASE CONTEXT:\n{kb_context}\n\nUse this context to provide accurate Azure guidance."

        return f"""You are an Azure Architecture Assistant helping refine an architecture project.

CURRENT PROJECT STATE:
{state_json}
{kb_section}

Your role:
1. Answer the user's question clearly and concisely
2. If the question clarifies project requirements, update the ProjectState JSON
3. Reference Azure best practices and Well-Architected Framework when relevant

Response format:
- For questions: Provide a clear answer
- For clarifications: Provide answer AND output the UPDATED ProjectState as JSON

Always be helpful, professional, and technically accurate."""


# Singleton instance
class LLMServiceSingleton:
    """
    Manages a singleton instance of LLMService.
    
    SINGLETON RATIONALE:
    - Connection pooling: HTTP clients to OpenAI/Azure OpenAI benefit from persistence
    - Rate limiting: Shared state prevents per-request quota issues
    - Initialization cost: Client setup has network overhead
    - Consistent configuration: All requests use same LLM settings
    
    Testability:
    - Override via FastAPI dependency injection (see app.dependencies.get_llm_service_dependency)
    - Use set_instance() to inject mock in unit tests
    - See tests/conftest.py for mock_llm_service fixture
    """
    _instance: LLMService | None = None

    @classmethod
    def get_instance(cls) -> LLMService:
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = LLMService()
        return cls._instance

    @classmethod
    def set_instance(cls, instance: LLMService | None) -> None:
        """Set or clear singleton instance (for testing/lifecycle)."""
        cls._instance = instance

def get_llm_service() -> LLMService:
    """Get or create LLM service instance."""
    return LLMServiceSingleton.get_instance()

