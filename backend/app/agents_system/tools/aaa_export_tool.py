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
from typing import Any, Dict, Literal, Optional, Type

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


class AAAExportTool(BaseTool):
    name: str = "aaa_export_state"
    description: str = (
        "Export AAA artifacts (including traceability links) from a provided ProjectState.state. "
        "Returns an AAA_EXPORT payload as a JSON code block."
    )

    args_schema: Type[BaseModel] = AAAExportInput

    def _run(
        self,
        exportFormat: ExportFormat = "json",
        state: Optional[Dict[str, Any]] = None,
        pretty: bool = True,
        fileName: Optional[str] = None,
    ) -> str:
        export_state = state or {}

        if exportFormat != "json":
            raise ValueError(f"Unsupported exportFormat: {exportFormat}")

        payload = json.dumps(
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
            f"{payload}\n"
            "```"
        )

    async def _arun(self, **kwargs: Any) -> str:
        return self._run(**kwargs)


def create_export_tools() -> list[BaseTool]:
    return [AAAExportTool()]
