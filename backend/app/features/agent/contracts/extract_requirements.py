"""Contracts for structured requirements extraction results."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

_EXTRACTION_CONFIG = ConfigDict(
    populate_by_name=True,
    alias_generator=to_camel,
    extra="forbid",
)

RequirementCategory = Literal["business", "functional", "nfr", "constraint"]


class RequirementSourceContract(BaseModel):
    model_config = _EXTRACTION_CONFIG

    document_id: str = Field(alias="documentId")
    excerpt: str
    location: str | None = None


class RequirementAmbiguityContract(BaseModel):
    model_config = _EXTRACTION_CONFIG

    is_ambiguous: bool = Field(alias="isAmbiguous")
    notes: str = ""


class ExtractedRequirementContract(BaseModel):
    model_config = _EXTRACTION_CONFIG

    text: str
    category: RequirementCategory
    ambiguity: RequirementAmbiguityContract
    sources: list[RequirementSourceContract]

    @field_validator("text")
    @classmethod
    def _validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Requirement text must not be empty")
        return cleaned

    @field_validator("sources")
    @classmethod
    def _validate_sources(cls, value: list[RequirementSourceContract]) -> list[RequirementSourceContract]:
        if not value:
            raise ValueError("Extracted requirement must include at least one source")
        return value


class RequirementsExtractionResultContract(BaseModel):
    model_config = _EXTRACTION_CONFIG

    requirements: list[ExtractedRequirementContract]
    assumptions: list[str] = Field(default_factory=list)
    ambiguities_detected: int = Field(alias="ambiguitiesDetected")
    chunks_processed: int = Field(alias="chunksProcessed")
