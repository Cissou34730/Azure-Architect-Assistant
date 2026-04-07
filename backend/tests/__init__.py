"""Tests for the state update parser merge logic — _remove and _replace_ support."""

from __future__ import annotations

from typing import Any

from app.agents_system.services.state_update_parser import (
    merge_state_updates_no_overwrite,
)

# ── _replace_ flag support ────────────────────────────────────────────


def test_replace_flag_replaces_entire_list() -> None:
    current: dict[str, Any] = {
        "clarificationQuestions": [
            {"id": "q-old", "question": "Old question", "status": "open"},
        ],
    }
    updates: dict[str, Any] = {
        "clarificationQuestions": [
            {"id": "q-new", "question": "New question", "status": "open"},
        ],
        "_replace_clarificationQuestions": True,
    }

    result = merge_state_updates_no_overwrite(current, updates)

    assert len(result.merged_state["clarificationQuestions"]) == 1
    assert result.merged_state["clarificationQuestions"][0]["id"] == "q-new"
    assert not result.conflicts


def test_replace_flag_not_present_merges_normally() -> None:
    current: dict[str, Any] = {
        "requirements": [
            {"id": "r-1", "text": "Existing", "category": "nfr"},
        ],
    }
    updates: dict[str, Any] = {
        "requirements": [
            {"id": "r-2", "text": "New", "category": "functional"},
        ],
    }

    result = merge_state_updates_no_overwrite(current, updates)

    assert len(result.merged_state["requirements"]) == 2


def test_replace_flag_ignored_for_non_list() -> None:
    current: dict[str, Any] = {"name": "Old"}
    updates: dict[str, Any] = {"name": "New", "_replace_name": True}

    result = merge_state_updates_no_overwrite(current, updates)

    # Non-list: _replace_ flag is ignored; normal scalar overwrite-block applies
    assert result.merged_state["name"] == "Old"
    assert len(result.conflicts) == 1


# ── _remove flag support ─────────────────────────────────────────────


def test_remove_item_by_id() -> None:
    current: dict[str, Any] = {
        "assumptions": [
            {"id": "a-1", "text": "To keep", "status": "open"},
            {"id": "a-2", "text": "To remove", "status": "open"},
        ],
    }
    updates: dict[str, Any] = {
        "assumptions": [
            {"id": "a-2", "_remove": True},
        ],
    }

    result = merge_state_updates_no_overwrite(current, updates)

    assert len(result.merged_state["assumptions"]) == 1
    assert result.merged_state["assumptions"][0]["id"] == "a-1"


def test_remove_nonexistent_item_is_noop() -> None:
    current: dict[str, Any] = {
        "assumptions": [
            {"id": "a-1", "text": "Only item"},
        ],
    }
    updates: dict[str, Any] = {
        "assumptions": [
            {"id": "a-999", "_remove": True},
        ],
    }

    result = merge_state_updates_no_overwrite(current, updates)

    assert len(result.merged_state["assumptions"]) == 1
    assert result.merged_state["assumptions"][0]["id"] == "a-1"

