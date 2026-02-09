"""AAA IaC artifacts tool.

Provides a deterministic tool to persist IaC artifacts and static validation
results into ProjectState. Cost estimation is intentionally handled by the
separate cost tool module to keep concerns fully decoupled.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

from langchain.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


IacFormat = Literal["bicep", "terraform", "arm", "yaml", "json", "other"]
ValidationStatus = Literal["pass", "fail", "skipped"]


class IaCFileInput(BaseModel):
    path: str = Field(min_length=1, description="Relative path for the file (e.g., infra/main.bicep)")
    format: IacFormat = Field(description="IaC format")
    content: str = Field(min_length=1, description="File content")


class IaCValidationResultInput(BaseModel):
    tool: str = Field(min_length=1, description="Validator name (e.g., bicep build, terraform validate)")
    status: ValidationStatus = Field(description="pass|fail|skipped")
    output: str | None = Field(default=None, description="Raw output (trimmed) or summary")


class AAAGenerateIacInput(BaseModel):
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="forbid")

    iac_files: list[IaCFileInput] = Field(default_factory=list, description="IaC files to persist")
    validation_results: list[IaCValidationResultInput] = Field(
        default_factory=list, description="Static validation results (recording only)"
    )


class AAAGenerateIacToolInput(BaseModel):
    """Raw tool payload for IaC artifacts."""

    payload: str | dict[str, Any] = Field(
        description="A JSON object (or JSON string) matching AAAGenerateIacInput."
    )


class AAAGenerateIacTool(BaseTool):
    name: str = "aaa_record_iac_artifacts"
    description: str = (
        "Record IaC artifacts and static validation results. "
        "Returns an AAA_STATE_UPDATE JSON block with iacArtifacts."
    )

    args_schema: type[BaseModel] = AAAGenerateIacToolInput

    def _run(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> str:
        try:
            raw_data = self._parse_payload(payload, **kwargs)
            args = AAAGenerateIacInput.model_validate(raw_data)
            updates = self._build_updates(args)
            return self._format_response(updates, args)
        except Exception as exc:  # noqa: BLE001
            return f"ERROR: {exc!s}"

    async def _arun(self, payload: str | dict[str, Any] | None = None, **kwargs: Any) -> str:
        return self._run(payload=payload, **kwargs)

    def _parse_payload(self, payload: str | dict[str, Any] | None, **kwargs: Any) -> Any:
        if payload is None:
            payload = kwargs.get("payload") or kwargs.get("tool_input")
            if payload is None:
                payload = kwargs
            if not payload:
                raise ValueError(f"Missing payload for {self.name}")

        if isinstance(payload, str):
            try:
                return json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON payload for IaC artifacts.") from exc
        return payload

    def _build_updates(self, args: AAAGenerateIacInput) -> dict[str, Any]:
        updates: dict[str, Any] = {}
        iac_files_list = [f.model_dump() for f in args.iac_files]
        val_results_list = [r.model_dump() for r in args.validation_results]

        if iac_files_list or val_results_list:
            updates["iacArtifacts"] = [
                {
                    "id": str(uuid.uuid4()),
                    "createdAt": _now_iso(),
                    "files": iac_files_list,
                    "validationResults": val_results_list,
                }
            ]

        return updates

    def _format_response(self, updates: dict[str, Any], args: AAAGenerateIacInput) -> str:
        payload_json = json.dumps(updates, ensure_ascii=False, indent=2)
        return (
            f"Recorded IaC artifacts at {_now_iso()} (iacFiles={len(args.iac_files)}).\n"
            "\n"
            "AAA_STATE_UPDATE\n"
            "```json\n"
            f"{payload_json}\n"
            "```"
        )


def create_iac_tools() -> list[BaseTool]:
    return [AAAGenerateIacTool()]
