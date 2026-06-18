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
        "chapter_id": str(raw.get("chapter_id") or category).strip(),
        "chapter_title": str(raw.get("chapter_title") or "").strip(),
        "fallback_language": str(raw.get("fallback_language") or "").strip(),
        "credit_action_when_missing": str(raw.get("credit_action_when_missing") or "").strip(),
        "planner_source": "llm",
    }


def _normalize_plan(parsed: Dict[str, Any], enterprise_name: str, max_tasks: int) -> Tuple[List[ResearchTask], Dict[str, Any]]:
    raw_tasks: Any = None
    is_list_input = isinstance(parsed, list)
    if is_list_input:
        # 模型偶尔直接返回任务数组
        raw_tasks = parsed
    elif isinstance(parsed, dict):
        raw_tasks = parsed.get("tasks")
        if isinstance(raw_tasks, dict):
            # 模型有时把 tasks 包装成对象，尝试取内部数组
            raw_tasks = raw_tasks.get("tasks") or raw_tasks.get("items") or raw_tasks.get("list")
    if not isinstance(raw_tasks, list):
        return [], {"normalize_error": "planner JSON missing tasks array", "raw_keys": list(parsed.keys()) if isinstance(parsed, dict) else type(parsed).__name__}
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
    parsed_dict = parsed if isinstance(parsed, dict) else {}
    metadata = {
        "plan_summary": str(parsed_dict.get("plan_summary") or "LLM Planner 已生成研究计划。"),
        "planning_assumptions": _coerce_list(parsed_dict.get("planning_assumptions"), limit=8),
        "data_boundary": str(parsed_dict.get("data_boundary") or "公开资料仅作为预尽调线索，正式授信前需权威来源复核。"),
        "task_count": len(tasks),
    }
    return tasks, metadata


def create_llm_research_plan(
    enterprise_name: str,
    objective: str,
    default_tasks: List[ResearchTask],
    max_tasks: int | None = None,
    thought_loop_context: str = "",
    skill_context: str = "",
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
        prompt = build_research_planner_prompt(
            enterprise_name,
            objective,
            list(default_tasks),
            max_tasks,
            thought_loop_context=thought_loop_context,
            skill_context=skill_context,
        )
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=base_url,
            temperature=0,
            max_tokens=8192,
            timeout=settings.RESEARCH_PLANNER_TIMEOUT_SECONDS,
            max_retries=0,
            model_kwargs={"response_format": {"type": "json_object"}},
        )
        response = llm.invoke(prompt)
        content = str(getattr(response, "content", response))
        parsed = _json_from_text(content)
        tasks, metadata = _normalize_plan(parsed, enterprise_name, max_tasks)
        if not tasks:
            normalize_error = metadata.pop("normalize_error", "planner returned no valid executable tasks")
            return {
                "success": False,
                "error": normalize_error,
                "tasks": [],
                "metadata": {**metadata, "latency_seconds": round(time.time() - started, 2), "raw_preview": content[:800]},
            }
        metadata["latency_seconds"] = round(time.time() - started, 2)
        metadata["model"] = model
        metadata["provider_base_url"] = base_url
        metadata["used_thought_loop_context"] = bool(thought_loop_context)
        metadata["used_skill_context"] = bool(skill_context)
        return {"success": True, "tasks": tasks, "metadata": metadata, "raw_preview": content[:800]}
    except Exception as exc:
        return {
            "success": False,
            "error": f"{type(exc).__name__}: {exc}",
            "tasks": [],
            "metadata": {"latency_seconds": round(time.time() - started, 2)},
        }
