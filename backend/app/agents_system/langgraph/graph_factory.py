"""Graph factory for the single-path LangGraph project chat runtime."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.config.app_settings import AppSettings, get_app_settings

from .nodes.agent import run_agent_node
from .nodes.architecture_planner import architecture_planner_node
from .nodes.clarify import execute_clarification_planner_node
from .nodes.context import build_context_summary_node, load_project_state_node
from .nodes.cost_estimator import execute_cost_stage_worker_node
from .nodes.export import execute_export_stage_worker_node
from .nodes.extract_requirements import execute_extract_requirements_node
from .nodes.iac_generator import execute_iac_stage_worker_node
from .nodes.manage_adr import execute_manage_adr_stage_worker_node
from .nodes.persist import apply_state_updates_node, persist_messages_node
from .nodes.postprocess import postprocess_node
from .nodes.research import build_research_plan_node, execute_research_worker_node
from .nodes.routing import (
    prepare_architecture_planner_handoff,
    should_route_to_cost_estimator,
    should_route_to_iac_generator,
)
from .nodes.stage_routing import (
    ProjectStage,
    build_retry_prompt,
    check_for_retry,
    classify_next_stage,
    propose_next_step,
)
from .nodes.validate import execute_validate_stage_worker_node
from .state import GraphState

logger = logging.getLogger(__name__)


@asynccontextmanager
async def build_project_chat_graph(
    db: AsyncSession,
    response_message_id: str = '',
) -> AsyncIterator[Any]:
    """Build the project chat graph with an optional SQLite-backed checkpointer."""
    workflow = _build_project_chat_workflow(db, response_message_id)
    settings = get_app_settings()

    if not settings.aaa_thread_memory_enabled:
        yield workflow.compile(checkpointer=None)
        return

    async with _build_thread_checkpointer(settings) as checkpointer:
        yield workflow.compile(checkpointer=checkpointer)


@asynccontextmanager
async def _build_thread_checkpointer(settings: AppSettings) -> AsyncIterator[AsyncSqliteSaver]:
    """Open the SQLite checkpointer used for thread-scoped LangGraph memory."""
    database_path = _thread_checkpointer_database_path(settings)
    async with AsyncSqliteSaver.from_conn_string(str(database_path)) as checkpointer:
        yield checkpointer


def _thread_checkpointer_database_path(settings: AppSettings) -> Path:
    """Resolve the SQLite file used for persistent thread checkpoints."""
    return settings.data_root / 'checkpoints.db'


def _build_project_chat_workflow(
    db: AsyncSession,
    response_message_id: str,
) -> StateGraph:
    """Build the uncompiled project chat workflow."""
    workflow = StateGraph(GraphState)

    # Core nodes (all phases)
    workflow.add_node('load_state', _wrap_load_state(db))
    workflow.add_node('build_summary', _wrap_build_summary(db))
    workflow.add_node('classify_stage', classify_next_stage)
    workflow.add_node('clarify_stage_worker', _wrap_clarify(db))
    workflow.add_node('export_stage_worker', execute_export_stage_worker_node)
    workflow.add_node('extract_requirements', _wrap_extract_requirements(db))
    workflow.add_node('iac_stage_worker', execute_iac_stage_worker_node)
    workflow.add_node('build_research', build_research_plan_node)
    workflow.add_node('research_worker', execute_research_worker_node)
    workflow.add_node('build_mindmap_guidance', _pass_through_mindmap_guidance)
    workflow.add_node('manage_adr_stage_worker', _wrap_manage_adr(db))
    workflow.add_node('validate_stage_worker', execute_validate_stage_worker_node)
    workflow.add_node('prepare_architecture_handoff', prepare_architecture_planner_handoff)
    workflow.add_node('architecture_planner', architecture_planner_node)
    workflow.add_node('cost_stage_worker', execute_cost_stage_worker_node)
    workflow.add_node('run_agent', _wrap_run_agent(db))
    workflow.add_node('persist_messages', _wrap_persist_messages(db))
    workflow.add_node('postprocess', _wrap_postprocess(response_message_id))
    workflow.add_node('apply_updates', _wrap_apply_updates(db))
    workflow.add_node('retry_prompt', build_retry_prompt)
    workflow.add_node('propose_next_step', propose_next_step)

    _build_workflow_edges(workflow)
    return workflow


def _wrap_load_state(db: AsyncSession):
    async def load_state(state: GraphState) -> dict:
        return await load_project_state_node(state, db)

    return load_state


def _wrap_build_summary(db: AsyncSession):
    async def build_summary(state: GraphState) -> dict:
        return await build_context_summary_node(state, db)

    return build_summary


def _wrap_postprocess(response_message_id: str):
    async def postprocess(state: GraphState) -> dict:
        return await postprocess_node(state, response_message_id)

    return postprocess


def _wrap_extract_requirements(db: AsyncSession):
    async def extract_requirements(state: GraphState, config: RunnableConfig) -> dict:
        return await execute_extract_requirements_node(state, db, config=config)

    return extract_requirements


def _wrap_clarify(db: AsyncSession):
    async def clarify(state: GraphState, config: RunnableConfig) -> dict:
        return await execute_clarification_planner_node(state, db, config=config)

    return clarify


def _wrap_persist_messages(db: AsyncSession):
    async def persist_messages(state: GraphState) -> dict:
        return await persist_messages_node(state, db)

    return persist_messages


def _wrap_manage_adr(db: AsyncSession):
    async def manage_adr(state: GraphState) -> dict:
        return await execute_manage_adr_stage_worker_node(state, db)

    return manage_adr


def _wrap_apply_updates(db: AsyncSession):
    async def apply_updates(state: GraphState) -> dict:
        return await apply_state_updates_node(state, db)

    return apply_updates


def _wrap_run_agent(db: AsyncSession):
    async def run_agent(state: GraphState, config: RunnableConfig) -> dict:
        return await run_agent_node(state, config=config, db=db)

    return run_agent


def _pass_through_mindmap_guidance(state: GraphState) -> dict:
    """Dedicated step to make mindmap guidance explicit in graph flow."""
    return {
        'mindmap_guidance': state.get('mindmap_guidance'),
    }


def _build_workflow_edges(workflow: StateGraph):
    """Define edges and conditional paths for the graph."""

    def route_after_summary(
        state: GraphState,
    ) -> Literal[
        'extract_requirements', 'clarify_stage_worker', 'export_stage_worker', 'build_research'
    ]:
        if state.get('next_stage') == ProjectStage.EXTRACT_REQUIREMENTS.value:
            return 'extract_requirements'
        if state.get('next_stage') == ProjectStage.CLARIFY.value:
            return 'clarify_stage_worker'
        if state.get('next_stage') == ProjectStage.EXPORT.value:
            return 'export_stage_worker'
        return 'build_research'

    def route_after_research_plan(
        state: GraphState,
    ) -> Literal['research_worker', 'build_mindmap_guidance']:
        if state.get('next_stage') == ProjectStage.PROPOSE_CANDIDATE.value and state.get(
            'research_plan'
        ):
            return 'research_worker'
        return 'build_mindmap_guidance'

    def route_after_research(
        state: GraphState,
    ) -> Literal[
        'cost_stage_worker',
        'iac_stage_worker',
        'architecture_planner',
        'manage_adr_stage_worker',
        'validate_stage_worker',
        'run_agent',
    ]:
        if state.get('next_stage') == ProjectStage.PRICING.value:
            return 'cost_stage_worker'
        if should_route_to_cost_estimator(state):
            return 'cost_stage_worker'
        if state.get('next_stage') == ProjectStage.IAC.value:
            return 'iac_stage_worker'
        if should_route_to_iac_generator(state):
            return 'iac_stage_worker'
        if state.get('next_stage') == ProjectStage.PROPOSE_CANDIDATE.value:
            return 'architecture_planner'
        if state.get('next_stage') == ProjectStage.MANAGE_ADR.value:
            return 'manage_adr_stage_worker'
        if state.get('next_stage') == ProjectStage.VALIDATE.value:
            return 'validate_stage_worker'
        return 'run_agent'

    def route_after_persist(state: GraphState) -> Literal['end', 'postprocess']:
        if state.get('handled_by_stage_worker'):
            return 'end'
        return 'postprocess'

    workflow.set_entry_point('load_state')
    workflow.add_edge('load_state', 'classify_stage')
    workflow.add_edge('classify_stage', 'build_summary')
    workflow.add_conditional_edges(
        'build_summary',
        route_after_summary,
        {
            'extract_requirements': 'extract_requirements',
            'clarify_stage_worker': 'clarify_stage_worker',
            'export_stage_worker': 'export_stage_worker',
            'build_research': 'build_research',
        },
    )
    workflow.add_edge('extract_requirements', 'persist_messages')
    workflow.add_edge('clarify_stage_worker', 'persist_messages')
    workflow.add_edge('export_stage_worker', 'persist_messages')
    workflow.add_conditional_edges(
        'build_research',
        route_after_research_plan,
        {
            'research_worker': 'research_worker',
            'build_mindmap_guidance': 'build_mindmap_guidance',
        },
    )
    research_routes = {
        'architecture_planner': 'prepare_architecture_handoff',
        'cost_stage_worker': 'cost_stage_worker',
        'iac_stage_worker': 'iac_stage_worker',
        'manage_adr_stage_worker': 'manage_adr_stage_worker',
        'validate_stage_worker': 'validate_stage_worker',
        'run_agent': 'run_agent',
    }

    workflow.add_edge('research_worker', 'build_mindmap_guidance')
    workflow.add_conditional_edges('build_mindmap_guidance', route_after_research, research_routes)
    workflow.add_edge('prepare_architecture_handoff', 'architecture_planner')
    workflow.add_edge('architecture_planner', 'persist_messages')
    workflow.add_edge('cost_stage_worker', 'persist_messages')
    workflow.add_edge('iac_stage_worker', 'persist_messages')
    workflow.add_edge('manage_adr_stage_worker', 'persist_messages')
    workflow.add_edge('validate_stage_worker', 'persist_messages')
    workflow.add_edge('run_agent', 'persist_messages')
    workflow.add_conditional_edges(
        'persist_messages',
        route_after_persist,
        {'end': END, 'postprocess': 'postprocess'},
    )
    workflow.add_conditional_edges(
        'postprocess',
        check_for_retry,
        {'retry': 'retry_prompt', 'continue': 'apply_updates'},
    )
    workflow.add_edge('retry_prompt', END)
    workflow.add_edge('apply_updates', 'propose_next_step')
    workflow.add_edge('propose_next_step', END)
