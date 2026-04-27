from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.agents_system.memory.compaction_service import CompactionService


class _PromptLoaderStub:
    def __init__(self) -> None:
        self.loaded: list[str] = []

    def load_prompt(self, prompt_name: str) -> dict[str, object]:
        self.loaded.append(prompt_name)
        return {
            "compaction": {
                "system": "Summarize Azure architecture turns.",
                "with_existing_summary": (
                    "Previous conversation summary:\n"
                    "{existing_summary}\n\n"
                    "New conversation turns to incorporate:\n"
                    "{new_turns}"
                ),
                "without_existing_summary": (
                    "Conversation turns to summarize:\n"
                    "{turns}"
                ),
            }
        }

    def load_prompt_file(self, prompt_name: str) -> dict[str, object]:
        return self.load_prompt(prompt_name)


def test_build_compaction_prompt_uses_yaml_templates() -> None:
    service = CompactionService(prompt_loader=_PromptLoaderStub())

    prompt = service.build_compaction_prompt(
        [{"role": "user", "content": "Need an Azure SQL fallback."}],
        existing_summary="Existing requirements",
    )

    assert "Existing requirements" in prompt
    assert "[user]: Need an Azure SQL fallback." in prompt


@pytest.mark.asyncio
async def test_compact_uses_yaml_system_prompt() -> None:
    prompt_loader = _PromptLoaderStub()
    service = CompactionService(
        compact_threshold_tokens=1,
        max_recent_turns=0,
        prompt_loader=prompt_loader,
    )
    captured: list[object] = []

    class _LLMStub:
        async def ainvoke(self, messages: list[object]) -> object:
            captured.extend(messages)
            return SimpleNamespace(content="Summarized thread")

    summary = await service.compact(
        [{"role": "assistant", "content": "Adopt Azure SQL Database."}],
        llm=_LLMStub(),
        existing_summary="Current direction",
    )

    assert summary == "Summarized thread"
    assert prompt_loader.loaded == ["memory_compaction_prompt.yaml", "memory_compaction_prompt.yaml"]
    assert captured[0].content == "Summarize Azure architecture turns."
    assert "Current direction" in captured[1].content
