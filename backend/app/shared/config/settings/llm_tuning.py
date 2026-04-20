"""LLM extraction / tuning settings mixin.

Centralises all tuneable model-behaviour constants that were previously
scattered across application code as magic literals.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class LLMTuningSettingsMixin(BaseModel):
    # ── LLM extraction ────────────────────────────────────────────────────────
    llm_analyze_max_tokens: int = Field(
        default=12000, ge=512, le=32768,
        description="Max completion tokens used for document analysis extraction",
    )
    llm_json_repair_min_tokens: int = Field(
        default=1500, ge=256, le=16384,
        description="Minimum token budget for JSON repair retries",
    )
    llm_json_repair_token_divisor: int = Field(
        default=2, ge=1, le=16,
        description="Repair token budget divisor based on original request budget",
    )
    llm_response_preview_log_chars: int = Field(
        default=500, ge=100, le=10000,
        description="Max chars for debug response previews",
    )
    llm_response_error_log_chars: int = Field(
        default=1000, ge=100, le=20000,
        description="Max chars for error response snippets",
    )
    llm_request_timeout_seconds: float = Field(
        default=600.0, ge=10.0, le=3600.0,
        description="Timeout in seconds for LLM requests",
    )

    # ── Model probe (settings / model-switch validation) ──────────────────────
    models_probe_max_tokens: int = Field(
        default=64,
        description="Max tokens used for the lightweight model-availability probe",
    )
    models_probe_temperature: float = Field(
        default=0.0,
        description="Temperature used for the lightweight model-availability probe",
    )

    # ── Decision thresholds ───────────────────────────────────────────────────
    mindmap_confidence_threshold: float = Field(
        default=0.75,
        description="Minimum confidence score for a WAF address to be considered resolved",
    )
    mindmap_coverage_weight: float = Field(
        default=0.5,
        description="Weight applied when computing mindmap coverage score",
    )
    kb_similarity_threshold: float = Field(
        default=0.5,
        description="Default similarity threshold for KB vector search",
    )

    # ── Per-agent temperature overrides ──────────────────────────────────────
    chat_temperature: float = Field(
        default=0.1,
        description="Temperature for the stage-aware chat agent LLM calls",
    )

    # ── Agent iteration budget ───────────────────────────────────────────────
    chat_max_agent_iterations: int = Field(
        default=15, ge=5, le=50,
        description="Maximum tool-call iterations per agent turn before forcing a final answer",
    )

    # ── Intent classifier (cheap LLM call for artifact intent detection) ─────
    intent_classifier_max_tokens: int = Field(
        default=64, ge=16, le=256,
        description="Max tokens for the lightweight intent classification LLM call",
    )
    intent_classifier_timeout_seconds: float = Field(
        default=5.0, ge=1.0, le=30.0,
        description="Timeout in seconds for the intent classification LLM call",
    )
