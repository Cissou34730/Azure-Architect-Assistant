"""AAA candidate architecture tool.

User Story 2 (T018/T019): Provide a deterministic tool that lets the agent
persist candidate architectures + assumptions + citations into ProjectState
via the existing state update pipeline.

This tool does NOT call external services. The agent is expected to gather
sources using existing tools (kb_search, microsoft_docs_search, etc.) and then
call this tool to package the result as an AAA_STATE_UPDATE JSON payload.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from langchain.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel

from .aaa_adr_tool import AAAManageAdrTool
from .aaa_diagram_tool import AAACreateDiagramSetTool
from .aaa_export_tool import AAAExportTool
from .aaa_iac_tool import AAAGenerateIacTool
from .aaa_validation_tool import AAARunValidationTool


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AAAGenerateCandidateInput(BaseModel):
    """Input schema for generating a candidate architecture state update."""

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    title: str = Field(min_length=1, description="Short candidate name")
    summary: str = Field(min_length=1, description="Concise candidate summary")

    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions (each becomes an Assumption artifact with status=open)",
    )

    diagram_ids: list[str] = Field(
        default_factory=list,
        description="Related diagram IDs (e.g., c4_context) if already generated",
    )

    source_citations: list[dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "SourceCitation[] objects. The agent should build these from logged "
            "referenceDocuments / mcpQueries so they can be persisted and rendered."
        ),
    )


class AAAGenerateCandidateToolInput(BaseModel):
    """Raw tool payload for candidate generation."""

    payload: str | dict[str, Any] = Field(
        description="A JSON object (or JSON string) matching AAAGenerateCandidateInput."
    )


class AAAGenerateCandidateTool(BaseTool):
    """Tool to create a CandidateArchitecture + Assumption artifacts as a state update."""

    name: str = "aaa_generate_candidate_architecture"
    description: str = (
        "Create a CandidateArchitecture artifact (plus Assumption artifacts) and return an "
        "AAA_STATE_UPDATE JSON block that can be merged into ProjectState without overwriting. "
        "Use after gathering sources via kb_search/microsoft_docs_search so you can include "
        "sourceCitations."
    )

    args_schema: type[BaseModel] = AAAGenerateCandidateToolInput

    def _run(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            raw_data = self._parse_payload(payload, **kwargs)
            args = self._validate_args(raw_data)

            candidate_id = str(uuid.uuid4())
            assumption_items, assumption_ids = self._build_assumptions(args.assumptions)

            candidate = {
                "id": candidate_id,
                "title": args.title.strip(),
                "summary": args.summary.strip(),
                "assumptionIds": assumption_ids,
                "diagramIds": args.diagram_ids,
                "sourceCitations": args.source_citations,
            }

            updates = {
                "assumptions": assumption_items,
                "candidateArchitectures": [candidate],
            }

            payload_str = json.dumps(updates, ensure_ascii=False, indent=2)

            return (
                f"Created candidate architecture '{candidate['title']}' (id={candidate_id}) at {_now_iso()}.\n"
                "\n"
                "AAA_STATE_UPDATE\n"
                "```json\n"
                f"{payload_str}\n"
                "```"
            )
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {exc!s}"

    def _parse_payload(self, payload: str | dict[str, Any] | None, **kwargs: Any) -> dict[str, Any]:
        if payload is None:
            payload = kwargs.get("payload") or kwargs.get("tool_input")
            if payload is None:
                raise ValueError("Missing payload for candidate generation")

        if isinstance(payload, str):
            try:
                return json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON payload for candidate generation.") from exc
        return payload if isinstance(payload, dict) else {}

    def _validate_args(self, data: dict[str, Any]) -> AAAGenerateCandidateInput:
        if not data:
            raise ValueError("Payload data is empty or invalid.")
        try:
            return AAAGenerateCandidateInput.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"Validation failed: {exc!s}") from exc

    def _build_assumptions(self, text_list: list[str]) -> tuple[list[dict[str, Any]], list[str]]:
        items = []
        ids = []
        for text in text_list:
            clean = text.strip()
            if not clean:
                continue
            a_id = str(uuid.uuid4())
            ids.append(a_id)
            items.append(
                {
                    "id": a_id,
                    "text": clean,
                    "status": "open",
                    "relatedRequirementIds": [],
                }
            )
        return items, ids

    async def _arun(self, **kwargs: Any) -> str:
        return self._run(**kwargs)


def create_aaa_tools(_context: Any | None = None) -> list[BaseTool]:
    """Factory returning AAA-specific tools for the agent."""

    return [
        AAAGenerateCandidateTool(),
        AAAManageAdrTool(),
        AAACreateDiagramSetTool(),
        AAARunValidationTool(),
        AAAGenerateIacTool(),
        AAAExportTool(),
    ]

