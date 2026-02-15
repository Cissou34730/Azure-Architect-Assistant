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
from typing import Any, Literal

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ExportFormat = Literal["json"]


class AAAExportInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    export_format: ExportFormat = Field(default="json", description="Export format")
    state: dict[str, Any] = Field(description="ProjectState.state payload to export")
    pretty: bool = Field(default=True, description="Pretty-print JSON")
    file_name: str | None = Field(default=None, description="Suggested file name")


class AAAExportToolInput(BaseModel):
    """Raw tool payload for export."""

    payload: str | dict[str, Any] = Field(
        description="A JSON object (or JSON string) matching AAAExportInput."
    )


class AAAExportTool(BaseTool):
    name: str = "aaa_export_state"
    description: str = (
        "Export AAA artifacts (including traceability links) from a provided ProjectState.state. "
        "Returns an AAA_EXPORT payload as a JSON code block."
    )

    args_schema: type[BaseModel] = AAAExportToolInput

    def _run(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            raw_data = self._parse_payload(payload, **kwargs)
            args = self._validate_args(raw_data)

            payload_json = json.dumps(
                {
                    "exportedAt": _now_iso(),
                    "state": args.state or {},
                },
                ensure_ascii=False,
                indent=2 if args.pretty else None,
            )

            suggested = args.file_name or "aaa-export.json"

            return (
                f"Exported AAA state to {suggested} at {_now_iso()}.\n"
                "\n"
                "AAA_EXPORT\n"
                "```json\n"
                f"{payload_json}\n"
                "```"
            )
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {exc!s}"

    def _parse_payload(self, payload: str | dict[str, Any] | None, **kwargs: Any) -> dict[str, Any]:
        if payload is None:
            payload = kwargs.get("payload") or kwargs.get("tool_input") or kwargs
            if not payload:
                raise ValueError("Missing payload for aaa_export_state")

        if isinstance(payload, str):
            try:
                return json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON payload for export.") from exc
        return payload if isinstance(payload, dict) else {}

    def _validate_args(self, data: dict[str, Any]) -> AAAExportInput:
        try:
            return AAAExportInput.model_validate(data)
        except ValidationError as exc:
            raise ValueError(f"Validation failed: {exc!s}") from exc

    async def _arun(self, **kwargs: Any) -> str:
        return self._run(**kwargs)

def create_export_tools() -> list[BaseTool]:
    return [AAAExportTool()]

