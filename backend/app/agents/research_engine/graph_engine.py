"""LangGraph wrapper for the DeepResearch engine.

This module intentionally keeps the existing specialist tools, HITL API shape,
Evidence Store, claim builder, follow-up planner, and synthesizer unchanged.
It only moves the internal DeepResearch orchestration shell into LangGraph
nodes so checkpointing/resume can be introduced later without rewriting the
business logic again.
"""

from __future__ import annotations

import asyncio
from typing import Any, Awaitable, Callable, Dict, List, Literal, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.skills import load_skills_for_task

from .claim_builder import build_claim_for_task
from .follow_up_planner import build_follow_up_tasks
from .gap_reflector import reflect_task_gaps
from .mcp_tools import load_sequential_thinking_tools, run_sequential_thought_loop, sequential_gap_review, sequential_plan_review
from .planner import create_default_research_plan, create_research_plan
from .report_quality_gate import apply_report_quality_gate, build_quality_timeline_event
from .state import ResearchGap, ResearchState, ResearchTask, initial_state, stable_id, timeline_event
from .synthesizer import synthesize_research_report
from .tool_router import execute_research_task


class DeepResearchGraphState(TypedDict, total=False):
    enterprise_name: str
    objective: str
    max_iterations: int
    phase: Literal["prepare", "execute"]
    research_state: ResearchState
    sequential_status: Dict[str, Any]
    sequential_tools: List[Any]
    prepared: bool
    executed: bool
    success: bool
    report: Dict[str, Any]
    error: str
    on_update: Callable[[Dict[str, Any]], Awaitable[None]]


async def _emit_prepare_update(graph_state: DeepResearchGraphState, payload: Dict[str, Any]) -> None:
    callback = graph_state.get("on_update")
    if callback:
        await callback(payload)


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
        "why_it_matters": str(raw_gap.get("why_it_matters") or "研究计划复核识别的补充证据缺口。"),
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
    tool_traces = result.get("tool_traces", [])
    state["evidence"].extend(evidence)
    state.setdefault("tool_traces", []).extend(tool_traces)
    task["evidence_ids"] = [item.get("id") for item in evidence if item.get("id")]
    task["tool_call_ids"] = [item.get("tool_call_id") for item in tool_traces if item.get("tool_call_id")]
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
            gaps.extend(_extra_gaps_from_review(task.get("id", ""), gap_review["json"]))
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


async def _prepare_plan_node(graph_state: DeepResearchGraphState) -> DeepResearchGraphState:
    enterprise_name = graph_state.get("enterprise_name", "")
    objective = graph_state.get("objective") or "完整贷前尽调"
    max_iterations = int(graph_state.get("max_iterations") or 6)
    state: ResearchState = initial_state(enterprise_name=enterprise_name, objective=objective, max_iterations=max_iterations)

    runtime_skills = load_skills_for_task("loan_due_diligence", objective)
    state["runtime_skills"] = {
        "skill_ids": runtime_skills.get("skill_ids", []),
        "errors": runtime_skills.get("errors", []),
    }
    state["timeline"].append(timeline_event(
        "Skill Runtime",
        "加载尽调方法论技能",
        f"已加载{len(runtime_skills.get('skill_ids', []))}个运行时技能：{', '.join(runtime_skills.get('skill_ids', [])) or '无'}",
        "completed" if runtime_skills.get("skill_ids") else "failed",
        "analysis",
    ))

    sequential_status = await load_sequential_thinking_tools()
    sequential_tools = sequential_status.get("tools", [])
    state["sequential_thinking"] = {
        "enabled": bool(sequential_status.get("available")),
        "transport": sequential_status.get("transport") or "disabled",
        "remote_url": sequential_status.get("remote_url", ""),
        "tool_names": sequential_status.get("tool_names", []),
        "error": sequential_status.get("error", ""),
    }
    if sequential_status.get("available"):
        state["timeline"].append(timeline_event("研究思考链", "已启用研究思考状态机", "用于计划生成前的研究步骤记录、扩展和修订。", "completed", "analysis"))
    else:
        state["timeline"].append(timeline_event("研究思考链", "未启用研究思考状态机", "Sequential Thinking 服务暂不可用，已降级为基础计划流程。", "completed", "analysis"))
    await _emit_prepare_update(graph_state, {"stage": "sequential_status", "research_state": state})

    thought_loop_context = ""
    default_tasks = create_default_research_plan(enterprise_name, objective)
    if sequential_status.get("available"):
        state["timeline"].append(timeline_event("研究思考链", "启动研究思考链", "确认主体边界、证据需求、数据边界和人工确认点。", "running", "analysis"))
        state["sequential_thought_loop"] = {"success": False, "steps": [], "plan_context": "", "error": ""}
        await _emit_prepare_update(graph_state, {"stage": "thought_loop_start", "research_state": state})

        async def on_thought_step(step: Dict[str, Any], steps: List[Dict[str, Any]]) -> None:
            state["sequential_thought_loop"] = {
                "success": False,
                "steps": steps,
                "plan_context": "\n".join([f"研究思考链步骤{item.get('thoughtNumber')}：{item.get('summary')}" for item in steps]),
                "error": "",
            }
            state["timeline"][-1]["findings"] = [f"已记录第{step.get('thoughtNumber')}步研究思考"]
            await _emit_prepare_update(graph_state, {"stage": "thought_loop_step", "step": step, "research_state": state})

        thought_loop = await run_sequential_thought_loop(
            enterprise_name,
            objective,
            default_tasks,
            tools=sequential_tools,
            session_id=stable_id("seq", enterprise_name, objective),
            on_step=on_thought_step,
        )
        state["sequential_thought_loop"] = thought_loop
        thought_loop_context = str(thought_loop.get("plan_context") or "")
        if thought_loop.get("success"):
            state["timeline"][-1]["status"] = "completed"
            state["timeline"][-1]["findings"] = [f"记录{len(thought_loop.get('steps', []))}步研究思考", "已注入LLM Planner"]
            state["timeline"].append(timeline_event("研究思考链", "完成研究思考链", "研究步骤已转化为计划生成上下文。", "completed", "analysis"))
        else:
            state["timeline"][-1]["status"] = "failed"
            state["timeline"][-1]["detail"] = str(thought_loop.get("error") or "研究思考链不可用")[:240]
            state["errors"].append(f"Sequential Thinking thought loop failed: {thought_loop.get('error')}")
        await _emit_prepare_update(graph_state, {"stage": "thought_loop_done", "research_state": state})

    state["timeline"].append(timeline_event("研究计划生成器", "生成研究计划中", "正在根据研究思考链上下文生成可执行研究问题。", "running", "analysis"))
    await _emit_prepare_update(graph_state, {"stage": "plan_generation_start", "research_state": state})
    plan_result = await asyncio.to_thread(create_research_plan, enterprise_name, objective, thought_loop_context, runtime_skills)
    tasks = plan_result.get("tasks", [])
    state["planner"] = {
        "source": plan_result.get("planner_source"),
        "metadata": plan_result.get("metadata", {}),
        "error": plan_result.get("error", ""),
    }
    if plan_result.get("planner_source") == "llm":
        detail = plan_result.get("metadata", {}).get("plan_summary") or "动态研究计划已生成结构化研究任务"
        state["timeline"][-1]["content"] = "生成动态研究计划"
        state["timeline"][-1]["detail"] = str(detail)[:240]
        state["timeline"][-1]["status"] = "completed"
    else:
        detail = plan_result.get("error") or plan_result.get("metadata", {}).get("reason") or "使用默认规则研究计划"
        state["timeline"][-1]["content"] = "动态计划降级到规则计划"
        state["timeline"][-1]["detail"] = str(detail)[:240]
        state["timeline"][-1]["status"] = "completed"
        if plan_result.get("error"):
            state["errors"].append(f"动态研究计划降级：{plan_result.get('error')}")
    state["tasks"] = []
    for index, task in enumerate(tasks, start=1):
        state["tasks"] = tasks[:index]
        await _emit_prepare_update(graph_state, {"stage": "plan_task", "task": task, "research_state": state})

    if sequential_status.get("available") and not thought_loop_context:
        plan_review = await sequential_plan_review(enterprise_name, objective, tasks, tools=sequential_tools)
        if plan_review.get("success") and isinstance(plan_review.get("json"), dict):
            state["sequential_plan_review"] = plan_review.get("json")
            tasks = _merge_sequential_plan(tasks, plan_review["json"], enterprise_name)
            plan_notes = plan_review["json"].get("plan_notes") or "已完成研究计划复核"
            state["timeline"].append(timeline_event("研究计划复核", "完成研究计划复核", str(plan_notes)[:240], "completed", "analysis"))
        else:
            state["errors"].append(f"Sequential Thinking plan review failed: {plan_review.get('error')}")
            state["timeline"].append(timeline_event("研究计划复核", "研究计划复核降级", "复核服务未返回结构化计划，已继续执行基础研究计划。", "failed", "analysis"))

    state["tasks"] = tasks
    state["timeline"].append(timeline_event("研究计划生成器", "生成研究计划", f"规划{len(tasks)}个研究问题", "completed", "analysis"))
    await _emit_prepare_update(graph_state, {"stage": "plan_done", "research_state": state})
    return {
        **graph_state,
        "research_state": state,
        "sequential_status": sequential_status,
        "sequential_tools": sequential_tools,
        "prepared": True,
        "success": True,
    }


async def _execute_round1_node(graph_state: DeepResearchGraphState) -> DeepResearchGraphState:
    state = graph_state.get("research_state") or {}
    enterprise_name = state.get("enterprise_name", graph_state.get("enterprise_name", ""))
    max_iterations = int(state.get("max_iterations") or graph_state.get("max_iterations") or 6)
    sequential_status = graph_state.get("sequential_status") or await load_sequential_thinking_tools()
    sequential_tools = graph_state.get("sequential_tools") or sequential_status.get("tools", [])

    completed = 0
    first_round_tasks = sorted(state.get("tasks", []), key=lambda item: item.get("priority", 99))
    for task in first_round_tasks:
        if completed >= max_iterations:
            break
        await _execute_task_round(state, enterprise_name, task, sequential_status, sequential_tools, round_number=1)
        completed += 1
        state["iteration"] = completed
    state["first_round_task_count"] = len(first_round_tasks)
    return {**graph_state, "research_state": state, "sequential_status": sequential_status, "sequential_tools": sequential_tools}


async def _plan_followups_node(graph_state: DeepResearchGraphState) -> DeepResearchGraphState:
    state = graph_state.get("research_state") or {}
    enterprise_name = state.get("enterprise_name", graph_state.get("enterprise_name", ""))
    follow_up_tasks = build_follow_up_tasks(enterprise_name, state.get("tasks", []), state.get("gaps", []), state.get("claims", []), limit=3)
    state["follow_up_tasks"] = follow_up_tasks
    if follow_up_tasks:
        state["timeline"].append(timeline_event(
            "研究计划复核",
            "生成二轮补证任务",
            f"基于证据缺口追加{len(follow_up_tasks)}个follow-up task",
            "completed",
            "analysis",
        ))
        state["tasks"].extend(follow_up_tasks)
    else:
        state["timeline"].append(timeline_event(
            "研究计划复核",
            "无需二轮补证",
            "当前证据缺口不足以生成高价值follow-up task",
            "completed",
            "analysis",
        ))
    return {**graph_state, "research_state": state}


async def _execute_followups_node(graph_state: DeepResearchGraphState) -> DeepResearchGraphState:
    state = graph_state.get("research_state") or {}
    enterprise_name = state.get("enterprise_name", graph_state.get("enterprise_name", ""))
    max_iterations = int(state.get("max_iterations") or graph_state.get("max_iterations") or 6)
    sequential_status = graph_state.get("sequential_status") or await load_sequential_thinking_tools()
    sequential_tools = graph_state.get("sequential_tools") or sequential_status.get("tools", [])
    completed = int(state.get("iteration") or 0)
    follow_up_tasks = state.get("follow_up_tasks", [])
    for task in follow_up_tasks:
        if completed >= max_iterations + len(follow_up_tasks):
            break
        await _execute_task_round(state, enterprise_name, task, sequential_status, sequential_tools, round_number=2)
        completed += 1
        state["iteration"] = completed
    return {**graph_state, "research_state": state, "sequential_status": sequential_status, "sequential_tools": sequential_tools}


async def _synthesize_node(graph_state: DeepResearchGraphState) -> DeepResearchGraphState:
    state = graph_state.get("research_state") or {}
    state["research_rounds"] = [
        {"round": 1, "task_count": int(state.get("first_round_task_count") or len([task for task in state.get("tasks", []) if task.get("round") == 1])), "description": "首轮计划任务执行"},
        {"round": 2, "task_count": len(state.get("follow_up_tasks", [])), "description": "证据缺口驱动补证"},
    ]
    state["report"] = synthesize_research_report(state)
    state["timeline"].append(timeline_event("报告装配器", "生成贷前尽调报告", "已完成研究计划、证据链、结论声明和证据缺口装配", "completed", "conclusion"))
    quality_patch = apply_report_quality_gate(state["report"])
    state["quality_evaluation"] = quality_patch.get("quality_evaluation")
    state["timeline"].append(build_quality_timeline_event(quality_patch))
    state["report"]["timeline"] = state["timeline"]
    return {**graph_state, "research_state": state, "report": state["report"], "executed": True, "success": True}


def _route_entry(graph_state: DeepResearchGraphState) -> str:
    return "execute_round1" if graph_state.get("phase") == "execute" else "prepare_plan"


async def _route_entry_node(graph_state: DeepResearchGraphState) -> DeepResearchGraphState:
    return graph_state


def build_deep_research_graph():
    workflow = StateGraph(DeepResearchGraphState)
    workflow.add_node("route_entry", _route_entry_node)
    workflow.add_node("prepare_plan", _prepare_plan_node)
    workflow.add_node("execute_round1", _execute_round1_node)
    workflow.add_node("plan_followups", _plan_followups_node)
    workflow.add_node("execute_followups", _execute_followups_node)
    workflow.add_node("synthesize", _synthesize_node)
    workflow.set_entry_point("route_entry")
    workflow.add_conditional_edges("route_entry", _route_entry, {
        "prepare_plan": "prepare_plan",
        "execute_round1": "execute_round1",
    })
    workflow.add_edge("prepare_plan", END)
    workflow.add_edge("execute_round1", "plan_followups")
    workflow.add_edge("plan_followups", "execute_followups")
    workflow.add_edge("execute_followups", "synthesize")
    workflow.add_edge("synthesize", END)
    return workflow.compile()


_GRAPH = None


def get_deep_research_graph():
    global _GRAPH
    if _GRAPH is None:
        _GRAPH = build_deep_research_graph()
    return _GRAPH


async def prepare_deep_research_plan_graph(
    enterprise_name: str,
    objective: str = "完整贷前尽调",
    max_iterations: int = 6,
    on_update: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    graph = get_deep_research_graph()
    result = await graph.ainvoke({
        "phase": "prepare",
        "enterprise_name": enterprise_name,
        "objective": objective,
        "max_iterations": max_iterations,
        "on_update": on_update,
    })
    return {
        "success": bool(result.get("success")),
        "research_state": result.get("research_state", {}),
        "sequential_status": result.get("sequential_status", {}),
        "graph_mode": "langgraph_shell",
    }


async def execute_deep_research_plan_graph(state: ResearchState) -> Dict[str, Any]:
    graph = get_deep_research_graph()
    result = await graph.ainvoke({
        "phase": "execute",
        "enterprise_name": state.get("enterprise_name", ""),
        "objective": state.get("objective", "完整贷前尽调"),
        "max_iterations": int(state.get("max_iterations") or 6),
        "research_state": state,
    })
    return {
        "success": bool(result.get("success")),
        "research_state": result.get("research_state", {}),
        "report": result.get("report", {}),
        "graph_mode": "langgraph_shell",
    }
