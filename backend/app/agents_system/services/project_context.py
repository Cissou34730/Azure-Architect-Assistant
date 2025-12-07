"""
Project context services for agent system.
Provides read/write access to ProjectState from database.
"""

import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

from ...models import ProjectState, Project

logger = logging.getLogger(__name__)


async def read_project_state(project_id: str, db: AsyncSession) -> Optional[Dict[str, Any]]:
    """
    Read ProjectState from database.
    
    Args:
        project_id: Project ID
        db: Database session
        
    Returns:
        ProjectState dictionary or None if not found
    """
    result = await db.execute(
        select(ProjectState).where(ProjectState.project_id == project_id)
    )
    state_record = result.scalar_one_or_none()
    
    if not state_record:
        logger.warning(f"No ProjectState found for project {project_id}")
        return None
    
    state_data = json.loads(state_record.state)
    state_data["projectId"] = project_id
    state_data["lastUpdated"] = state_record.updated_at
    
    logger.debug(f"Loaded ProjectState for project {project_id}")
    return state_data


async def update_project_state(
    project_id: str,
    updates: Dict[str, Any],
    db: AsyncSession,
    merge: bool = True
) -> Dict[str, Any]:
    """
    Update ProjectState in database.
    
    Args:
        project_id: Project ID
        updates: Dictionary with state updates
        db: Database session
        merge: If True, merge with existing state; if False, replace entirely
        
    Returns:
        Updated ProjectState dictionary
        
    Raises:
        ValueError: If project or state not found
    """
    # Verify project exists
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        raise ValueError(f"Project {project_id} not found")
    
    # Get current state
    result = await db.execute(
        select(ProjectState).where(ProjectState.project_id == project_id)
    )
    state_record = result.scalar_one_or_none()
    
    if not state_record:
        raise ValueError(f"ProjectState not initialized for project {project_id}")
    
    # Merge or replace
    if merge:
        current_state = json.loads(state_record.state)
        # Deep merge - update nested dicts
        updated_state = _deep_merge(current_state, updates)
    else:
        updated_state = updates
    
    # Update database record
    state_record.state = json.dumps(updated_state)
    state_record.updated_at = datetime.utcnow().isoformat()
    
    await db.commit()
    
    # Return with metadata
    updated_state["projectId"] = project_id
    updated_state["lastUpdated"] = state_record.updated_at
    
    logger.info(f"Updated ProjectState for project {project_id}")
    return updated_state


def _deep_merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.
    Updates values are merged into base, nested dicts are recursively merged.
    """
    result = base.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


async def get_project_context_summary(project_id: str, db: AsyncSession) -> str:
    """
    Get formatted summary of project context for agent prompts.
    
    Args:
        project_id: Project ID
        db: Database session
        
    Returns:
        Formatted string with project context
    """
    # Get project
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    
    if not project:
        return f"Project {project_id} not found"
    
    # Get state
    state = await read_project_state(project_id, db)
    
    if not state:
        return f"Project: {project.name}\nNo architecture state available yet."
    
    # Format summary
    summary_parts = [
        f"PROJECT: {project.name}",
        f"Created: {project.created_at}",
        ""
    ]
    
    # Context
    if "context" in state:
        ctx = state["context"]
        summary_parts.append("CONTEXT:")
        if ctx.get("summary"):
            summary_parts.append(f"  Summary: {ctx['summary']}")
        if ctx.get("objectives"):
            summary_parts.append(f"  Objectives: {', '.join(ctx['objectives'])}")
        if ctx.get("targetUsers"):
            summary_parts.append(f"  Target Users: {ctx['targetUsers']}")
        if ctx.get("scenarioType"):
            summary_parts.append(f"  Scenario: {ctx['scenarioType']}")
        summary_parts.append("")
    
    # NFRs
    if "nfrs" in state:
        nfrs = state["nfrs"]
        summary_parts.append("NON-FUNCTIONAL REQUIREMENTS:")
        if nfrs.get("availability"):
            summary_parts.append(f"  Availability: {nfrs['availability']}")
        if nfrs.get("security"):
            summary_parts.append(f"  Security: {nfrs['security']}")
        if nfrs.get("performance"):
            summary_parts.append(f"  Performance: {nfrs['performance']}")
        if nfrs.get("costConstraints"):
            summary_parts.append(f"  Cost: {nfrs['costConstraints']}")
        summary_parts.append("")
    
    # Application Structure
    if "applicationStructure" in state:
        app_struct = state["applicationStructure"]
        summary_parts.append("APPLICATION STRUCTURE:")
        if app_struct.get("components"):
            summary_parts.append(f"  Components: {len(app_struct['components'])} defined")
            for comp in app_struct["components"][:3]:  # Show first 3
                summary_parts.append(f"    - {comp.get('name', 'Unnamed')}: {comp.get('description', '')[:50]}")
        if app_struct.get("integrations"):
            summary_parts.append(f"  Integrations: {', '.join(app_struct['integrations'][:5])}")
        summary_parts.append("")
    
    # Open Questions
    if "openQuestions" in state and state["openQuestions"]:
        summary_parts.append("OPEN QUESTIONS:")
        for q in state["openQuestions"][:5]:
            summary_parts.append(f"  - {q}")
    
    return "\n".join(summary_parts)
