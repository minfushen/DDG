"""Compatibility facade for the LangGraph-backed DeepResearch engine.

The public API intentionally stays stable for the FastAPI task runner and
frontend. The orchestration itself lives in ``graph_engine.py`` so future
checkpointing, native interrupt, and resume support can be added around graph
nodes without changing callers again.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional

from .graph_engine import execute_deep_research_plan_graph, prepare_deep_research_plan_graph, resume_deep_research_graph
from .state import ResearchState


async def prepare_deep_research_plan(
    enterprise_name: str,
    objective: str = "完整贷前尽调",
    max_iterations: int = 6,
    on_update: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    parsed_intent: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Build and review the research plan without executing external tools."""
    return await prepare_deep_research_plan_graph(
        enterprise_name, objective, max_iterations,
        on_update=on_update, parsed_intent=parsed_intent, task_id=task_id,
    )


async def execute_deep_research_plan(
    state: ResearchState,
    task_id: Optional[str] = None,
    on_update: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """Execute an approved research state and synthesize the final report."""
    return await execute_deep_research_plan_graph(state, task_id=task_id, on_update=on_update)


async def run_deep_research_due_diligence(
    enterprise_name: str,
    objective: str = "完整贷前尽调",
    max_iterations: int = 6,
    approved_state: ResearchState | None = None,
    parsed_intent: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
    on_update: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    if approved_state is not None:
        return await execute_deep_research_plan(approved_state, task_id=task_id, on_update=on_update)
    prepared = await prepare_deep_research_plan(
        enterprise_name, objective, max_iterations,
        parsed_intent=parsed_intent, task_id=task_id, on_update=on_update,
    )
    if not prepared.get("success"):
        return prepared
    return await execute_deep_research_plan(prepared["research_state"], task_id=task_id, on_update=on_update)


async def resume_deep_research(
    task_id: str,
    on_update: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """从 checkpoint 断点续跑（execute 中途崩溃后重启恢复）。"""
    return await resume_deep_research_graph(task_id, on_update=on_update)


def run_deep_research_due_diligence_sync(
    enterprise_name: str,
    objective: str = "完整贷前尽调",
    max_iterations: int = 6,
) -> Dict[str, Any]:
    return asyncio.run(run_deep_research_due_diligence(enterprise_name, objective, max_iterations))
