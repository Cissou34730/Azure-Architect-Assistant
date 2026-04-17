from __future__ import annotations

import asyncio
import json
from typing import Any, Literal

import yaml  # type: ignore[import-untyped]  # PyYAML ships without inline type information.
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

_DIAGNOSTIC_CONFIG = ConfigDict(populate_by_name=True, alias_generator=to_camel, extra="forbid")

IacFormat = Literal["bicep", "terraform", "arm", "yaml", "json", "other"]
ValidationSeverity = Literal["error"]

_ARM_REQUIRED_KEYS: tuple[str, ...] = ("$schema", "contentVersion", "resources")
_BICEP_DECLARATIONS: tuple[str, ...] = ("param", "resource", "module", "output", "var", "targetScope")
_TERRAFORM_BLOCKS: tuple[str, ...] = (
    "resource",
    "module",
    "data",
    "provider",
    "terraform",
    "variable",
    "output",
    "locals",
)


class ValidationDiagnostic(BaseModel):
    model_config = _DIAGNOSTIC_CONFIG

    message: str
    line: int | None = None
    severity: ValidationSeverity = "error"


class IacFileValidationInput(BaseModel):
    model_config = _DIAGNOSTIC_CONFIG

    path: str = Field(min_length=1)
    format: IacFormat
    content: str = Field(min_length=1)


class AAAValidateIacBundleInput(BaseModel):
    model_config = _DIAGNOSTIC_CONFIG

    files: list[IacFileValidationInput] = Field(default_factory=list, min_length=1)


class AAAValidateIacBundleToolInput(BaseModel):
    payload: str | dict[str, Any] = Field(
        description="A JSON object (or JSON string) matching AAAValidateIacBundleInput."
    )


class IacFileValidationResult(BaseModel):
    model_config = _DIAGNOSTIC_CONFIG

    path: str
    format: IacFormat
    valid: bool
    errors: list[ValidationDiagnostic] = Field(default_factory=list)


class IacBundleValidationResult(BaseModel):
    model_config = _DIAGNOSTIC_CONFIG

    valid: bool
    file_results: list[IacFileValidationResult]


class AAAValidateIacBundleTool(BaseTool):
    name: str = "aaa_validate_iac_bundle"
    description: str = (
        "Validate generated IaC bundles and schema-backed JSON/YAML outputs before persistence. "
        "Returns structured per-file diagnostics for ARM, Bicep, Terraform, JSON, and YAML files."
    )

    args_schema: type[BaseModel] = AAAValidateIacBundleToolInput

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
        args = AAAValidateIacBundleInput.model_validate(raw_data)
        file_results = [_validate_iac_file(item) for item in args.files]
        return IacBundleValidationResult(
            valid=all(result.valid for result in file_results),
            file_results=file_results,
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
                raise ValueError("Invalid JSON payload for IaC validation.") from exc
        return payload


def _validate_iac_file(file_input: IacFileValidationInput) -> IacFileValidationResult:
    diagnostics = _validate_content(file_input)
    return IacFileValidationResult(
        path=file_input.path,
        format=file_input.format,
        valid=not diagnostics,
        errors=diagnostics,
    )


def _validate_content(file_input: IacFileValidationInput) -> list[ValidationDiagnostic]:
    format_name = file_input.format
    if format_name == "arm":
        return _validate_arm_template(file_input.content)
    if format_name == "json":
        return _validate_json_document(file_input.content)
    if format_name == "yaml":
        return _validate_yaml_document(file_input.content)
    if format_name == "bicep":
        return _validate_bicep_document(file_input.content)
    if format_name == "terraform":
        return _validate_terraform_document(file_input.content)
    return []


def _validate_arm_template(content: str) -> list[ValidationDiagnostic]:
    document, diagnostics = _load_json_document(content)
    if diagnostics:
        return diagnostics
    if not isinstance(document, dict):
        return [ValidationDiagnostic(message="ARM templates must be JSON objects.", line=1)]

    errors: list[ValidationDiagnostic] = []
    for key in _ARM_REQUIRED_KEYS:
        if key not in document:
            message = {
                "$schema": "ARM templates must define a top-level $schema value.",
                "contentVersion": "ARM templates must define a top-level contentVersion value.",
                "resources": "ARM templates must define a top-level resources list.",
            }[key]
            errors.append(ValidationDiagnostic(message=message, line=1))
    resources = document.get("resources")
    if "resources" in document and not isinstance(resources, list):
        errors.append(
            ValidationDiagnostic(
                message="ARM templates must define resources as a list.",
                line=1,
            )
        )
    return errors


def _validate_json_document(content: str) -> list[ValidationDiagnostic]:
    _, diagnostics = _load_json_document(content)
    return diagnostics


def _load_json_document(content: str) -> tuple[Any | None, list[ValidationDiagnostic]]:
    try:
        return json.loads(content), []
    except json.JSONDecodeError as exc:
        return None, [ValidationDiagnostic(message=exc.msg, line=exc.lineno)]


def _validate_yaml_document(content: str) -> list[ValidationDiagnostic]:
    try:
        yaml.safe_load(content)
    except yaml.YAMLError as exc:
        problem_mark = getattr(exc, "problem_mark", None)
        line = problem_mark.line + 1 if problem_mark is not None else None
        return [ValidationDiagnostic(message=str(exc), line=line)]
    return []


def _validate_bicep_document(content: str) -> list[ValidationDiagnostic]:
    bracket_error = _find_unbalanced_delimiter(content)
    if bracket_error is not None:
        return [bracket_error]
    if not _contains_declaration(content, _BICEP_DECLARATIONS):
        return [
            ValidationDiagnostic(
                message="Bicep files must declare at least one param, resource, module, var, output, or targetScope statement.",
                line=1,
            )
        ]
    return []


def _validate_terraform_document(content: str) -> list[ValidationDiagnostic]:
    bracket_error = _find_unbalanced_delimiter(content)
    if bracket_error is not None:
        return [bracket_error]
    if not _contains_declaration(content, _TERRAFORM_BLOCKS):
        return [
            ValidationDiagnostic(
                message="Terraform files must declare at least one resource, module, data, provider, terraform, variable, output, or locals block.",
                line=1,
            )
        ]
    return []


def _contains_declaration(content: str, declarations: tuple[str, ...]) -> bool:
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue
        if any(line.startswith(f"{declaration} ") or line == declaration for declaration in declarations):
            return True
    return False


_DELIMITER_PAIRS: dict[str, str] = {"(": ")", "[": "]", "{": "}"}


def _find_unbalanced_delimiter(content: str) -> ValidationDiagnostic | None:
    stack: list[tuple[str, int]] = []
    for index, char in enumerate(content):
        if char in _DELIMITER_PAIRS:
            stack.append((char, index))
            continue
        if char not in _DELIMITER_PAIRS.values():
            continue
        if not stack:
            return ValidationDiagnostic(
                message=f"Unmatched closing delimiter '{char}'.",
                line=_line_number_for_offset(content, index),
            )
        opening, opening_index = stack.pop()
        if _DELIMITER_PAIRS[opening] != char:
            return ValidationDiagnostic(
                message=f"Mismatched delimiters: '{opening}' closed by '{char}'.",
                line=_line_number_for_offset(content, opening_index),
            )
    if not stack:
        return None
    opening, opening_index = stack[-1]
    return ValidationDiagnostic(
        message=f"Unclosed delimiter '{opening}'.",
        line=_line_number_for_offset(content, opening_index),
    )


def _line_number_for_offset(content: str, offset: int) -> int:
    return content[:offset].count("\n") + 1


def create_iac_validation_tools() -> list[BaseTool]:
    return [AAAValidateIacBundleTool()]
