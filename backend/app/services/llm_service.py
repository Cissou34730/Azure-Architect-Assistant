"""
LLM Service for document analysis, chat, and proposal generation.
Uses unified AI service layer for provider abstraction.
"""

import logging
import json
import re
from typing import Dict, List, Any, Optional, Callable

from app.services.ai import get_ai_service, ChatMessage

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM operations in project workflow."""

    def __init__(self):
        self.ai_service = get_ai_service()
        self.model = self.ai_service.get_llm_model()
        logger.info(f"LLMService ready with model: {self.model}")

    async def analyze_documents(self, document_texts: List[str]) -> Dict[str, Any]:
        """
        Analyze documents and extract ProjectState structure.

        Args:
            document_texts: List of document text content

        Returns:
            Dictionary representing ProjectState
        """
        # Analysis document count log suppressed

        combined_text = "\n\n---\n\n".join(document_texts)

        system_prompt = """You are an Azure Architecture Assistant. Analyze the provided project documents and extract key information to create a structured Architecture Sheet (ProjectState).

Your response MUST be a valid JSON object with the following structure:
{
  "context": {
    "summary": "Brief project summary",
    "objectives": ["objective1", "objective2"],
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
    "comsponents": [{"name": "component name", "description": "component description"}],
    "integrations": ["integration1", "integration2"]
  },
  "dataCompliance": {
    "dataTypes": ["data type1", "data type2"],
    "complianceRequirements": ["requirement1", "requirement2"],
    "dataResidency": "Data residency requirements"
  },
  "technicalConstraints": {
    "constraints": ["constraint1", "constraint2"],
    "assumptions": ["assumption1", "assumption2"]
  },
  "openQuestions": ["question1", "question2"]
}

Extract as much information as possible from the documents. For missing information, leave fields empty or use empty arrays."""

        user_prompt = f"Analyze these project documents and extract the Architecture Sheet:\n\n{combined_text}"

        response = await self._complete(system_prompt, user_prompt)
        project_state = self._parse_project_state(response)

        # Analysis completion log suppressed
        return project_state

    async def process_chat_message(
        self,
        user_message: str,
        current_state: Dict[str, Any],
        recent_messages: List[Dict[str, Any]],
        kb_sources: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
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
        state: Dict[str, Any],
        on_progress: Optional[Callable[[str, Optional[str]], None]] = None,
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

    def _parse_project_state(self, response: str) -> Dict[str, Any]:
        """Parse ProjectState from LLM response."""
        # Extract JSON from response
        json_match = re.search(r"\{[\s\S]*\}", response)
        if not json_match:
            logger.error("Failed to extract JSON from LLM response")
            raise ValueError("Failed to extract JSON from LLM response")

        parsed = json.loads(json_match.group(0))
        return parsed

    def _parse_chat_response(
        self, response: str, current_state: Dict[str, Any]
    ) -> Dict[str, Any]:
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
        self, state: Dict[str, Any], kb_context: str, has_kb_context: bool
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
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    """Get or create LLM service instance."""
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
