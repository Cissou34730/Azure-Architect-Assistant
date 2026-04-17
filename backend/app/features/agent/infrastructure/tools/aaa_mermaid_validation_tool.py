from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.features.diagrams.application.syntax_validator import SyntaxValidator

_DIAGNOSTIC_CONFIG = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="forbid")


class MermaidValidationError(BaseModel):
    model_config = _DIAGNOSTIC_CONFIG

    message: str
    line: int | None = None
    severity: Literal["error"] = "error"


class AAAMermaidValidationInput(BaseModel):
    model_config = _DIAGNOSTIC_CONFIG

    source_code: str = Field(min_length=1, description="Mermaid source code to validate.")


class AAAMermaidValidationToolInput(BaseModel):
    payload: str | dict[str, Any] = Field(
        description="A JSON object (or JSON string) matching AAAMermaidValidationInput."
    )


class MermaidValidationToolResult(BaseModel):
    model_config = _DIAGNOSTIC_CONFIG

    valid: bool
    detected_diagram_type: str | None = None
    errors: list[MermaidValidationError] = Field(default_factory=list)


class AAAMermaidValidationTool(BaseTool):
    name: str = "aaa_validate_mermaid_diagram"
    description: str = (
        "Validate Mermaid diagram syntax before persisting or presenting it. "
        "Returns a structured validity flag plus line-aware diagnostics."
    )

    args_schema: type[BaseModel] = AAAMermaidValidationToolInput

    def _run(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return asyncio.run(self._arun(payload=payload, **kwargs))

    async def _arun(
        self,
        payload: str | dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        raw_data = self._parse_payload(payload, **kwargs)
        args = AAAMermaidValidationInput.model_validate(raw_data)

        validator = SyntaxValidator()
        validation_result = await validator.validate_mermaid_syntax(args.source_code)
        detected_diagram_type = validator.detect_mermaid_diagram_type(args.source_code)

        errors: list[MermaidValidationError] = []
        if not validation_result.is_valid and validation_result.error:
            errors.append(
                MermaidValidationError(
                    message=validation_result.error,
                    line=validation_result.error_line,
                )
            )

        return MermaidValidationToolResult(
            valid=validation_result.is_valid,
            detected_diagram_type=detected_diagram_type,
            errors=errors,
        ).model_dump(mode="json", by_alias=True)

    def _parse_payload(
        self,
        payload: str | dict[str, Any] | None,
        **kwargs: Any,
    ) -> Any:
        if payload is None:
            payload = kwargs.get("payload") or kwargs.get("tool_input") or kwargs
        if not payload:
            raise ValueError(f"Missing payload for {self.name}")
        if isinstance(payload, str):
            try:
                return json.loads(payload.strip())
            except json.JSONDecodeError as exc:
                raise ValueError("Invalid JSON payload for Mermaid validation.") from exc
        return payload


def create_mermaid_validation_tools() -> list[BaseTool]:
    return [AAAMermaidValidationTool()]
