"""Compatibility wrapper for the feature-owned AAA artifacts tool."""

from app.features.agent.infrastructure.tools.aaa_artifacts_tool import (
    AAAManageArtifactsTool,
    AAAManageArtifactsToolInput,
)

__all__ = [
    "AAAManageArtifactsTool",
    "AAAManageArtifactsToolInput",
]
