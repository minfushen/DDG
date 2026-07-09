"""Unified tool execution middleware.

Wraps the repeated trace-try-except-normalize pattern used in tool_router.py
into a single ``run_tool()`` call.  Every tool invocation gets:

1. Automatic timing via ``tool_trace``
2. Consistent error capture (Exception → error string + failed trace)
3. Evidence annotation on success
4. Raw output recording

Usage::

    from .tool_middleware import run_tool

    result = run_tool(
        tool_name="cninfo_webapi_financial",
        tool_fn=lambda: build_financial_summary("600519"),
        research_task_id=task_id,
        category="financial",
        query="600519 2024-12-31",
        query_summary="巨潮 WebAPI 结构化财务数据",
        evidence=evidence,
        raw_outputs=raw_outputs,
        errors=errors,
        tool_traces=tool_traces,
        extract_evidence=_my_extractor,
        result_key="cninfo_financial",
    )
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from app.memory import ShortTermMemory
from app.config import settings
from app.api import cache_store as _cache_store

from .tool_trace import annotate_evidence, finish_tool_trace, start_tool_trace

logger = logging.getLogger(__name__)


# Default TTLs per tool category (seconds). Search is short; structured data is longer.
_DEFAULT_TOOL_TTLS: Dict[str, int] = {
    "bocha": 3600,
    "searxng": 1800,
    "rag": 3600,
    "listed_company": 2592000,
    "structured_financial": 604800,
    "cninfo_announcements": 604800,
    "cninfo_webapi_financial": 604800,
    "cninfo_webapi_risk": 86400,
    "yuandian_legal_risk": 86400,
    "yuandian_business": 86400,
    "structured_business": 604800,
    "business_agent": 86400,
    "financial_agent": 86400,
    "industry_agent": 86400,
    "listed_company_public_info": 604800,
}


def _resolve_tool_ttl(tool_name: str) -> int:
    """Return TTL for *tool_name* from config or defaults."""
    if settings.TOOL_CACHE_TTL_BY_TOOL:
        try:
            overrides = json.loads(settings.TOOL_CACHE_TTL_BY_TOOL)
            if tool_name in overrides:
                return int(overrides[tool_name])
        except (json.JSONDecodeError, ValueError, TypeError):
            logger.warning("Invalid TOOL_CACHE_TTL_BY_TOOL JSON, using defaults")
    return _DEFAULT_TOOL_TTLS.get(tool_name, settings.TOOL_CACHE_TTL_SECONDS)


def _tool_cache_args(
    tool_name: str,
    query: str,
    category: str,
    query_summary: str,
) -> Dict[str, Any]:
    """Arguments that define the cache identity of a tool call.

    Runtime identifiers such as ``research_task_id`` are intentionally excluded
    so that identical queries across different tasks share cache entries.
    """
    return {
        "tool_name": tool_name,
        "query": query,
        "category": category,
        "query_summary": query_summary,
    }


def run_tool(
    *,
    tool_name: str,
    tool_fn: Callable[[], Any],
    research_task_id: str,
    category: str,
    query: str,
    query_summary: str,
    evidence: List[Dict[str, Any]],
    raw_outputs: Dict[str, Any],
    errors: List[str],
    tool_traces: List[Dict[str, Any]],
    extract_evidence: Optional[Callable[[Any], None]] = None,
    result_key: Optional[str] = None,
    session_id: Optional[str] = None,
) -> Any:
    """Execute *tool_fn* with unified tracing, error handling and evidence collection.

    Parameters
    ----------
    tool_name:
        Internal name shown in traces (e.g. ``"cninfo_webapi_financial"``).
    tool_fn:
        Zero-argument callable that performs the actual work and returns a
        result dict (or ``None``).
    research_task_id:
        Current research task identifier.
    category:
        Task category (``"financial"``, ``"legal"``, ``"business"``, …).
    query / query_summary:
        Human-readable description of what this tool call does.
    evidence / raw_outputs / errors / tool_traces:
        Mutable containers from the caller — items are **appended in-place**.
    extract_evidence:
        Optional callback ``fn(result)`` that inspects the tool result and
        appends normalised evidence items to *evidence*.  Called only on
        success (result is not ``None``).
    result_key:
        If provided, ``raw_outputs[result_key]`` is populated with a summary
        dict (``success``, ``error``, ``result_count``, ``result_keys``).
    session_id:
        Optional session identifier. If not provided, ``research_task_id``
        is used.  Used for short-term memory tracking.

    Returns
    -------
    Any
        The raw result from *tool_fn* on success, or ``None`` on failure / skip.
    """
    trace = start_tool_trace(
        research_task_id=research_task_id,
        internal_tool_name=tool_name,
        query=query,
        query_summary=query_summary,
        category=category,
    )
    before_count = len(evidence)

    # --- check tool result cache ---
    cache_key: Optional[str] = None
    cached_result: Any = None
    cache_hit = False
    if settings.ENABLE_TOOL_CACHE:
        cache_key = _cache_store.tool_cache_key(
            tool_name, _tool_cache_args(tool_name, query, category, query_summary)
        )
        cached = _cache_store.get_tool_cache(cache_key)
        if cached is not None:
            cached_result = cached["result"]
            cache_hit = True

    if cache_hit:
        result = cached_result
        logger.debug("Tool cache hit: %s", tool_name)
    else:
        try:
            result = tool_fn()
        except Exception as exc:
            err_msg = f"{tool_name}失败：{type(exc).__name__}: {exc}"
            logger.warning(err_msg)
            errors.append(err_msg)
            tool_traces.append(finish_tool_trace(trace, status="failed", error=err_msg))
            # --- short-term memory: record failure ---
            if settings.ENABLE_SHORT_TERM_MEMORY:
                stm = ShortTermMemory(
                    session_id=session_id or research_task_id,
                    task_id=research_task_id,
                )
                stm.add_tool_result(
                    tool_name=tool_name,
                    result_summary=err_msg,
                    success=False,
                    cache_hit=False,
                    metadata={"query": query, "category": category},
                )
            return None

        # --- store successful result in cache ---
        if settings.ENABLE_TOOL_CACHE and cache_key is not None and result is not None:
            try:
                _cache_store.set_tool_cache(
                    cache_key,
                    tool_name,
                    _tool_cache_args(tool_name, query, category, query_summary),
                    result,
                    _resolve_tool_ttl(tool_name),
                )
            except Exception as exc:
                logger.warning("Failed to write tool cache for %s: %s", tool_name, exc)

    # --- record raw output summary ---
    if result_key and result is not None:
        raw_outputs[result_key] = {
            "success": True,
            "result_keys": list(result.keys()) if isinstance(result, dict) else None,
        }

    # --- skip if tool returned nothing useful ---
    if result is None:
        tool_traces.append(finish_tool_trace(trace, status="empty", result_count=0))
        return None

    # --- extract evidence ---
    if extract_evidence is not None:
        try:
            extract_evidence(result)
        except Exception as exc:
            err_msg = f"{tool_name}证据提取失败：{type(exc).__name__}: {exc}"
            logger.warning(err_msg)
            errors.append(err_msg)

    new_evidence = evidence[before_count:]
    annotate_evidence(new_evidence, trace)
    tool_traces.append(
        finish_tool_trace(
            trace,
            status="cache_hit" if cache_hit else "success",
            result_count=len(new_evidence),
        )
    )

    # --- short-term memory: record tool invocation ---
    if settings.ENABLE_SHORT_TERM_MEMORY:
        stm = ShortTermMemory(
            session_id=session_id or research_task_id,
            task_id=research_task_id,
        )
        result_summary = f"{query_summary}"
        if result is not None:
            if isinstance(result, dict):
                result_summary += f" → keys={list(result.keys())}"
            elif isinstance(result, list):
                result_summary += f" → count={len(result)}"
        stm.add_tool_result(
            tool_name=tool_name,
            result_summary=result_summary,
            success=result is not None,
            cache_hit=cache_hit,
            metadata={"query": query, "category": category},
        )

    return result
