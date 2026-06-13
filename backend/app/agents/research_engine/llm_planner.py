"""LLM planner for Plan-Execute style due-diligence research."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple
import json
import re
import time

from langchain_openai import ChatOpenAI

from app.config import settings

from .prompts import ALLOWED_RESEARCH_CATEGORIES, ALLOWED_TOOL_HINTS, build_research_planner_prompt
from .state import ResearchTask, stable_id


def _json_from_text(text: str) -> Dict[str, Any]:
    value = (text or "").strip()
    if not value:
        return {}
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", value, flags=re.S)
    if match:
        try:
            parsed = json.loads(match.group(1))
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass
    start = value.find("{")
    end = value.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(value[start : end + 1])
        return parsed if isinstance(parsed, dict) else {}
    return {}


def _coerce_list(value: Any, limit: int = 8) -> List[str]:
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:limit]


def _normalize_task(raw: Dict[str, Any], enterprise_name: str, index: int) -> ResearchTask | None:
    question = str(raw.get("question") or "").strip()
    purpose = str(raw.get("purpose") or "").strip()
    category = str(raw.get("category") or "general").strip()
    if not question or not purpose:
        return None
    if category not in ALLOWED_RESEARCH_CATEGORIES:
        category = "general"

    required_evidence = _coerce_list(raw.get("required_evidence"), limit=10)
    tool_hints = [hint for hint in _coerce_list(raw.get("tool_hints"), limit=8) if hint in ALLOWED_TOOL_HINTS]
    success_criteria = _coerce_list(raw.get("success_criteria"), limit=6)
    if not required_evidence or not tool_hints:
        return None

    raw_id = str(raw.get("id") or "").strip()
    task_id = raw_id if raw_id.startswith("rt_") else stable_id("rt_llm", enterprise_name, question, index)
    try:
        priority = int(raw.get("priority") or index)
    except (TypeError, ValueError):
        priority = index

    return {
        "id": task_id,
        "question": question,
        "purpose": purpose,
        "category": category,
        "required_evidence": required_evidence,
        "priority": priority,
        "status": "pending",
        "tool_hints": tool_hints,
        "success_criteria": success_criteria,
        "planner_source": "llm",
    }


def _normalize_plan(parsed: Dict[str, Any], enterprise_name: str, max_tasks: int) -> Tuple[List[ResearchTask], Dict[str, Any]]:
    raw_tasks = parsed.get("tasks")
    if not isinstance(raw_tasks, list):
        raise ValueError("planner JSON missing tasks array")
    tasks: List[ResearchTask] = []
    seen_ids: set[str] = set()
    for index, raw_task in enumerate(raw_tasks[:max_tasks], start=1):
        if not isinstance(raw_task, dict):
            continue
        task = _normalize_task(raw_task, enterprise_name, index)
        if not task or task["id"] in seen_ids:
            continue
        tasks.append(task)
        seen_ids.add(task["id"])
    if not tasks:
        raise ValueError("planner returned no valid executable tasks")
    metadata = {
        "plan_summary": str(parsed.get("plan_summary") or "LLM Planner 已生成研究计划。"),
        "planning_assumptions": _coerce_list(parsed.get("planning_assumptions"), limit=8),
        "data_boundary": str(parsed.get("data_boundary") or "公开资料仅作为预尽调线索，正式授信前需权威来源复核。"),
        "task_count": len(tasks),
    }
    return tasks, metadata


def create_llm_research_plan(
    enterprise_name: str,
    objective: str,
    default_tasks: List[ResearchTask],
    max_tasks: int | None = None,
) -> Dict[str, Any]:
    """Return an LLM-generated research plan or a structured failure."""

    if not settings.ENABLE_LLM_RESEARCH_PLANNER:
        return {"success": False, "error": "disabled", "tasks": [], "metadata": {}}
    api_key = settings.RESEARCH_PLANNER_LLM_API_KEY or settings.LLM_API_KEY
    base_url = settings.RESEARCH_PLANNER_LLM_BASE_URL or settings.LLM_BASE_URL
    model = settings.RESEARCH_PLANNER_LLM_MODEL or settings.LLM_MODEL
    if not api_key:
        return {"success": False, "error": "Research planner LLM API key not configured", "tasks": [], "metadata": {}}

    max_tasks = max_tasks or settings.RESEARCH_PLANNER_MAX_TASKS
    started = time.time()
    try:
        prompt = build_research_planner_prompt(enterprise_name, objective, list(default_tasks), max_tasks)
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0,
            max_tokens=900,
            timeout=settings.RESEARCH_PLANNER_TIMEOUT_SECONDS,
            max_retries=0,
        )
        response = llm.invoke(prompt)
        content = str(getattr(response, "content", response))
        parsed = _json_from_text(content)
        tasks, metadata = _normalize_plan(parsed, enterprise_name, max_tasks)
        metadata["latency_seconds"] = round(time.time() - started, 2)
        metadata["model"] = model
        metadata["provider_base_url"] = base_url
        return {"success": True, "tasks": tasks, "metadata": metadata, "raw_preview": content[:800]}
    except Exception as exc:
        return {
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
            "tasks": [],
            "metadata": {"latency_seconds": round(time.time() - started, 2)},
        }
