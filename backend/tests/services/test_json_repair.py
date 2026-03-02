"""Tests for JSON repair utilities extracted from llm_service."""

import pytest

from app.services.ai.json_repair import (
    extract_json_candidate,
    parse_json_with_repair,
    repair_json_content,
)


# ---------------------------------------------------------------------------
# extract_json_candidate
# ---------------------------------------------------------------------------

class TestExtractJsonCandidate:
    def test_extracts_simple_object(self):
        assert extract_json_candidate('{"key": "value"}') == '{"key": "value"}'

    def test_extracts_from_surrounding_text(self):
        text = 'Here is the JSON: {"a": 1} done.'
        assert extract_json_candidate(text) == '{"a": 1}'

    def test_returns_none_when_no_json(self):
        assert extract_json_candidate("no json here") is None

    def test_returns_none_when_only_opening_brace(self):
        assert extract_json_candidate("{ broken") is None

    def test_returns_none_when_braces_reversed(self):
        assert extract_json_candidate("} before {") is None

    def test_handles_nested_braces(self):
        text = '{"outer": {"inner": 1}}'
        assert extract_json_candidate(text) == '{"outer": {"inner": 1}}'

    def test_handles_multiple_objects_returns_outermost(self):
        text = '{"a": 1} and {"b": 2}'
        result = extract_json_candidate(text)
        assert result == '{"a": 1} and {"b": 2}'

    def test_empty_string(self):
        assert extract_json_candidate("") is None


# ---------------------------------------------------------------------------
# parse_json_with_repair
# ---------------------------------------------------------------------------

class TestParseJsonWithRepair:
    @pytest.mark.asyncio
    async def test_valid_json_passes_through(self):
        async def fail_repair(_json: str, _tokens: int) -> str:
            raise AssertionError("repair should not be called")

        result = await parse_json_with_repair(
            '{"key": "value"}',
            max_tokens=100,
            repair_fn=fail_repair,
        )
        assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_invalid_json_triggers_repair(self):
        async def mock_repair(_json: str, _tokens: int) -> str:
            return '{"repaired": true}'

        result = await parse_json_with_repair(
            "{broken json",
            max_tokens=100,
            repair_fn=mock_repair,
        )
        assert result == {"repaired": True}

    @pytest.mark.asyncio
    async def test_repair_failure_raises(self):
        async def bad_repair(_json: str, _tokens: int) -> str:
            return "still broken"

        with pytest.raises(Exception):
            await parse_json_with_repair(
                "{broken json",
                max_tokens=100,
                repair_fn=bad_repair,
            )


# ---------------------------------------------------------------------------
# repair_json_content
# ---------------------------------------------------------------------------

class TestRepairJsonContent:
    @pytest.mark.asyncio
    async def test_successful_repair(self):
        async def mock_complete(_sys: str, _usr: str, _tokens: int) -> str:
            return '{"fixed": true}'

        result = await repair_json_content(
            "{bad json",
            max_tokens=100,
            complete_fn=mock_complete,
        )
        assert result == '{"fixed": true}'

    @pytest.mark.asyncio
    async def test_repair_with_surrounding_text(self):
        async def mock_complete(_sys: str, _usr: str, _tokens: int) -> str:
            return 'Here is the repaired JSON: {"fixed": true}'

        result = await repair_json_content(
            "{bad json",
            max_tokens=100,
            complete_fn=mock_complete,
        )
        assert result == '{"fixed": true}'

    @pytest.mark.asyncio
    async def test_repair_no_json_raises(self):
        async def mock_complete(_sys: str, _usr: str, _tokens: int) -> str:
            return "I cannot fix this"

        with pytest.raises(ValueError, match="no JSON object found"):
            await repair_json_content(
                "{bad json",
                max_tokens=100,
                complete_fn=mock_complete,
            )

    @pytest.mark.asyncio
    async def test_repair_passes_correct_prompts(self):
        captured: dict = {}

        async def capture_complete(sys: str, usr: str, tokens: int) -> str:
            captured["system"] = sys
            captured["user"] = usr
            captured["tokens"] = tokens
            return '{"result": 1}'

        await repair_json_content(
            "{bad",
            max_tokens=200,
            complete_fn=capture_complete,
        )
        assert "JSON repair" in captured["system"]
        assert "{bad" in captured["user"]
        assert captured["tokens"] == 200
