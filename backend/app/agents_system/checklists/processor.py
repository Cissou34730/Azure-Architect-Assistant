"""Processes agent outputs to extract and normalize WAF checklist evaluations."""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents_system.checklists.engine import ChecklistEngine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Text-parsing utilities
# ---------------------------------------------------------------------------


def find_json_blocks(text: str, prefix: str) -> list[dict[str, Any]]:
    """Find JSON blocks starting with *prefix*, handling nested brackets."""
    results: list[dict[str, Any]] = []
    start_idx = 0
    while True:
        idx = text.find(prefix, start_idx)
        if idx == -1:
            break

        json_start = text.find("{", idx + len(prefix))
        if json_start == -1:
            start_idx = idx + len(prefix)
            continue

        bracket_count = 0
        json_end = -1
        for i in range(json_start, len(text)):
            if text[i] == "{":
                bracket_count += 1
            elif text[i] == "}":
                bracket_count -= 1
                if bracket_count == 0:
                    json_end = i + 1
                    break

        if json_end != -1:
            try:
                block_str = text[json_start:json_end]
                results.append(json.loads(block_str))
            except (json.JSONDecodeError, ValueError):
                logger.warning("Skipping unparseable JSON block at offset %d", json_start)
            start_idx = json_end
        else:
            start_idx = json_start + 1

    return results


# ---------------------------------------------------------------------------
# Processor
# ---------------------------------------------------------------------------


class WafResultProcessor:
    """Parse agent output and apply WAF evaluation updates to normalized tables."""

    def __init__(self, engine: ChecklistEngine) -> None:
        self.engine = engine

    async def process_orchestrator_result(
        self, project_id: str, result: dict[str, Any]
    ) -> None:
        """Scan orchestrator result for ``AAA_STATE_UPDATE`` blocks and persist them."""
        output = result.get("output", "")
        if not output:
            return

        update_blocks = find_json_blocks(output, "AAA_STATE_UPDATE:")
        for update_data in update_blocks:
            await self._process_state_update(project_id, update_data)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _process_state_update(
        self, project_id: str, update_data: dict[str, Any]
    ) -> None:
        """Process a single ``AAA_STATE_UPDATE`` payload."""
        waf_update = update_data.get("wafChecklist")
        if not isinstance(waf_update, dict):
            return

        items: list[dict[str, Any]] = waf_update.get("items", [])
        if not items:
            return

        template_slug = str(
            waf_update.get("slug") or self.engine.default_template_slug()
        )

        # Ensure the checklist exists so items can be attached.
        await self.engine.ensure_project_checklist(project_id, template_slug)

        # Delegate the complete payload to the engine's sync path which
        # already handles item creation, dedup, and evaluation mapping.
        await self.engine.process_agent_result(
            project_id,
            {"AAA_STATE_UPDATE": {"wafChecklist": {template_slug: waf_update}}},
        )

        logger.info("Processed WAF state update for project %s (template=%s)", project_id, template_slug)
