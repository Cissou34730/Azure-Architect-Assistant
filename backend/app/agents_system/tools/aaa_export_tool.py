"""AAA export tool.

User Story 6 (T039): Export the current AAA artifacts with traceability links.

This tool is designed for the agent:
- The agent already has ProjectState (or a subset) in context
- The agent passes it into this tool, which returns a stable export payload

No external calls are made.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional, Type, Union

from langchain.tools import BaseTool
from pydantic import BaseModel, Field


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ExportFormat = Literal["json"]


class AAAExportInput(BaseModel):
    exportFormat: ExportFormat = Field(default="json", description="Export format")
    state: Dict[str, Any] = Field(description="ProjectState.state payload to export")
    pretty: bool = Field(default=True, description="Pretty-print JSON")
    fileName: Optional[str] = Field(default=None, description="Suggested file name")


class AAAExportToolInput(BaseModel):
    """Raw tool payload for export."""

    payload: Union[str, Dict[str, Any]] = Field(
        description="A JSON object (or JSON string) matching AAAExportInput."
    )


class AAAExportTool(BaseTool):
    name: str = "aaa_export_state"
    description: str = (
        "Export AAA artifacts (including traceability links) from a provided ProjectState.state. "
        "Returns an AAA_EXPORT payload as a JSON code block."
    )

    args_schema: Type[BaseModel] = AAAExportToolInput

    def _run(
        self,
        payload: Union[str, Dict[str, Any], None] = None,
        **kwargs: Any,
    ) -> str:
        if payload is None:
            if "payload" in kwargs:
                payload = kwargs["payload"]
            else:
                raise ValueError("Missing payload for aaa_export_state")

        if isinstance(payload, str):
            try:
                data = json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON payload for export.") from exc
        else:
            data = payload

        try:
            args = AAAExportInput.model_validate(data)
        except Exception as exc:
            return f"ERROR: Validation failed for AAAExportInput: {str(exc)}"

        exportFormat = args.exportFormat
        state_data = args.state
        pretty = args.pretty
        fileName = args.fileName

        export_state = state_data or {}

        if exportFormat != "json":
            raise ValueError(f"Unsupported exportFormat: {exportFormat}")

        payload_json = json.dumps(
            {
                "exportedAt": _now_iso(),
                "state": export_state,
            },
            ensure_ascii=False,
            indent=2 if pretty else None,
        )

        suggested = fileName or "aaa-export.json"

        return (
            f"Exported AAA state to {suggested} at {_now_iso()}.\n"
            "\n"
            "AAA_EXPORT\n"
            "```json\n"
            f"{payload_json}\n"
            "```"
        )

    async def _arun(self, **kwargs: Any) -> str:
        return self._run(**kwargs)


def create_export_tools() -> list[BaseTool]:
    return [AAAExportTool()]
