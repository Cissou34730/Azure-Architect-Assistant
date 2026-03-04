"""Diagram business-logic helpers extracted from project_router.

Functions here handle:
* building a description from project state for the diagram generator,
* generating an initial C4-Context diagram, and
* persisting the resulting reference back into ProjectState.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ProjectState
from app.models.diagram import Diagram, DiagramSet, DiagramType
from app.services.diagram.database import get_diagram_session
from app.services.diagram.diagram_generator import DiagramGenerator
from app.services.diagram.llm_client import DiagramLLMClient

logger = logging.getLogger(__name__)


def build_diagram_input_description(state: dict[str, Any]) -> str:
    context_raw = state.get("context")
    context = context_raw if isinstance(context_raw, dict) else {}
    summary = (context.get("summary") or "").strip()

    requirements_raw = state.get("requirements")
    requirements = requirements_raw if isinstance(requirements_raw, list) else []

    parts: list[str] = []
    if summary:
        parts.append(f"Project summary: {summary}")

    for category in ["business", "functional", "nfr"]:
        lines = _get_requirement_lines_by_category(requirements, category)
        if lines:
            title = f"{category.capitalize()} requirements:"
            parts.append(f"{title}\n" + "\n".join(lines))

    # Fall back to a safe minimal description to satisfy diagram generator input constraints.
    if not parts:
        parts.append(
            "Generate a C4 Context diagram for the system described by the project documents."
        )

    return "\n\n".join(parts)


def _get_requirement_lines_by_category(
    requirements: list[Any], category: str
) -> list[str]:
    """Helper to extract requirement lines for a specific category."""
    lines: list[str] = []
    for r in requirements:
        if (
            isinstance(r, dict)
            and (r.get("category") or "").strip().lower() == category
        ):
            text = (r.get("text") or "").strip()
            if text:
                lines.append(f"- {text}")
    return lines


async def ensure_initial_c4_context_diagram(
    project_id: str, state: dict[str, Any]
) -> dict[str, Any] | None:
    """Generate a C4 Context diagram and return a reference payload.

    Uses the diagram DB + DiagramGenerator (same components as /api/diagram-sets).
    """

    description = build_diagram_input_description(state)
    llm_client = DiagramLLMClient()
    generator = DiagramGenerator(llm_client)

    async for session in get_diagram_session():
        diagram_set = DiagramSet(
            adr_id=None,
            input_description=description,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        session.add(diagram_set)
        await session.flush()

        result = await generator.generate_c4_context(description=description)
        if not result.success or not result.source_code:
            raise RuntimeError(
                f"C4 context diagram generation failed after {result.attempts} attempts: {result.error}"
            )

        diagram = Diagram(
            diagram_set_id=diagram_set.id,
            diagram_type=DiagramType.C4_CONTEXT.value,
            source_code=result.source_code,
            rendered_svg=None,
            rendered_png=None,
            version="1.0.0",
            previous_version_id=None,
            created_at=datetime.now(timezone.utc),
        )
        session.add(diagram)
        await session.flush()

        # get_diagram_session() will commit for us after yielding.
        return {
            "id": diagram.id,
            "type": "c4_context",
            "source": diagram.source_code,
            "version": diagram.version,
            "diagramSetId": diagram_set.id,
            "url": f"/api/diagram-sets/{diagram_set.id}",
            "updatedAt": diagram.created_at.isoformat(),
        }

    return None


async def append_diagram_reference_to_project_state(
    project_id: str,
    state: dict[str, Any],
    diagram_ref: dict[str, Any],
    db: AsyncSession,
) -> dict[str, Any]:
    """Persist a diagram reference into ProjectState.state and return updated state."""

    result = await db.execute(
        select(ProjectState).where(ProjectState.project_id == project_id)
    )
    state_record = result.scalar_one_or_none()
    if not state_record:
        # Should not happen (analyze-docs just created it), but be defensive.
        state_record = ProjectState(
            project_id=project_id,
            state=json.dumps(state),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        db.add(state_record)
        await db.flush()

    persisted = json.loads(state_record.state)
    diagrams = persisted.get("diagrams")
    if not isinstance(diagrams, list):
        diagrams = []

    # Do not duplicate if already present
    if not any(isinstance(d, dict) and d.get("id") == diagram_ref.get("id") for d in diagrams):
        diagrams.append(diagram_ref)

    persisted["diagrams"] = diagrams
    state_record.state = json.dumps(persisted)
    state_record.updated_at = datetime.now(timezone.utc).isoformat()
    await db.commit()

    # Return merged view
    updated = dict(state)
    updated["diagrams"] = diagrams
    return updated
