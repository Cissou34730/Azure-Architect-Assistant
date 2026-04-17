"""LLM seam for structured ADR drafting."""

from __future__ import annotations

import inspect
import json
from collections.abc import Awaitable, Callable, Mapping
from copy import deepcopy
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel

from app.agents_system.config.prompt_loader import PromptLoader
from app.shared.ai import llm_service

ADRDraftAction = Literal["create", "supersede"]


class ADRDraftArtifact(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        extra="forbid",
    )

    title: str
    context: str
    decision: str
    consequences: str
    alternatives_considered: list[str] = Field(alias="alternativesConsidered")
    related_requirement_ids: list[str] = Field(alias="relatedRequirementIds")
    related_mind_map_node_ids: list[str] = Field(default_factory=list, alias="relatedMindMapNodeIds")
    related_diagram_ids: list[str] = Field(default_factory=list, alias="relatedDiagramIds")
    related_waf_evidence_ids: list[str] = Field(default_factory=list, alias="relatedWafEvidenceIds")
    missing_evidence_reason: str | None = Field(default=None, alias="missingEvidenceReason")
    source_citations: list[dict[str, Any]] = Field(default_factory=list, alias="sourceCitations")
    supersedes_adr_id: str | None = Field(default=None, alias="supersedesAdrId")


class ADRDraftEnvelope(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        extra="forbid",
    )

    action: ADRDraftAction
    adr: ADRDraftArtifact


ADRGenerator = Callable[[str, str], dict[str, Any] | str | Awaitable[dict[str, Any] | str]]


class ADRDrafterWorker:
    """Generate a structured ADR draft from prompt-grounded project context."""

    def __init__(
        self,
        *,
        generator: ADRGenerator | None = None,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        self._generator = generator or self._default_generator
        self._prompt_loader = prompt_loader or PromptLoader.get_instance()

    async def draft_adr(
        self,
        *,
        user_message: str,
        project_state: Mapping[str, Any],
        requested_action: ADRDraftAction,
        target_adr: Mapping[str, Any] | None = None,
    ) -> ADRDraftEnvelope:
        prompt = self._prompt_loader.load_prompt_file("adr_writer.yaml")
        system_prompt = str(prompt.get("system_prompt") or "").strip()
        user_prompt = self._build_user_prompt(
            user_message=user_message,
            project_state=project_state,
            requested_action=requested_action,
            target_adr=target_adr,
        )
        raw_response = self._generator(system_prompt, user_prompt)
        if inspect.isawaitable(raw_response):
            raw_response = await raw_response
        envelope = self._parse_response(raw_response)
        if envelope.action != requested_action:
            raise ValueError(
                f"ADR drafter returned action '{envelope.action}' when '{requested_action}' was required."
            )
        return envelope

    async def _default_generator(self, system_prompt: str, user_prompt: str) -> str:
        return await llm_service.get_llm_service()._complete(  # pyright: ignore[reportPrivateUsage]
            system_prompt,
            user_prompt,
            max_tokens=2000,
        )

    def _parse_response(self, response: dict[str, Any] | str) -> ADRDraftEnvelope:
        payload = response
        if isinstance(response, str):
            payload = json.loads(response)
        if not isinstance(payload, dict):
            raise ValueError("ADR drafter returned an invalid payload.")
        try:
            return ADRDraftEnvelope.model_validate(payload)
        except ValidationError as exc:
            raise ValueError(str(exc)) from exc

    def _build_user_prompt(
        self,
        *,
        user_message: str,
        project_state: Mapping[str, Any],
        requested_action: ADRDraftAction,
        target_adr: Mapping[str, Any] | None,
    ) -> str:
        response_contract = {
            "action": requested_action,
            "adr": {
                "title": "string",
                "context": "string",
                "decision": "string",
                "consequences": "string",
                "alternativesConsidered": ["string"],
                "relatedRequirementIds": ["string"],
                "relatedMindMapNodeIds": ["string"],
                "relatedDiagramIds": ["string"],
                "relatedWafEvidenceIds": ["string"],
                "missingEvidenceReason": "string|null",
                "sourceCitations": [
                    {
                        "id": "string",
                        "kind": "referenceDocument|mcp",
                        "referenceDocumentId": "string|null",
                        "mcpQueryId": "string|null",
                        "url": "string|null",
                        "note": "string|null",
                    }
                ],
                "supersedesAdrId": "string|null",
            },
        }
        payload = {
            "requestedAction": requested_action,
            "userMessage": user_message,
            "targetAdr": deepcopy(dict(target_adr)) if isinstance(target_adr, Mapping) else None,
            "projectState": {
                key: deepcopy(project_state.get(key))
                for key in (
                    "requirements",
                    "assumptions",
                    "candidateArchitectures",
                    "adrs",
                    "diagrams",
                    "findings",
                    "mindMap",
                    "referenceDocuments",
                    "mcpQueries",
                )
                if project_state.get(key) is not None
            },
            "responseContract": response_contract,
        }
        return (
            "Return JSON only.\n"
            "Use the responseContract exactly.\n"
            "Draft a structured ADR with explicit alternativesConsidered and traceability.\n"
            "Do not omit source citations or requirement links.\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )


__all__ = ["ADRDraftArtifact", "ADRDraftEnvelope", "ADRDrafterWorker"]

