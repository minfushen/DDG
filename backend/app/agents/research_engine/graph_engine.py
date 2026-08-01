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
from langchain_core.runnables import RunnableConfig

from app.agents.skills import load_skills_for_task
from app.config import settings
from .checkpointer import get_checkpointer

from .claim_builder import build_claim_for_task
from .evidence_consistency import apply_conflicts_to_claim, conflicts_to_gaps, detect_field_conflicts
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
    session_id: str
    parsed_intent: Dict[str, Any]
    prepared: bool
    executed: bool
    success: bool
    report: Dict[str, Any]
    error: str


async def _emit_prepare_update(config: RunnableConfig, payload: Dict[str, Any]) -> None:
    callback = (config or {}).get("configurable", {}).get("on_update")
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


async def _run_task_research(
    enterprise_name: str,
    task: ResearchTask,
    session_id: str | None = None,
) -> tuple[ResearchTask, Dict[str, Any]]:
    """并行安全的单任务工具检索：只做重 I/O，不触碰共享 state。

    返回 (task, result)；单任务异常时返回带 errors 的空结果，保证 gather 不中断。
    """
    try:
        result = await asyncio.to_thread(execute_research_task, enterprise_name, task, session_id=session_id)
        return task, result
    except Exception as exc:  # 单任务失败不应拖垮整批并行
        return task, {"evidence": [], "tool_traces": [], "raw_outputs": {}, "errors": [f"{type(exc).__name__}: {exc}"]}


async def _compute_gap_review(
    task: ResearchTask,
    result: Dict[str, Any],
    sequential_status: Dict[str, Any],
    sequential_tools: List[Any],
) -> Dict[str, Any] | None:
    """并行预计算单任务的 Sequential Thinking gap review。

    在串行 merge 之前并行执行 MCP 调用，避免 npx 冷启动串行成为瓶颈。
    """
    if not sequential_status.get("available"):
        return None
    evidence = result.get("evidence", [])
    gaps = reflect_task_gaps(task, evidence)
    try:
        return await sequential_gap_review(task, evidence, gaps, tools=sequential_tools)
    except Exception as exc:
        return {"success": False, "error": f"{type(exc).__name__}: {exc}"}


async def _merge_task_result(
    state: ResearchState,
    enterprise_name: str,
    task: ResearchTask,
    result: Dict[str, Any],
    gap_review: Dict[str, Any] | None,
    round_number: int = 1,
    session_id: str | None = None,
) -> None:
    """顺序合并单个任务的研究结果到共享 state。

    gap_review 由并行预计算步骤传入；本函数仅做确定性状态写入，不发起 MCP 调用，
    避免 npx 冷启动串行阻塞。timeline 用本地引用而非 state["timeline"][-1]。
    """
    task["status"] = "running"
    task["round"] = round_number
    state["current_task_id"] = task.get("id")
    agent = "Research Engine" if round_number == 1 else "Research Engine · 二轮补证"
    tl_event = timeline_event(agent, "执行研究任务", task.get("question", ""), "running", "action")
    state["timeline"].append(tl_event)

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
    # 跨源证据一致性校验：检测同字段跨源取值冲突，降置信度并标记人工复核
    conflicts = detect_field_conflicts(evidence)
    if conflicts:
        apply_conflicts_to_claim(claim, conflicts)
    state["claims"].append(claim)
    task["claim_ids"] = [claim.get("id", "")]

    gaps = reflect_task_gaps(task, evidence)
    # gap_review 由并行预计算步骤传入（见 _compute_gap_review），merge 只做状态写入
    if gap_review and gap_review.get("success") and isinstance(gap_review.get("json"), dict):
        task["sequential_gap_notes"] = gap_review["json"].get("gap_notes", "")
        task["sequential_follow_up_queries"] = gap_review["json"].get("follow_up_queries", [])
        gaps.extend(_extra_gaps_from_review(task.get("id", ""), gap_review["json"]))
    elif gap_review and gap_review.get("error"):
        state["errors"].append(f"Sequential Thinking gap review failed for {task.get('id')}: {gap_review.get('error')}")
    # 跨源冲突缺口喂给 approve_gap 中断（人工复核冲突字段）
    if conflicts:
        gaps.extend(conflicts_to_gaps(task.get("id", ""), conflicts))
    state["gaps"].extend(gaps)

    if result.get("errors"):
        state["errors"].extend(result.get("errors", []))
    task["status"] = "completed" if evidence else "failed"
    tl_event["status"] = "completed" if evidence else "failed"
    tl_event["findings"] = [
        f"证据 {len(evidence)} 项",
        f"结论 {1 if claim else 0} 条",
        f"缺口 {len(gaps)} 项",
    ]
    if round_number > 1:
        tl_event["detail"] = f"二轮补证任务，父任务：{task.get('parent_task_id') or '未标记'}"


async def _prepare_plan_node(graph_state: DeepResearchGraphState, config: RunnableConfig) -> DeepResearchGraphState:
    enterprise_name = graph_state.get("enterprise_name", "")
    objective = graph_state.get("objective") or "完整贷前尽调"
    max_iterations = int(graph_state.get("max_iterations") or 6)
    session_id = graph_state.get("session_id") or stable_id("sess", enterprise_name, objective)
    parsed_intent = graph_state.get("parsed_intent") or None
    state: ResearchState = initial_state(enterprise_name=enterprise_name, objective=objective, max_iterations=max_iterations)
    state["parsed_intent"] = parsed_intent
    state["slots"] = (parsed_intent or {}).get("slots") or {}
    state["max_depth"] = int(getattr(settings, "RESEARCH_MAX_DEPTH", 2) or 2)
    state["current_depth"] = 1

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
    await _emit_prepare_update(config, {"stage": "sequential_status", "research_state": state})

    thought_loop_context = ""
    default_tasks = create_default_research_plan(enterprise_name, objective, parsed_intent=parsed_intent)
    if sequential_status.get("available"):
        state["timeline"].append(timeline_event("研究思考链", "启动研究思考链", "确认主体边界、证据需求、数据边界和人工确认点。", "running", "analysis"))
        state["sequential_thought_loop"] = {"success": False, "steps": [], "plan_context": "", "error": ""}
        await _emit_prepare_update(config, {"stage": "thought_loop_start", "research_state": state})

        async def on_thought_step(step: Dict[str, Any], steps: List[Dict[str, Any]]) -> None:
            state["sequential_thought_loop"] = {
                "success": False,
                "steps": steps,
                "plan_context": "\n".join([f"研究思考链步骤{item.get('thoughtNumber')}：{item.get('summary')}" for item in steps]),
                "error": "",
            }
            state["timeline"][-1]["findings"] = [f"已记录第{step.get('thoughtNumber')}步研究思考"]
            await _emit_prepare_update(config, {"stage": "thought_loop_step", "step": step, "research_state": state})

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
        await _emit_prepare_update(config, {"stage": "thought_loop_done", "research_state": state})

    state["timeline"].append(timeline_event("研究计划生成器", "生成研究计划中", "正在根据研究思考链上下文生成可执行研究问题。", "running", "analysis"))
    await _emit_prepare_update(config, {"stage": "plan_generation_start", "research_state": state})
    plan_result = await asyncio.to_thread(
        create_research_plan,
        enterprise_name,
        objective,
        thought_loop_context,
        runtime_skills,
        session_id=session_id,
        parsed_intent=parsed_intent,
    )
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
        await _emit_prepare_update(config, {"stage": "plan_task", "task": task, "research_state": state})

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
    await _emit_prepare_update(config, {"stage": "plan_done", "research_state": state})
    return {
        **graph_state,
        "research_state": state,
        "session_id": session_id,
        "prepared": True,
        "success": True,
    }


async def _execute_round1_node(graph_state: DeepResearchGraphState, config: RunnableConfig) -> DeepResearchGraphState:
    state = graph_state.get("research_state") or {}
    enterprise_name = state.get("enterprise_name", graph_state.get("enterprise_name", ""))
    max_iterations = int(state.get("max_iterations") or graph_state.get("max_iterations") or 6)
    session_id = graph_state.get("session_id") or stable_id("sess", enterprise_name, state.get("objective", "完整贷前尽调"))
    sequential_status = await load_sequential_thinking_tools()
    sequential_tools = sequential_status.get("tools", [])

    completed = 0
    first_round_tasks = sorted(state.get("tasks", []), key=lambda item: item.get("priority", 99))
    batch = first_round_tasks[:max_iterations]
    # 并行执行各任务的工具检索（工商/财务/司法/行业互不依赖），结果按任务顺序返回
    if batch:
        results = await asyncio.gather(*[_run_task_research(enterprise_name, t, session_id) for t in batch])
        # 并行预计算 MCP gap review（避免 npx 冷启动串行瓶颈），再顺序合并状态
        gap_reviews = await asyncio.gather(*[_compute_gap_review(t, r, sequential_status, sequential_tools) for t, r in results])
        for (task, result), gap_review in zip(results, gap_reviews):
            await _merge_task_result(state, enterprise_name, task, result, gap_review, round_number=1, session_id=session_id)
        completed = len(batch)
    state["first_round_task_count"] = len(first_round_tasks)
    state["iteration"] = completed
    return {**graph_state, "research_state": state, "sequential_status": sequential_status, "sequential_tools": sequential_tools, "session_id": session_id}


async def _plan_followups_node(graph_state: DeepResearchGraphState, config: RunnableConfig) -> DeepResearchGraphState:
    state = graph_state.get("research_state") or {}
    enterprise_name = state.get("enterprise_name", graph_state.get("enterprise_name", ""))
    # 树状递归：当前层级+1 即为本批 follow-up 的深度
    depth = int(state.get("current_depth", 1)) + 1
    follow_up_tasks = build_follow_up_tasks(enterprise_name, state.get("tasks", []), state.get("gaps", []), state.get("claims", []), limit=3, depth=depth)
    state["follow_up_tasks"] = follow_up_tasks
    if follow_up_tasks:
        depth_label = "二轮补证" if depth == 2 else f"第{depth}轮深研补证"
        state["timeline"].append(timeline_event(
            "研究计划复核",
            f"生成{depth_label}任务",
            f"基于证据缺口追加{len(follow_up_tasks)}个follow-up task（深度{depth}）",
            "completed",
            "analysis",
        ))
        state["tasks"].extend(follow_up_tasks)
    else:
        state["timeline"].append(timeline_event(
            "研究计划复核",
            "无需补证",
            "当前证据缺口不足以生成高价值follow-up task",
            "completed",
            "analysis",
        ))
    return {**graph_state, "research_state": state}


async def _execute_followups_node(graph_state: DeepResearchGraphState, config: RunnableConfig) -> DeepResearchGraphState:
    state = graph_state.get("research_state") or {}
    enterprise_name = state.get("enterprise_name", graph_state.get("enterprise_name", ""))
    session_id = graph_state.get("session_id") or stable_id("sess", enterprise_name, state.get("objective", "完整贷前尽调"))
    sequential_status = await load_sequential_thinking_tools()
    sequential_tools = sequential_status.get("tools", [])
    completed = int(state.get("iteration") or 0)
    follow_up_tasks = state.get("follow_up_tasks", [])
    gaps_before = len(state.get("gaps", []))
    # 并行执行补证任务（补证任务之间互不依赖），round_number 取自任务 depth
    if follow_up_tasks:
        results = await asyncio.gather(*[_run_task_research(enterprise_name, t, session_id) for t in follow_up_tasks])
        gap_reviews = await asyncio.gather(*[_compute_gap_review(t, r, sequential_status, sequential_tools) for t, r in results])
        for (task, result), gap_review in zip(results, gap_reviews):
            await _merge_task_result(state, enterprise_name, task, result, gap_review, round_number=int(task.get("depth", 2)), session_id=session_id)
        completed += len(follow_up_tasks)
    state["iteration"] = completed
    # 推进递归深度；记录本轮补证是否产生新缺口，供树状递归路由判断
    state["current_depth"] = int(state.get("current_depth", 1)) + (1 if follow_up_tasks else 0)
    state["_followups_produced_new_gaps"] = len(state.get("gaps", [])) > gaps_before
    return {**graph_state, "research_state": state, "sequential_status": sequential_status, "sequential_tools": sequential_tools, "session_id": session_id}


async def _synthesize_node(graph_state: DeepResearchGraphState, config: RunnableConfig) -> DeepResearchGraphState:
    state = graph_state.get("research_state") or {}
    state["research_rounds"] = [
        {"round": 1, "task_count": int(state.get("first_round_task_count") or len([task for task in state.get("tasks", []) if task.get("round") == 1])), "description": "首轮计划任务执行"},
        {"round": 2, "task_count": len(state.get("follow_up_tasks", [])), "description": "证据缺口驱动补证"},
    ]
    state["report"] = synthesize_research_report(state, template=state.get("template"))
    state["timeline"].append(timeline_event("报告装配器", "生成贷前尽调报告", "已完成研究计划、证据链、结论声明和证据缺口装配", "completed", "conclusion"))
    quality_patch = apply_report_quality_gate(state["report"])
    state["quality_evaluation"] = quality_patch.get("quality_evaluation")
    state["quality_score"] = quality_patch.get("quality_score")
    state["quality_passed"] = bool(quality_patch.get("quality_passed"))
    state["quality_issues"] = quality_patch.get("quality_issues") or []
    state["quality_rounds"] = int(state.get("quality_rounds") or 0) + 1
    state["timeline"].append(build_quality_timeline_event(quality_patch))
    state["report"]["timeline"] = state["timeline"]
    return {**graph_state, "research_state": state, "report": state["report"], "executed": True, "success": True}


async def _quality_driven_followups_node(graph_state: DeepResearchGraphState, config: RunnableConfig) -> DeepResearchGraphState:
    """质量门未通过时，把质量问题转化为补证任务并进入下一轮执行。"""
    state = graph_state.get("research_state") or {}
    enterprise_name = state.get("enterprise_name", graph_state.get("enterprise_name", ""))
    quality_issues = state.get("quality_issues", [])
    quality_rounds = int(state.get("quality_rounds") or 0)

    follow_up_tasks = []
    for index, issue in enumerate(quality_issues[:3], start=1):
        recommendation = issue.get("recommendation") or issue.get("message") or "补充证据或修正报告"
        dimension = issue.get("dimension") or "quality"
        severity = issue.get("severity") or "P1"
        question = f"质量复核：{recommendation}"
        task_id = stable_id("rt_quality", enterprise_name, dimension, recommendation, index)
        follow_up_tasks.append({
            "id": task_id,
            "question": question[:240],
            "purpose": f"修复质量维度 {dimension} 的问题（{severity}）",
            "category": "quality_refinement",
            "required_evidence": [recommendation[:160]],
            "priority": 70 if severity == "P0" else 60,
            "status": "pending",
            "tool_hints": ["public_search", "financial", "industry", "business", "legal"],
            "parent_task_id": None,
            "round": quality_rounds,
            "generated_by": "quality_gate",
        })

    state["follow_up_tasks"] = follow_up_tasks
    if follow_up_tasks:
        state["timeline"].append(timeline_event(
            "报告质量门",
            f"质量评分未通过，启动第{quality_rounds}轮质量驱动补证",
            f"基于{len(follow_up_tasks)}项质量问题追加follow-up task",
            "completed",
            "analysis",
        ))
        state["tasks"].extend(follow_up_tasks)
    else:
        state["timeline"].append(timeline_event(
            "报告质量门",
            "质量评分未通过但无明确修复建议",
            "按当前证据边界输出报告",
            "completed",
            "risk",
        ))
    return {**graph_state, "research_state": state}


def _route_entry(graph_state: DeepResearchGraphState) -> str:
    return "execute_round1" if graph_state.get("phase") == "execute" else "prepare_plan"


async def _route_entry_node(graph_state: DeepResearchGraphState, config: RunnableConfig) -> DeepResearchGraphState:
    return graph_state


def _route_synthesize(graph_state: DeepResearchGraphState) -> str:
    state = graph_state.get("research_state") or {}
    quality_passed = bool(state.get("quality_passed"))
    quality_rounds = int(state.get("quality_rounds") or 0)
    if quality_passed or quality_rounds >= 2:
        return "end"
    return "quality_followups"


def _route_after_followups(graph_state: DeepResearchGraphState) -> str:
    """树状递归路由：深度未达上限且补证产生了新缺口则继续深研，否则合成报告。

    受 max_depth 与 max_iterations 双重守卫约束，避免无限递归。
    """
    state = graph_state.get("research_state") or {}
    current_depth = int(state.get("current_depth", 1))
    max_depth = int(state.get("max_depth", 2))
    max_iterations = int(state.get("max_iterations") or 6)
    iteration = int(state.get("iteration") or 0)
    if (
        current_depth < max_depth
        and state.get("_followups_produced_new_gaps")
        and iteration < max_iterations
    ):
        return "plan_followups"
    return "synthesize"


def build_deep_research_graph(checkpointer=None):
    workflow = StateGraph(DeepResearchGraphState)
    workflow.add_node("route_entry", _route_entry_node)
    workflow.add_node("prepare_plan", _prepare_plan_node)
    workflow.add_node("execute_round1", _execute_round1_node)
    workflow.add_node("plan_followups", _plan_followups_node)
    workflow.add_node("execute_followups", _execute_followups_node)
    workflow.add_node("synthesize", _synthesize_node)
    workflow.add_node("quality_followups", _quality_driven_followups_node)
    workflow.set_entry_point("route_entry")
    workflow.add_conditional_edges("route_entry", _route_entry, {
        "prepare_plan": "prepare_plan",
        "execute_round1": "execute_round1",
    })
    workflow.add_edge("prepare_plan", END)
    workflow.add_edge("execute_round1", "plan_followups")
    workflow.add_edge("plan_followups", "execute_followups")
    workflow.add_conditional_edges("execute_followups", _route_after_followups, {
        "plan_followups": "plan_followups",
        "synthesize": "synthesize",
    })
    workflow.add_conditional_edges("synthesize", _route_synthesize, {
        "end": END,
        "quality_followups": "quality_followups",
    })
    workflow.add_edge("quality_followups", "execute_followups")
    return workflow.compile(checkpointer=checkpointer)


_GRAPH = None


async def get_deep_research_graph():
    global _GRAPH
    if _GRAPH is None:
        checkpointer = await get_checkpointer()
        _GRAPH = build_deep_research_graph(checkpointer=checkpointer)
    return _GRAPH


async def prepare_deep_research_plan_graph(
    enterprise_name: str,
    objective: str = "完整贷前尽调",
    max_iterations: int = 6,
    on_update: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
    parsed_intent: Optional[Dict[str, Any]] = None,
    task_id: Optional[str] = None,
) -> Dict[str, Any]:
    graph = await get_deep_research_graph()
    thread_id = task_id or stable_id("thread", enterprise_name, objective)
    result = await graph.ainvoke(
        {
            "phase": "prepare",
            "enterprise_name": enterprise_name,
            "objective": objective,
            "max_iterations": max_iterations,
            "parsed_intent": parsed_intent or {},
        },
        config={"configurable": {"thread_id": thread_id, "on_update": on_update}},
    )
    return {
        "success": bool(result.get("success")),
        "research_state": result.get("research_state", {}),
        "graph_mode": "langgraph_checkpoint",
        "thread_id": thread_id,
    }


async def execute_deep_research_plan_graph(
    state: ResearchState,
    task_id: Optional[str] = None,
    on_update: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    graph = await get_deep_research_graph()
    thread_id = task_id or stable_id("thread", state.get("enterprise_name", ""), state.get("objective", "完整贷前尽调"))
    result = await graph.ainvoke(
        {
            "phase": "execute",
            "enterprise_name": state.get("enterprise_name", ""),
            "objective": state.get("objective", "完整贷前尽调"),
            "max_iterations": int(state.get("max_iterations") or 6),
            "research_state": state,
        },
        config={"configurable": {"thread_id": thread_id, "on_update": on_update}},
    )
    return {
        "success": bool(result.get("success")),
        "research_state": result.get("research_state", {}),
        "report": result.get("report", {}),
        "graph_mode": "langgraph_checkpoint",
        "thread_id": thread_id,
    }


async def resume_deep_research_graph(
    task_id: str,
    on_update: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None,
) -> Dict[str, Any]:
    """从 checkpoint 断点续跑（execute 中途崩溃后重启恢复用）。

    传入与 prepare/execute 相同的 task_id 作为 thread_id，ainvoke(None) 让
    LangGraph 从最后保存的 checkpoint 续跑，而非重新从 entry 开始。
    """
    graph = await get_deep_research_graph()
    result = await graph.ainvoke(
        None,
        config={"configurable": {"thread_id": task_id, "on_update": on_update}},
    )
    return {
        "success": bool(result.get("success")) if result else False,
        "research_state": (result or {}).get("research_state", {}),
        "report": (result or {}).get("report", {}),
        "graph_mode": "langgraph_checkpoint_resume",
        "thread_id": task_id,
    }
