"""Rule-first DeepResearch due-diligence engine.

This stage intentionally avoids replacing the existing full due-diligence
pipeline. It produces a research_report JSON that can later feed the report
builder or a Sequential Thinking MCP loop.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, List

from .claim_builder import build_claim_for_task
from .follow_up_planner import build_follow_up_tasks
from .gap_reflector import reflect_task_gaps
from .mcp_tools import load_sequential_thinking_tools, sequential_gap_review, sequential_plan_review
from .planner import create_research_plan
from .state import ResearchGap, ResearchState, ResearchTask, initial_state, stable_id, timeline_event
from .synthesizer import synthesize_research_report
from .tool_router import execute_research_task


def _normalize_extra_task(raw: Dict[str, Any], enterprise_name: str, index: int) -> ResearchTask:
    question = str(raw.get("question") or "").strip()
    purpose = str(raw.get("purpose") or "补充研究证据缺口。").strip()
    category = str(raw.get("category") or "general").strip()
    task_id = str(raw.get("id") or stable_id("rt_seq", enterprise_name, question or index))
    required_evidence = raw.get("required_evidence") if isinstance(raw.get("required_evidence"), list) else []
    tool_hints = raw.get("tool_hints") if isinstance(raw.get("tool_hints"), list) else []
    return {
        "id": task_id,
        "question": question or f"补充研究问题 {index}",
        "purpose": purpose,
        "category": category,
        "required_evidence": [str(item) for item in required_evidence[:8]],
        "priority": int(raw.get("priority") or 50 + index),
        "status": "pending",
        "tool_hints": [str(item) for item in tool_hints[:6]],
    }


def _merge_sequential_plan(tasks: list[ResearchTask], review_json: Dict[str, Any], enterprise_name: str) -> list[ResearchTask]:
    existing_ids = {task.get("id") for task in tasks}
    merged = list(tasks)
    add_tasks = review_json.get("add_tasks") if isinstance(review_json, dict) else []
    if not isinstance(add_tasks, list):
        return merged
    for index, raw_task in enumerate(add_tasks[:3], start=1):
        if not isinstance(raw_task, dict):
            continue
        task = _normalize_extra_task(raw_task, enterprise_name, index)
        if task.get("id") in existing_ids:
            continue
        task["planner_source"] = "sequential_thinking_mcp"
        merged.append(task)
        existing_ids.add(task.get("id"))
    return merged


def _extra_gaps_from_review(task_id: str, review_json: Dict[str, Any]) -> list[ResearchGap]:
    raw_gaps = review_json.get("extra_gaps") if isinstance(review_json, dict) else []
    if not isinstance(raw_gaps, list):
        return []
    gaps: list[ResearchGap] = []
    for index, raw_gap in enumerate(raw_gaps[:3], start=1):
        if not isinstance(raw_gap, dict):
            continue
        description = str(raw_gap.get("description") or "").strip()
        if not description:
            continue
        actions = raw_gap.get("suggested_next_actions") if isinstance(raw_gap.get("suggested_next_actions"), list) else []
        gaps.append({
            "id": stable_id("gap_seq", task_id, description, index),
            "task_id": task_id,
            "description": description,
            "why_it_matters": str(raw_gap.get("why_it_matters") or "Sequential Thinking MCP 识别的补充证据缺口。"),
            "suggested_next_actions": [str(item) for item in actions[:6]],
            "severity": str(raw_gap.get("severity") or "medium"),
            "source": "sequential_thinking_mcp",
        })
    return gaps


async def _execute_task_round(
    state: ResearchState,
    enterprise_name: str,
    task: ResearchTask,
    sequential_status: Dict[str, Any],
    sequential_tools: List[Any],
    round_number: int = 1,
) -> None:
    task["status"] = "running"
    task["round"] = round_number
    state["current_task_id"] = task.get("id")
    agent = "Research Engine" if round_number == 1 else "Research Engine · 二轮补证"
    state["timeline"].append(timeline_event(agent, "执行研究任务", task.get("question", ""), "running", "action"))

    result = await asyncio.to_thread(execute_research_task, enterprise_name, task)
    evidence = result.get("evidence", [])
    state["evidence"].extend(evidence)
    task["evidence_ids"] = [item.get("id") for item in evidence if item.get("id")]
    task["raw_outputs"] = result.get("raw_outputs", {})

    claim = build_claim_for_task(enterprise_name, task, evidence)
    if round_number > 1:
        claim["text"] = f"二轮补证：{claim.get('text', '')}"
        claim["parent_task_id"] = task.get("parent_task_id")
        claim["round"] = round_number
    state["claims"].append(claim)
    task["claim_ids"] = [claim.get("id", "")]

    gaps = reflect_task_gaps(task, evidence)
    if sequential_status.get("available"):
        gap_review = await sequential_gap_review(task, evidence, gaps, tools=sequential_tools)
        if gap_review.get("success") and isinstance(gap_review.get("json"), dict):
            task["sequential_gap_notes"] = gap_review["json"].get("gap_notes", "")
            task["sequential_follow_up_queries"] = gap_review["json"].get("follow_up_queries", [])
            extra_gaps = _extra_gaps_from_review(task.get("id", ""), gap_review["json"])
            gaps.extend(extra_gaps)
        elif gap_review.get("error"):
            state["errors"].append(f"Sequential Thinking gap review failed for {task.get('id')}: {gap_review.get('error')}")
    state["gaps"].extend(gaps)

    if result.get("errors"):
        state["errors"].extend(result.get("errors", []))
    task["status"] = "completed" if evidence else "failed"
    state["timeline"][-1]["status"] = "completed" if evidence else "failed"
    state["timeline"][-1]["findings"] = [
        f"证据 {len(evidence)} 项",
        f"结论 {1 if claim else 0} 条",
        f"缺口 {len(gaps)} 项",
    ]
    if round_number > 1:
        state["timeline"][-1]["detail"] = f"二轮补证任务，父任务：{task.get('parent_task_id') or '未标记'}"


async def prepare_deep_research_plan(enterprise_name: str, objective: str = "完整贷前尽调", max_iterations: int = 6) -> Dict[str, Any]:
    """Build and review the research plan without executing tools.

    This is the natural HITL checkpoint: humans can inspect whether the agent
    is asking the right due-diligence questions before costly external calls.
    """
    state: ResearchState = initial_state(enterprise_name=enterprise_name, objective=objective, max_iterations=max_iterations)
    sequential_status = await load_sequential_thinking_tools()
    sequential_tools = sequential_status.get("tools", [])
    state["sequential_thinking"] = {
        "enabled": bool(sequential_status.get("available")),
        "tool_names": sequential_status.get("tool_names", []),
        "error": sequential_status.get("error", ""),
    }
    if sequential_status.get("available"):
        state["timeline"].append(timeline_event("Sequential Thinking MCP", "已启用研究规划增强", "用于计划复核和证据缺口复核", "completed", "analysis"))
    else:
        state["timeline"].append(timeline_event("Sequential Thinking MCP", "未启用研究检查点", f"Sequential Thinking MCP 未启用或不可用：{sequential_status.get('error')}", "completed", "analysis"))

    plan_result = await asyncio.to_thread(create_research_plan, enterprise_name, objective)
    tasks = plan_result.get("tasks", [])
    state["planner"] = {
        "source": plan_result.get("planner_source"),
        "metadata": plan_result.get("metadata", {}),
        "error": plan_result.get("error", ""),
    }
    if plan_result.get("planner_source") == "llm":
        detail = plan_result.get("metadata", {}).get("plan_summary") or "LLM Planner 已生成结构化研究计划"
        state["timeline"].append(timeline_event("LLM Planner", "生成动态研究计划", str(detail)[:240], "completed", "analysis"))
    else:
        detail = plan_result.get("error") or plan_result.get("metadata", {}).get("reason") or "使用默认规则研究计划"
        state["timeline"].append(timeline_event("Research Planner", "LLM Planner 降级到规则计划", str(detail)[:240], "completed", "analysis"))
        if plan_result.get("error"):
            state["errors"].append(f"LLM Planner fallback: {plan_result.get('error')}")

    if sequential_status.get("available"):
        plan_review = await sequential_plan_review(enterprise_name, objective, tasks, tools=sequential_tools)
        if plan_review.get("success") and isinstance(plan_review.get("json"), dict):
            state["sequential_plan_review"] = plan_review.get("json")
            tasks = _merge_sequential_plan(tasks, plan_review["json"], enterprise_name)
            plan_notes = plan_review["json"].get("plan_notes") or "已完成研究计划复核"
            state["timeline"].append(timeline_event("Sequential Thinking MCP", "完成研究计划复核", str(plan_notes)[:240], "completed", "analysis"))
        else:
            state["errors"].append(f"Sequential Thinking plan review failed: {plan_review.get('error')}")
            state["timeline"].append(timeline_event("Sequential Thinking MCP", "研究计划复核降级", str(plan_review.get("error") or "未返回结构化计划")[:240], "failed", "analysis"))

    state["tasks"] = tasks
    state["timeline"].append(timeline_event("Research Planner", "生成研究计划", f"规划{len(tasks)}个研究问题", "completed", "analysis"))
    return {"success": True, "research_state": state, "sequential_status": sequential_status}


async def execute_deep_research_plan(state: ResearchState) -> Dict[str, Any]:
    """Execute an approved research state and synthesize the final report."""
    enterprise_name = state.get("enterprise_name", "")
    max_iterations = int(state.get("max_iterations") or 6)
    sequential_status = await load_sequential_thinking_tools()
    sequential_tools = sequential_status.get("tools", [])
    if "sequential_thinking" not in state:
        state["sequential_thinking"] = {
            "enabled": bool(sequential_status.get("available")),
            "tool_names": sequential_status.get("tool_names", []),
            "error": sequential_status.get("error", ""),
        }

    completed = 0
    first_round_tasks = sorted(state.get("tasks", []), key=lambda item: item.get("priority", 99))
    for task in first_round_tasks:
        if completed >= max_iterations:
            break
        await _execute_task_round(state, enterprise_name, task, sequential_status, sequential_tools, round_number=1)
        completed += 1
        state["iteration"] = completed

    follow_up_tasks = build_follow_up_tasks(enterprise_name, state.get("tasks", []), state.get("gaps", []), state.get("claims", []), limit=3)
    state["follow_up_tasks"] = follow_up_tasks
    if follow_up_tasks:
        state["timeline"].append(timeline_event(
            "Sequential Thinking MCP",
            "生成二轮补证任务",
            f"基于证据缺口追加{len(follow_up_tasks)}个follow-up task",
            "completed",
            "analysis",
        ))
        state["tasks"].extend(follow_up_tasks)
        for task in follow_up_tasks:
            if completed >= max_iterations + len(follow_up_tasks):
                break
            await _execute_task_round(state, enterprise_name, task, sequential_status, sequential_tools, round_number=2)
            completed += 1
            state["iteration"] = completed
    else:
        state["timeline"].append(timeline_event(
            "Sequential Thinking MCP",
            "无需二轮补证",
            "当前证据缺口不足以生成高价值follow-up task",
            "completed",
            "analysis",
        ))

    state["research_rounds"] = [
        {"round": 1, "task_count": len(first_round_tasks), "description": "首轮计划任务执行"},
        {"round": 2, "task_count": len(follow_up_tasks), "description": "Sequential Thinking Gap驱动补证"},
    ]

    state["report"] = synthesize_research_report(state)
    state["timeline"].append(timeline_event("Research Synthesizer", "生成研究型尽调报告", "已输出Research Plan、Evidence、Claim和Gap", "completed", "conclusion"))
    state["report"]["timeline"] = state["timeline"]
    return {"success": True, "research_state": state, "report": state["report"]}


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


def run_deep_research_due_diligence_sync(enterprise_name: str, objective: str = "完整贷前尽调", max_iterations: int = 6) -> Dict[str, Any]:
    return asyncio.run(run_deep_research_due_diligence(enterprise_name, objective, max_iterations))
