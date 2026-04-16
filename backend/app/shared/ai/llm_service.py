"""
LLM Service for document analysis, chat, and proposal generation.
Uses unified AI service layer for provider abstraction.
"""

import json
import logging
import re
from collections.abc import Callable
from typing import Any

from openai import APIError, APITimeoutError, BadRequestError, RateLimitError

from app.shared.ai import ChatMessage, get_ai_service
from app.shared.ai.json_repair import (
    extract_json_candidate,
    parse_json_with_repair,
    repair_json_content,
)
from app.shared.config.app_settings import get_app_settings

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM operations in project workflow."""

    def __init__(self):
        self.ai_service = get_ai_service()
        self.app_settings = get_app_settings()
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

        system_prompt = """You are an Azure Architecture Assistant performing thorough document analysis.

Your task: Extract a comprehensive, exhaustive inventory of ALL information from the provided project documents.
Do NOT summarize or condense — capture every requirement, constraint, stakeholder mention, integration point,
scale/volume indicator, and implicit expectation found in the text.

Return JSON ONLY (no markdown, no code fences) with this structure:
{
    "context": {
        "summary": "Detailed project summary covering purpose, scope, and key business drivers",
        "objectives": ["objective1", "objective2"],
        "targetUsers": "Description of all target users, user roles, and stakeholders mentioned",
        "scenarioType": "Type of scenario (e.g., web app, IoT, data analytics, migration, modernization)",
        "stakeholders": ["stakeholder1", "stakeholder2"],
        "businessDrivers": ["driver1", "driver2"]
    },
    "nfrs": {
        "availability": "Availability/uptime requirements with specific SLA targets if mentioned",
        "security": "All security requirements: authentication, authorization, encryption, compliance frameworks",
        "performance": "Performance targets: latency, throughput, response times, concurrent users/scale/volume",
        "costConstraints": "Budget, cost model (CapEx/OpEx), optimization priorities",
        "scalability": "Growth projections, expected scale, peak load characteristics",
        "operationalExcellence": "Monitoring, alerting, deployment, maintenance requirements"
    },
    "applicationStructure": {
        "components": [{"name": "component name", "description": "detailed component description including responsibilities"}],
        "integrations": ["all external systems, APIs, third-party services mentioned"],
        "dataFlows": ["description of data flow between components"]
    },
    "dataCompliance": {
        "dataTypes": ["every data type mentioned: PII, financial, health, etc."],
        "complianceRequirements": ["all regulatory/compliance frameworks: GDPR, HIPAA, SOC 2, PCI DSS, ISO 27001, etc."],
        "dataResidency": "Data residency/sovereignty requirements with specific regions if mentioned"
    },
    "technicalConstraints": {
        "constraints": ["every technical constraint: platform limits, legacy systems, required technologies, deployment restrictions"],
        "assumptions": ["every assumption: implicit or explicit, about technology, team, timeline, etc."]
    },
    "openQuestions": ["critical gaps or missing information that block architecture decisions"],

    "requirements": [
        {
            "category": "business | functional | nfr",
            "text": "Full requirement text — be specific and detailed, not summarized",
            "priority": "high | medium | low",
            "ambiguity": {"isAmbiguous": false, "notes": "explain what is unclear if ambiguous"},
            "sources": [
                {"documentId": "<from input if present>", "fileName": "<from input if present>", "excerpt": "verbatim short quote from the source"}
            ]
        }
    ],
    "clarificationQuestions": [
        {
            "question": "Specific clarification question tied to a gap or ambiguity",
            "priority": 1,
            "relatedRequirementIndexes": [0],
            "impact": "Why this answer matters for architecture decisions"
        }
    ]
}

EXTRACTION RULES (mandatory):
- Be EXHAUSTIVE: extract every explicit AND implicit requirement. A mention of "users in Europe" implies a data residency requirement.
- Cross-reference across documents: if Document A mentions a component and Document B mentions its constraints, link them.
- Capture scale indicators: any mention of user counts, data volumes, transaction rates, concurrent sessions, growth projections.
- Capture integration points: every external system, API, service, or data source mentioned.
- Capture stakeholders: every person, role, team, or department mentioned.
- Preserve DocumentId references: when input contains "DocumentId: X" headers, use that X in sources[].documentId.
- Mark ambiguities: if a requirement could be interpreted multiple ways, set isAmbiguous=true with notes explaining the ambiguity.
- Priority assessment: assign priority based on business impact (explicit "must" = high, "should" = medium, "nice to have" = low).
- Do NOT invent requirements not supported by the text — but DO surface implicit requirements that logically follow from explicit ones.
- If documents are contradictory, capture both versions and flag the contradiction in openQuestions.
"""

        user_prompt = (
            "Analyze these project documents and extract the Architecture Sheet + AAA requirements.\n\n"
            + combined_text
        )

        try:
            project_state = await self._complete_json(
                system_prompt,
                user_prompt,
                max_tokens=self.app_settings.llm_analyze_max_tokens,
            )
        except (APITimeoutError, RateLimitError, APIError):
            # Network/server-level failure — no point retrying with the legacy path
            raise
        except (ValueError, TypeError, json.JSONDecodeError) as e:
            # Content-level failure (bad JSON, empty response, etc.) — try legacy parser
            logger.warning(f"JSON mode failed, falling back to legacy parsing: {e}")
            response = await self._complete(
                system_prompt,
                user_prompt,
                max_tokens=self.app_settings.llm_analyze_max_tokens,
            )
            project_state = self._parse_project_state(response)

        return project_state

    async def _complete_json(
        self, system_prompt: str, user_prompt: str, max_tokens: int = 2000
    ) -> dict[str, Any]:
        """Make an LLM call requesting JSON-only output and parse it.

        Uses OpenAI JSON mode via response_format when supported by the provider.
        Falls back to regular mode if not supported.
        """
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=user_prompt),
        ]

        try:
            response = await self.ai_service.chat(
                messages=messages,
                temperature=None,
                use_model_default_temperature=True,
                max_tokens=max_tokens,
                response_format={"type": "json_object"},
                timeout=self.app_settings.llm_request_timeout_seconds,
            )
        except BadRequestError as e:
            # response_format not supported by this model — retry without it
            logger.warning(f"JSON mode failed, retrying without response_format: {e}")
            response = await self.ai_service.chat(
                messages=messages,
                temperature=None,
                use_model_default_temperature=True,
                max_tokens=max_tokens,
                timeout=self.app_settings.llm_request_timeout_seconds,
            )

        content = response.content
        if not content:
            raise ValueError("LLM returned empty response")

        # Log first 500 chars for debugging
        logger.debug(
            "LLM response preview: %s...",
            content[: self.app_settings.llm_response_preview_log_chars],
        )

        return await self._parse_json_with_repair(content, max_tokens=max_tokens)

    async def _parse_json_with_repair(
        self,
        content: str,
        max_tokens: int,
    ) -> dict[str, Any]:
        """Parse JSON content and attempt one repair pass on decode failure."""
        async def _repair(invalid_json: str, repair_tokens: int) -> str:
            return await self._repair_json_content(
                invalid_json=invalid_json,
                max_tokens=repair_tokens,
            )

        return await parse_json_with_repair(
            content,
            max_tokens=max(
                self.app_settings.llm_json_repair_min_tokens,
                max_tokens // self.app_settings.llm_json_repair_token_divisor,
            ),
            repair_fn=_repair,
            preview_chars=self.app_settings.llm_response_error_log_chars,
        )

    async def _repair_json_content(self, invalid_json: str, max_tokens: int) -> str:
        """Ask the model to repair malformed/truncated JSON and return valid JSON only."""
        async def _complete(system: str, user: str, tokens: int) -> str:
            return await self._complete(system, user, max_tokens=tokens)

        return await repair_json_content(
            invalid_json,
            max_tokens,
            complete_fn=_complete,
        )

    @staticmethod
    def _extract_json_candidate(response_text: str) -> str | None:
        """Extract the outer JSON object from text if present."""
        return extract_json_candidate(response_text)

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
            timeout=self.app_settings.llm_request_timeout_seconds,
        )

        return response.content

    def _parse_project_state(self, response: str) -> dict[str, Any]:
        """Parse ProjectState from LLM response."""
        # Extract JSON from response
        json_candidate = self._extract_json_candidate(response)
        if json_candidate is None:
            logger.error("Failed to extract JSON from LLM response")
            logger.error(
                "Response content (first %s chars): %s",
                self.app_settings.llm_response_error_log_chars,
                response[: self.app_settings.llm_response_error_log_chars],
            )
            raise ValueError("Failed to extract JSON from LLM response")

        try:
            parsed = json.loads(json_candidate)
            return parsed
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode failed in _parse_project_state: {e}")
            logger.error(
                "Extracted JSON string: %s",
                json_candidate[: self.app_settings.llm_response_error_log_chars],
            )
            raise

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

