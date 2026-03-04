"""Helpers to process checklist updates embedded in agent output."""

from __future__ import annotations

import json
from typing import Any

from app.agents_system.checklists.engine import ChecklistEngine


def find_json_blocks(text: str, marker: str) -> list[dict[str, Any]]:  # noqa: C901, PLR0912
    """Extract top-level JSON objects that follow a marker in free-form text."""
    results: list[dict[str, Any]] = []
    search_from = 0
    while True:
        marker_index = text.find(marker, search_from)
        if marker_index < 0:
            break
        cursor = marker_index + len(marker)

        start = text.find("{", cursor)
        if start < 0:
            break

        brace_depth = 0
        in_string = False
        escaped = False
        end = -1
        for index in range(start, len(text)):
            char = text[index]
            if in_string:
                if escaped:
                    escaped = False
                    continue
                if char == "\\":
                    escaped = True
                    continue
                if char == '"':
                    in_string = False
                continue

            if char == '"':
                in_string = True
                continue
            if char == "{":
                brace_depth += 1
                continue
            if char == "}":
                brace_depth -= 1
                if brace_depth == 0:
                    end = index
                    break

        if end < 0:
            break

        block_text = text[start : end + 1]
        try:
            block = json.loads(block_text)
        except json.JSONDecodeError:
            search_from = end + 1
            continue

        if isinstance(block, dict):
            results.append(block)
        search_from = end + 1

    return results


class WafResultProcessor:
    """Process orchestrator output and persist embedded WAF checklist updates."""

    def __init__(self, engine: ChecklistEngine) -> None:
        self.engine = engine

    async def process_orchestrator_result(self, project_id: str, result: dict[str, Any]) -> None:
        output = str(result.get("output") or "")
        if not output.strip():
            return

        updates = find_json_blocks(output, "AAA_STATE_UPDATE:")
        for update in updates:
            waf_update = update.get("wafChecklist")
            if not isinstance(waf_update, dict):
                continue

            items = waf_update.get("items")
            if not isinstance(items, (list, dict)) or len(items) == 0:
                continue

            template_slug = str(
                waf_update.get("slug")
                or waf_update.get("template")
                or "azure-waf-v1"
            ).strip()
            await self.engine.ensure_project_checklist(project_id, template_slug)
            await self.engine.sync_project_state_to_db(
                project_id,
                {"wafChecklist": waf_update},
            )
