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
from typing import Any, Dict, List, Optional, Type, Union

from langchain.tools import BaseTool
from pydantic import BaseModel, Field

from .aaa_adr_tool import AAAManageAdrTool
from .aaa_validation_tool import AAARunValidationTool
from .aaa_iac_tool import AAAGenerateIacTool
from .aaa_export_tool import AAAExportTool


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AAAGenerateCandidateInput(BaseModel):
    """Input schema for generating a candidate architecture state update."""

    title: str = Field(min_length=1, description="Short candidate name")
    summary: str = Field(min_length=1, description="Concise candidate summary")

    assumptions: List[str] = Field(
        default_factory=list,
        description="Assumptions (each becomes an Assumption artifact with status=open)",
    )

    diagramIds: List[str] = Field(
        default_factory=list,
        description="Related diagram IDs (e.g., c4_context) if already generated",
    )

    sourceCitations: List[Dict[str, Any]] = Field(
        default_factory=list,
        description=(
            "SourceCitation[] objects. The agent should build these from logged "
            "referenceDocuments / mcpQueries so they can be persisted and rendered."
        ),
    )


class AAAGenerateCandidateToolInput(BaseModel):
    """Raw tool payload for candidate generation."""

    payload: Union[str, Dict[str, Any]] = Field(
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

    args_schema: Type[BaseModel] = AAAGenerateCandidateToolInput

    def _run(
        self,
        payload: Union[str, Dict[str, Any], None] = None,
        **kwargs: Any,
    ) -> str:
        if payload is None:
            if "payload" in kwargs:
                payload = kwargs["payload"]
            else:
                raise ValueError("Missing payload for aaa_generate_candidate_architecture")

        if isinstance(payload, str):
            try:
                data = json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON payload for candidate generation.") from exc
        else:
            data = payload

        try:
            args = AAAGenerateCandidateInput.model_validate(data)
        except Exception as exc:
            return f"ERROR: Validation failed for AAAGenerateCandidateInput: {str(exc)}"

        title = args.title
        summary = args.summary
        assumptions = args.assumptions
        diagramIds = args.diagramIds
        sourceCitations = args.sourceCitations

        candidate_id = str(uuid.uuid4())
        assumption_items: List[Dict[str, Any]] = []
        assumption_ids: List[str] = []

        for assumption_text in assumptions or []:
            clean = (assumption_text or "").strip()
            if not clean:
                continue
            assumption_id = str(uuid.uuid4())
            assumption_ids.append(assumption_id)
            assumption_items.append(
                {
                    "id": assumption_id,
                    "text": clean,
                    "status": "open",
                    "relatedRequirementIds": [],
                }
            )

        candidate = {
            "id": candidate_id,
            "title": title.strip(),
            "summary": summary.strip(),
            "assumptionIds": assumption_ids,
            "diagramIds": diagramIds or [],
            "sourceCitations": sourceCitations or [],
        }

        updates: Dict[str, Any] = {
            "assumptions": assumption_items,
            "candidateArchitectures": [candidate],
        }

        payload = json.dumps(updates, ensure_ascii=False, indent=2)

        return (
            f"Created candidate architecture '{candidate['title']}' (id={candidate_id}) at {_now_iso()}.\n"
            "\n"
            "AAA_STATE_UPDATE\n"
            "```json\n"
            f"{payload}\n"
            "```"
        )

    async def _arun(self, **kwargs: Any) -> str:
        # Keep async signature; actual work is fast and synchronous.
        return self._run(**kwargs)


def create_aaa_tools() -> List[BaseTool]:
    """Factory returning AAA-specific tools for the agent."""

    return [
        AAAGenerateCandidateTool(),
        AAAManageAdrTool(),
        AAARunValidationTool(),
        AAAGenerateIacTool(),
        AAAExportTool(),
    ]
