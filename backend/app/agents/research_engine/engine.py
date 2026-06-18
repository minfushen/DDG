"""Compatibility facade for the LangGraph-backed DeepResearch engine.

The public API intentionally stays stable for the FastAPI task runner and
frontend. The orchestration itself lives in ``graph_engine.py`` so future
checkpointing, native interrupt, and resume support can be added around graph
nodes without changing callers again.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, Optional

from .graph_engine import execute_deep_research_plan_graph, prepare_deep_research_plan_graph
from .state import ResearchState


async def prepare_deep_research_plan(
    enterprise_name: str,
    objective: str = "完整贷前尽调",
    max_iterations: int = 6,
    on_update: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """Build and review the research plan without executing external tools."""
    return await prepare_deep_research_plan_graph(enterprise_name, objective, max_iterations, on_update=on_update)


async def execute_deep_research_plan(state: ResearchState) -> Dict[str, Any]:
    """Execute an approved research state and synthesize the final report."""
    return await execute_deep_research_plan_graph(state)


async def run_deep_research_due_diligence(
    enterprise_name: str,
    objective: str = "完整贷前尽调",
    max_iterations: int = 6,
    approved_state: ResearchState | None = None,
) -> Dict[str, Any]:
    if approved_state is not None:
        return await execute_deep_research_plan(approved_state)
    prepared = await prepare_deep_research_plan(enterprise_name, objective, max_iterations)
    if not prepared.get("success"):
        return prepared
    return await execute_deep_research_plan(prepared["research_state"])


def run_deep_research_due_diligence_sync(
    enterprise_name: str,
    objective: str = "完整贷前尽调",
    max_iterations: int = 6,
) -> Dict[str, Any]:
    return asyncio.run(run_deep_research_due_diligence(enterprise_name, objective, max_iterations))
