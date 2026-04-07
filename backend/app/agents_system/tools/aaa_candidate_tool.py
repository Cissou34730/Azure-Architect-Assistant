"""Compatibility wrapper for the feature-owned AAA tool factory."""

from app.features.agent.infrastructure.tools import (
    AAAGenerateCandidateInput,
    AAAGenerateCandidateTool,
    AAAGenerateCandidateToolInput,
    create_aaa_tools,
)

__all__ = [
    "AAAGenerateCandidateInput",
    "AAAGenerateCandidateTool",
    "AAAGenerateCandidateToolInput",
    "create_aaa_tools",
]

