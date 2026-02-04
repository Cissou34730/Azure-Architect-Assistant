"""
Processes agent outputs to extract and normalize WAF checklist evaluations.
"""

import json
import logging
from typing import Any

from app.agents_system.checklists.engine import ChecklistEngine

logger = logging.getLogger(__name__)

def find_json_blocks(text: str, prefix: str) -> list[dict[str, Any]]:
    """
    Find JSON blocks starting with a prefix, handling nested brackets.
    """
    results = []
    start_idx = 0
    while True:
        idx = text.find(prefix, start_idx)
        if idx == -1:
            break

        # Find the first '{' after the prefix
        json_start = text.find("{", idx + len(prefix))
        if json_start == -1:
            start_idx = idx + len(prefix)
            continue

        # Extract balanced bracket block
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
            except Exception as e:
                logger.error(f"Failed to parse JSON block: {e}")
            start_idx = json_end
        else:
            start_idx = json_start + 1

    return results

class WafResultProcessor:
    """
    Parses agent output and updates normalized WAF tables.
    """

    def __init__(self, engine: ChecklistEngine) -> None:
        self.engine = engine

    async def process_orchestrator_result(self, project_id: str, result: dict[str, Any]) -> None:
        """
        Scan orchestrator result for WAF updates and apply them to the DB.
        """
        output = result.get("output", "")
        if not output:
            return

        update_blocks = find_json_blocks(output, "AAA_STATE_UPDATE:")
        for update_data in update_blocks:
            await self._process_state_update(project_id, update_data)

    async def _process_state_update(self, project_id: str, update_data: dict[str, Any]) -> None:
        """
        Process a single AAA_STATE_UPDATE payload.
        """
        # Look for wafChecklist updates
        waf_update = update_data.get("wafChecklist")
        if not waf_update:
            return

        items = waf_update.get("items", [])
        if not items:
            return

        template_slug = waf_update.get("slug", "waf-2024") # Fallback to default

        # Ensure checklist is instantiated
        await self.engine.instantiate_checklist(project_id, template_slug)

        for item_data in items:
            item_id = item_data.get("id")
            if not item_id:
                continue

            evals = item_data.get("evaluations", [])
            if not evals:
                continue

            # Take the latest evaluation
            latest_eval = evals[-1]
            status = latest_eval.get("status")
            if not status:
                continue

            # Map status if needed (covered/partial/notCovered to engine enum)
            # engine.update_item_evaluation handles mapping via normalize_helpers if we want,
            # but let's do it here or make engine handle it.

            # For simplicity, we assume the engine knows how to map or we provide mapped status
            from app.services.normalize_helpers import map_legacy_status
            mapped_status = map_legacy_status(status)

            await self.engine.update_item_evaluation(
                item_id=item_id,
                project_id=project_id,
                status=mapped_status,
                score=1.0 if mapped_status == "fulfilled" else 0.5 if mapped_status == "partially_fulfilled" else 0.0,
                evidence={
                    "description": latest_eval.get("evidence", ""),
                    "related_findings": latest_eval.get("relatedFindingIds", []),
                    "citations": latest_eval.get("sourceCitations", [])
                },
                evaluator="agent-orchestrator"
            )

        # Re-calculate progress
        # We need the checklist ID. Let's fetch it.
        checklist = await self.engine.get_project_checklist(project_id, template_slug)
        if checklist:
            await self.engine.calculate_progress(checklist.id)
            logger.info(f"Updated WAF progress for project {project_id}: {checklist.completion_percentage}%")
