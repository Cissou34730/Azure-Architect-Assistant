"""Compatibility wrapper for the feature-owned AAA IaC tool."""

from app.features.agent.infrastructure.tools.aaa_iac_tool import (
    AAAGenerateIacInput,
    AAAGenerateIacTool,
    AAAGenerateIacToolInput,
)

__all__ = [
    "AAAGenerateIacInput",
    "AAAGenerateIacTool",
    "AAAGenerateIacToolInput",
]
