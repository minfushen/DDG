# ========================================
# 任务管理API
# ========================================

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import json
import uuid
import asyncio
from datetime import datetime

from app.agents.research_engine import prepare_deep_research_plan, run_deep_research_due_diligence
from app.agents.state import SSEEvent
from app.agents.evidence import normalize_evidence_list
from app.agents.hitl import create_interrupt, get_active_interrupt, public_interrupts, resolve_interrupt
from app.agents.research_engine.tool_trace import public_tool_traces
from app.agents.sub_agents.full_report_builder import build_full_due_diligence_report
from app.api.report_exporter import export_completed_report
from app.api.task_store import load_task_snapshot, save_task_snapshot

router = APIRouter()

# 任务存储（生产环境应使用数据库）
tasks: Dict[str, Dict[str, Any]] = {}
task_events: Dict[str, asyncio.Event] = {}


def ensure_task_loaded(task_id: str) -> bool:
    if task_id in tasks:
        return True
    snapshot = load_task_snapshot(task_id)
    if not snapshot:
        return False
    tasks[task_id] = normalize_task_snapshot(snapshot)
    task_events[task_id] = asyncio.Event()
    return True


def persist_task(task_id: str) -> None:
    task = tasks.get(task_id)
    if task:
        save_task_snapshot(task)


def normalize_task_snapshot(task: Dict[str, Any]) -> Dict[str, Any]:
    defaults = {
        "timeline": [],
        "plan": [],
        "evidence": [],
        "report": None,
        "error": None,
        "research_plan": [],
        "research_claims": [],
        "research_gaps": [],
        "follow_up_tasks": [],
        "research_rounds": [],
        "tool_traces": [],
        "interrupts": [],
        "active_interrupt": None,
        "human_actions": [],
        "pending_report": None,
        "report_export_path": None,
        "report_export_hash": None,
        "report_exported_at": None,
        "planner": None,
        "sequential_thinking": None,
        "sequential_thought_loop": None,
        "sequential_plan_review": None,
        "engine_mode": "deepresearch",
        "agent_state": "completed",
        "enterprise_name": task.get("enterprise_name") or "未知企业",
    }
    for key, value in defaults.items():
        task.setdefault(key, value)
    return task


def _create_financial_upload_interrupt(task: Dict[str, Any], reason: str = "完整尽调需要补充近三年财务报表。") -> Dict[str, Any]:
    return create_interrupt(
        task,
        interrupt_type="upload_material",
        title="上传近三年财务报表",
        message=reason,
        context={
            "enterprise_name": task.get("enterprise_name"),
            "material_scope": "financial_statements",
            "accepted_formats": ["xlsx", "xls", "csv"],
        },
        required_inputs=[
            {"name": "income_statement", "label": "利润表", "required": True},
            {"name": "balance_sheet", "label": "资产负债表", "required": True},
            {"name": "cash_flow", "label": "现金流量表", "required": True},
        ],
        options=[
            {"action": "upload_and_resume", "label": "上传并继续"},
            {"action": "continue_public_pre_dd", "label": "先按公开资料预尽调"},
        ],
    )


def _should_confirm_entity(original_input: str, enterprise_name: str, input_parse: Dict[str, Any]) -> bool:
    name = (enterprise_name or "").strip()
    if not name:
        return True
    return float(input_parse.get("confidence") or 0) < 0.35


def _create_entity_confirmation_interrupt(task: Dict[str, Any]) -> Dict[str, Any]:
    input_parse = task.get("input_parse") or {}
    return create_interrupt(
        task,
        interrupt_type="confirm_entity",
        title="请确认尽调主体",
        message="系统已从你的输入中识别出拟尽调主体。请确认主体无误后再启动后续研究，避免把简称、证券简称或任务话术带入报告。",
        context={
            "original_input": task.get("original_input"),
            "recognized_name": task.get("enterprise_name"),
            "stock_code": input_parse.get("stock_code"),
            "confidence": input_parse.get("confidence"),
            "reason": input_parse.get("reason"),
        },
        options=[
            {"action": "confirm", "label": "确认主体并开始"},
            {"action": "edit_company_name", "label": "修改企业名称"},
            {"action": "continue_as_entered", "label": "按当前识别继续"},
        ],
        required_inputs=[{"name": "enterprise_name", "label": "企业名称", "required": False}],
    )


def _create_plan_confirmation_interrupt(task: Dict[str, Any], research_state: Dict[str, Any]) -> Dict[str, Any]:
    research_tasks = research_state.get("tasks", [])
    planner = research_state.get("planner") or {}
    sequential = research_state.get("sequential_thinking") or {}
    thought_loop = research_state.get("sequential_thought_loop") or {}
    return create_interrupt(
        task,
        interrupt_type="approve_plan",
        title="请确认研究计划",
        message="研究计划已生成。请先确认研究问题、证据需求和工具路线，再允许 Agent 执行外部检索和专项分析。",
        context={
            "enterprise_name": task.get("enterprise_name"),
            "objective": research_state.get("objective"),
            "planner": planner,
            "sequential_thinking": sequential,
            "sequential_thought_loop": thought_loop,
            "tasks": research_tasks,
            "task_count": len(research_tasks),
        },
        options=[
            {"action": "approve_plan", "label": "确认计划并执行"},
            {"action": "revise_plan", "label": "补充研究要求"},
            {"action": "cancel_task", "label": "暂不执行"},
        ],
        required_inputs=[{"name": "comment", "label": "补充研究要求", "required": False}],
    )


def _critical_gaps_after_follow_up(gaps: List[Dict[str, Any]], follow_up_tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not follow_up_tasks:
        return []
    critical = [gap for gap in gaps if str(gap.get("severity") or "").lower() in {"high", "medium"}]
    return critical[:5]


def _create_gap_confirmation_interrupt(task: Dict[str, Any], gaps: List[Dict[str, Any]]) -> Dict[str, Any]:
    return create_interrupt(
        task,
        interrupt_type="approve_gap",
        title="二轮补证后仍存在证据缺口",
        message="研究引擎已完成首轮检索和二轮补证，但仍有部分关键证据不足。请确认是否按公开资料边界生成报告，或先补充材料后继续。",
        context={
            "enterprise_name": task.get("enterprise_name"),
            "gaps": gaps,
            "gap_count": len(gaps),
        },
        options=[
            {"action": "approve_public_boundary", "label": "确认边界并生成报告"},
            {"action": "upload_materials", "label": "补充材料"},
            {"action": "mark_manual_review", "label": "标记人工复核"},
        ],
        required_inputs=[{"name": "comment", "label": "确认说明", "required": False}],
    )


def _minimal_research_state_from_plan(task: Dict[str, Any]) -> Dict[str, Any]:
    raw_plan = task.get("research_plan") or task.get("plan") or []
    tasks_from_plan = []
    for index, item in enumerate(raw_plan, start=1):
        tasks_from_plan.append({
            "id": item.get("id") or f"rt_manual_{index}",
            "question": item.get("question") or item.get("name") or f"人工确认研究问题 {index}",
            "purpose": item.get("purpose") or "人工确认后继续执行。",
            "category": item.get("category") or "general",
            "required_evidence": item.get("required_evidence") or [],
            "priority": item.get("priority") or 50 + index,
            "status": "pending",
            "tool_hints": item.get("tool_hints") or [],
        })
    return {
        "enterprise_name": task.get("enterprise_name"),
        "objective": "完整贷前尽调",
        "report_mode": "deepresearch_due_diligence",
        "tasks": tasks_from_plan,
        "current_task_id": None,
        "evidence": [],
        "claims": [],
        "gaps": [],
        "timeline": task.get("timeline", []),
        "iteration": 0,
        "max_iterations": task.get("max_iterations", 6),
        "errors": [],
        "report": None,
    }


def _plan_items_from_research_tasks(research_plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {
            "id": item.get("id"),
            "name": item.get("question"),
            "status": item.get("status", "pending"),
            "category": item.get("category"),
            "purpose": item.get("purpose"),
            "required_evidence": item.get("required_evidence", []),
            "tool_hints": item.get("tool_hints", []),
            "planner_source": item.get("planner_source"),
        }
        for item in research_plan
    ]


def _apply_prepare_research_state(task_id: str, research_state: Dict[str, Any], stage: str = "prepare_update") -> None:
    task = tasks[task_id]
    research_plan = research_state.get("tasks", [])
    task.update({
        "agent_state": "planning",
        "timeline": research_state.get("timeline", task.get("timeline", [])),
        "plan": _plan_items_from_research_tasks(research_plan),
        "research_state": research_state,
        "research_plan": research_plan,
        "planner": research_state.get("planner"),
        "sequential_thinking": research_state.get("sequential_thinking"),
        "sequential_thought_loop": research_state.get("sequential_thought_loop"),
        "sequential_plan_review": research_state.get("sequential_plan_review"),
        "prepare_stage": stage,
    })


def _publish_pending_report(task_id: str) -> None:
    task = tasks[task_id]
    pending_report = task.get("pending_report")
    if pending_report:
        task["report"] = pending_report
        task["pending_report"] = None
    task["agent_state"] = "completed"
    append_timeline(
        task_id,
        "Human Review",
        "人工确认证据边界",
        "已记录人工确认动作，报告按当前证据边界生成。",
        "completed",
        "conclusion",
    )


async def run_deepresearch_task_background(task_id: str):
    """Run the Plan-Execute DeepResearch engine inside the existing task system."""
    task = tasks[task_id]
    try:
        task.update({
            "agent_state": "planning",
            "timeline": task.get("timeline", []) + [{
                "id": uuid.uuid4().hex,
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "DeepResearch Engine",
                "content": "启动 Plan-Execute 研究引擎",
                "detail": "先生成研究计划，再按证据需求执行证据采集和专项分析",
                "status": "running",
                "type": "analysis",
            }],
        })
        notify_task_update(task_id)

        if not task.get("plan_approved") and not task.get("approved_research_state"):
            async def publish_prepare_update(payload: Dict[str, Any]) -> None:
                research_state = payload.get("research_state") or {}
                if not research_state:
                    return
                stage = str(payload.get("stage") or "prepare_update")
                _apply_prepare_research_state(task_id, research_state, stage=stage)
                notify_task_update(task_id)
                if stage in {"plan_task", "thought_loop_step"}:
                    # The in-memory SSE notifier is an Event, not a queue. A tiny
                    # yield keeps fast prepare updates observable as separate
                    # frontend states instead of collapsing into one final frame.
                    await asyncio.sleep(0.12)

            prepared = await prepare_deep_research_plan(
                enterprise_name=task["enterprise_name"],
                objective="完整贷前尽调",
                max_iterations=task.get("max_iterations", 6),
                on_update=publish_prepare_update,
            )
            research_state = prepared.get("research_state", {})
            research_plan = research_state.get("tasks", [])
            task.update({
                "agent_state": "waiting_human",
                "timeline": research_state.get("timeline", task.get("timeline", [])),
                "plan": _plan_items_from_research_tasks(research_plan),
                "research_state": research_state,
                "research_plan": research_plan,
                "planner": research_state.get("planner"),
                "sequential_thinking": research_state.get("sequential_thinking"),
                "sequential_thought_loop": research_state.get("sequential_thought_loop"),
                "sequential_plan_review": research_state.get("sequential_plan_review"),
                "error": None if prepared.get("success") else prepared.get("error", "研究计划生成失败"),
            })
            _create_plan_confirmation_interrupt(task, research_state)
            append_timeline(
                task_id,
                "Human Review",
                "等待确认研究计划",
                f"已生成{len(research_plan)}个研究问题，确认后才会执行工具调用。",
                "running",
                "analysis",
            )
            notify_task_update(task_id)
            return

        result = await run_deep_research_due_diligence(
            enterprise_name=task["enterprise_name"],
            objective="完整贷前尽调",
            max_iterations=task.get("max_iterations", 6),
            approved_state=task.get("approved_research_state") or task.get("research_state"),
        )
        research_state = result.get("research_state", {})
        report = result.get("report") or {}
        research_plan = report.get("research_plan") or research_state.get("tasks", [])
        evidence = report.get("evidence") or research_state.get("evidence", [])
        tool_traces = research_state.get("tool_traces", []) or report.get("tool_traces", []) or []
        claims = report.get("claims") or research_state.get("claims", [])
        gaps = report.get("gaps") or research_state.get("gaps", [])
        follow_up_tasks = research_state.get("follow_up_tasks", [])

        task.update({
            "agent_state": "completed" if result.get("success") else "completed",
            "timeline": report.get("timeline") or research_state.get("timeline", task.get("timeline", [])),
            "plan": [
                {
                    "id": item.get("id"),
                    "name": item.get("question"),
                    "status": item.get("status", "pending"),
                    "category": item.get("category"),
                    "purpose": item.get("purpose"),
                    "required_evidence": item.get("required_evidence", []),
                    "tool_hints": item.get("tool_hints", []),
                    "evidence_ids": item.get("evidence_ids", []),
                    "claim_ids": item.get("claim_ids", []),
                    "planner_source": item.get("planner_source"),
                    "sequential_gap_notes": item.get("sequential_gap_notes"),
                    "round": item.get("round"),
                    "parent_task_id": item.get("parent_task_id"),
                    "generated_by": item.get("generated_by"),
                    "search_query": item.get("search_query"),
                }
                for item in research_plan
            ],
            "evidence": evidence,
            "tool_traces": tool_traces,
            "report": report,
            "error": None if result.get("success") else result.get("error", "DeepResearch执行失败"),
            "research_state": research_state,
            "research_plan": research_plan,
            "research_claims": claims,
            "research_gaps": gaps,
            "planner": research_state.get("planner"),
            "sequential_thinking": research_state.get("sequential_thinking"),
            "sequential_plan_review": research_state.get("sequential_plan_review"),
            "follow_up_tasks": follow_up_tasks,
            "research_rounds": research_state.get("research_rounds", []),
        })
        critical_gaps = _critical_gaps_after_follow_up(gaps, follow_up_tasks)
        if critical_gaps:
            task["pending_report"] = report
            task["report"] = None
            _create_gap_confirmation_interrupt(task, critical_gaps)
            append_timeline(
                task_id,
                "Human Review",
                "等待人工确认证据缺口",
                f"二轮补证后仍有{len(critical_gaps)}个中高优先级证据缺口，需要确认报告边界。",
                "running",
                "risk",
            )
        notify_task_update(task_id)
    except Exception as e:
        task.update({
            "agent_state": "completed",
            "error": str(e),
            "timeline": task.get("timeline", []) + [{
                "id": uuid.uuid4().hex,
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "DeepResearch Engine",
                "content": "DeepResearch 执行失败",
                "detail": str(e),
                "status": "completed",
                "type": "risk",
            }],
        })
        notify_task_update(task_id)


def schedule_task_background(task_id: str, delay_seconds: float = 0.5):
    """Schedule execution after the create-task response has flushed."""
    loop = asyncio.get_running_loop()
    loop.call_later(delay_seconds, lambda: asyncio.create_task(run_deepresearch_task_background(task_id)))


def notify_task_update(task_id: str):
    """通知 SSE 订阅者任务状态已变化。"""
    task = tasks.get(task_id)
    if task:
        export_completed_report(task)
    persist_task(task_id)
    if task_id in task_events:
        task_events[task_id].set()
        task_events[task_id] = asyncio.Event()


def append_timeline(task_id: str, agent: str, content: str, detail: str = "", status: str = "completed", event_type: str = "action"):
    """追加一条任务时间轴并通知订阅者。"""
    tasks[task_id]["timeline"] = tasks[task_id].get("timeline", []) + [{
        "id": uuid.uuid4().hex,
        "time": datetime.now().strftime("%H:%M:%S"),
        "agent": agent,
        "content": content,
        "detail": detail,
        "status": status,
        "type": event_type,
    }]
    notify_task_update(task_id)


def make_task_state_event(task_id: str) -> SSEEvent:
    """把当前任务状态包装为 SSE state 事件。"""
    task = tasks[task_id]
    return SSEEvent(
        type="state",
        data={
            "enterprise_name": task.get("enterprise_name"),
            "original_input": task.get("original_input"),
            "input_parse": task.get("input_parse"),
            "agent_state": task.get("agent_state"),
            "timeline": task.get("timeline", []),
            "plan": task.get("plan", []),
            "evidence": task.get("evidence", []),
            "report": task.get("report"),
            "error": task.get("error"),
            "upload_required": task.get("agent_state") in {"waiting_upload", "waiting_human"} and (get_active_interrupt(task) or {}).get("type") == "upload_material",
            "active_interrupt": get_active_interrupt(task),
            "interrupts": public_interrupts(task),
            "human_actions": task.get("human_actions", []),
            "full_due_diligence_context": task.get("full_due_diligence_context"),
            "engine_mode": task.get("engine_mode"),
            "research_plan": task.get("research_plan", []),
            "research_claims": task.get("research_claims", []),
            "research_gaps": task.get("research_gaps", []),
            "planner": task.get("planner"),
            "sequential_thinking": task.get("sequential_thinking"),
            "sequential_thought_loop": task.get("sequential_thought_loop"),
            "sequential_plan_review": task.get("sequential_plan_review"),
            "prepare_stage": task.get("prepare_stage"),
            "follow_up_tasks": task.get("follow_up_tasks", []),
            "research_rounds": task.get("research_rounds", []),
            "tool_traces": public_tool_traces(task.get("tool_traces", [])),
            "report_export_path": task.get("report_export_path"),
            "quality_evaluation": (task.get("report") or task.get("pending_report") or {}).get("quality_evaluation"),
            "quality_score": (task.get("report") or task.get("pending_report") or {}).get("quality_score"),
            "quality_passed": (task.get("report") or task.get("pending_report") or {}).get("quality_passed"),
            "quality_issues": (task.get("report") or task.get("pending_report") or {}).get("quality_issues", []),
        },
    )


class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    enterprise_name: str = Field(..., description="企业名称")
    template_name: str = Field(
        default="due_diligence_report_template",
        description="尽调报告模板名称"
    )
    engine_mode: str = Field(
        default="deepresearch",
        description="执行引擎：仅支持 deepresearch"
    )


class CreateTaskResponse(BaseModel):
    """创建任务响应"""
    task_id: str
    enterprise_name: str
    status: str


class TaskStatusResponse(BaseModel):
    """任务状态响应"""
    task_id: str
    enterprise_name: str
    agent_state: str
    timeline: List[dict]
    plan: List[dict]
    evidence: List[dict]
    report: Optional[dict]
    engine_mode: Optional[str] = None
    research_plan: List[dict] = []
    research_claims: List[dict] = []
    research_gaps: List[dict] = []
    planner: Optional[dict] = None
    sequential_thinking: Optional[dict] = None
    sequential_thought_loop: Optional[dict] = None
    sequential_plan_review: Optional[dict] = None
    follow_up_tasks: List[dict] = []
    research_rounds: List[dict] = []
    active_interrupt: Optional[dict] = None
    interrupts: List[dict] = []
    human_actions: List[dict] = []
    tool_traces: List[dict] = []
    report_export_path: Optional[str] = None
    quality_evaluation: Optional[dict] = None
    quality_score: Optional[int] = None
    quality_passed: Optional[bool] = None
    quality_issues: List[dict] = []
    prepare_stage: Optional[str] = None


class ResumeTaskRequest(BaseModel):
    """恢复任务请求"""
    parsed_financial_data: Dict[str, Any]


class ResumeInterruptRequest(BaseModel):
    """人工中断恢复请求"""
    resolution: Dict[str, Any] = Field(default_factory=dict)


async def resume_financial_task_with_uploaded_data(
    task_id: str,
    parsed_financial_data: Dict[str, Any],
):
    """基于上传财报恢复财务任务。"""
    from app.agents.sub_agents.financial_agent import run_financial_agent_with_uploaded_data

    task = tasks[task_id]
    task.update({
        "agent_state": "calling_financial",
        "error": None,
    })
    append_timeline(
        task_id,
        "系统",
        "已接收上传财报，继续财务分析",
        "开始校验表格完整性和重点科目覆盖情况",
    )
    notify_task_update(task_id)

    append_timeline(
        task_id,
        "财务Agent",
        "校验财报结构",
        "确认利润表、资产负债表、现金流量表均已解析完成",
        "completed",
        "discovery",
    )

    append_timeline(
        task_id,
        "财务Agent",
        "标准化重点科目",
        "对齐年度列，提取营收、利润、资产、负债、权益及现金流科目",
        "completed",
        "analysis",
    )

    if task.get("full_due_diligence_context"):
        previous_timeline = task.get("timeline", [])
        previous_evidence = task.get("evidence", [])
        context = task.get("full_due_diligence_context") or {}
        append_timeline(
            task_id,
            "系统",
            "恢复完整尽调综合报告生成",
            "沿用已完成的工商、司法、行业专项结果，并补齐财务专项",
            "completed",
            "action",
        )
        result = await run_financial_agent_with_uploaded_data(
            enterprise_name=task["enterprise_name"],
            parsed_financial_data=parsed_financial_data,
        )
        task["timeline"] = previous_timeline + result.get("timeline", [])
        financial_evidence = normalize_evidence_list(result.get("evidence", []), agent="financial")
        task["evidence"] = previous_evidence + financial_evidence
        if not result.get("success") or not result.get("financial_analysis_report"):
            task.update({
                "agent_state": "waiting_human",
                "error": result.get("error", "上传财报分析未完成"),
                "full_due_diligence_context": context,
            })
            _create_financial_upload_interrupt(task, reason="上传财报分析未完成，请补充或重新上传三大表文件。")
            notify_task_update(task_id)
            return

        sub_reports = dict(context.get("sub_reports") or {})
        sub_reports["financial"] = result["financial_analysis_report"]
        merged_evidence = normalize_evidence_list(context.get("evidence", []), agent="research") + financial_evidence
        report = build_full_due_diligence_report(
            enterprise_name=task["enterprise_name"],
            sub_reports=sub_reports,
            evidence=merged_evidence,
            pending_upload=False,
            report_mode="financial_enhanced_dd",
            financial_data_status="complete",
        )
        updated_context = {
            **context,
            "sub_reports": sub_reports,
            "evidence": merged_evidence,
            "report": report,
            "pending_upload": False,
        }

        task.update({
            "agent_state": "completed",
            "report": report,
            "error": None,
            "full_due_diligence_context": updated_context,
            "timeline": task.get("timeline", []) + [{
                "id": uuid.uuid4().hex,
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "系统",
                "content": "完整尽调报告生成完成",
                "detail": "已补齐财务专项并形成统一授信审查意见",
                "status": "completed",
                "type": "action",
            }],
        })
        notify_task_update(task_id)
        return

    result = await run_financial_agent_with_uploaded_data(
        enterprise_name=task["enterprise_name"],
        parsed_financial_data=parsed_financial_data,
    )

    task["timeline"] = task.get("timeline", []) + result.get("timeline", [])
    task["evidence"] = task.get("evidence", []) + normalize_evidence_list(result.get("evidence", []), agent="financial")

    if not result.get("success"):
        task.update({
            "agent_state": "waiting_human",
            "error": result.get("error", "上传财报分析失败"),
        })
        _create_financial_upload_interrupt(task, reason="上传财报分析失败，请检查文件后重新上传。")
        notify_task_update(task_id)
        return

    if result.get("financial_analysis_report"):
        append_timeline(
            task_id,
            "财务Agent",
            "生成银行财务分析专报",
            "按资产、负债、权益、利润、现金流和财务指标章节组织结论",
            "completed",
            "conclusion",
        )
        task.update({
            "agent_state": "completed",
            "report": result["financial_analysis_report"],
            "error": None,
            "timeline": task.get("timeline", []) + [{
                "id": uuid.uuid4().hex,
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "系统",
                "content": "企业客户财务状况分析报告生成完成",
                "detail": "已按银行财务分析模板生成正式报告结构",
                "status": "completed",
                "type": "action",
            }],
        })
        notify_task_update(task_id)
        return

    task.update({
        "agent_state": "waiting_human",
        "error": "上传财报分析未返回可展示报告",
    })
    _create_financial_upload_interrupt(task, reason="上传财报分析未返回可展示报告，请检查文件后重新上传。")
    notify_task_update(task_id)


@router.post("/tasks", response_model=CreateTaskResponse)
async def create_task(request: CreateTaskRequest):
    """创建尽调任务"""
    from app.agents.planning.intent_extractor import fast_extract_user_intent

    task_id = datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:8]
    input_parse = fast_extract_user_intent(request.enterprise_name)
    enterprise_name = input_parse["enterprise_name"]

    engine_mode = "deepresearch"

    # 创建任务记录
    tasks[task_id] = {
        "task_id": task_id,
        "enterprise_name": enterprise_name,
        "original_input": request.enterprise_name,
        "input_parse": input_parse,
        "template_name": request.template_name,
        "engine_mode": engine_mode,
        "agent_state": "creating_task",
        "timeline": [],
        "plan": [],
        "evidence": [],
        "report": None,
        "error": None,
        "execution_started": True,
        "full_due_diligence_context": None,
        "research_state": None,
        "research_plan": [],
        "research_claims": [],
        "research_gaps": [],
        "follow_up_tasks": [],
        "research_rounds": [],
        "tool_traces": [],
        "interrupts": [],
        "active_interrupt": None,
        "human_actions": [],
        "pending_report": None,
        "report_export_path": None,
        "report_export_hash": None,
        "report_exported_at": None,
        "planner": None,
        "sequential_thinking": None,
        "sequential_thought_loop": None,
        "sequential_plan_review": None,
        "created_at": datetime.now().isoformat(),
    }
    task_events[task_id] = asyncio.Event()
    persist_task(task_id)
    if _should_confirm_entity(request.enterprise_name, enterprise_name, input_parse):
        _create_entity_confirmation_interrupt(tasks[task_id])
        append_timeline(
            task_id,
            "Human Review",
            "等待确认尽调主体",
            f"识别主体：{enterprise_name}。确认后再启动完整研究流程。",
            "running",
            "action",
        )
    else:
        schedule_task_background(task_id)

    return CreateTaskResponse(
        task_id=task_id,
        enterprise_name=enterprise_name,
        status="created",
    )


@router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    """SSE流式获取任务执行状态"""
    if not ensure_task_loaded(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_generator():
        """SSE事件生成器：只订阅状态，不重新执行任务。"""
        try:
            yield f"data: {make_task_state_event(task_id).model_dump_json()}\n\n"

            while task_id in tasks and tasks[task_id].get("agent_state") not in {"waiting_confirm", "waiting_human", "completed"}:
                event = task_events[task_id]
                await event.wait()
                yield f"data: {make_task_state_event(task_id).model_dump_json()}\n\n"

        except Exception as e:
            # 发送错误事件
            yield f"data: {SSEEvent(type='error', data={'error': str(e)}).model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Transfer-Encoding": "chunked",
        },
    )


@router.get("/tasks/{task_id}", response_model=TaskStatusResponse)
async def get_task(task_id: str):
    """获取任务状态"""
    if not ensure_task_loaded(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]

    return TaskStatusResponse(
        task_id=task["task_id"],
        enterprise_name=task["enterprise_name"],
        agent_state=task["agent_state"],
        timeline=task["timeline"],
        plan=task["plan"],
        evidence=task["evidence"],
        report=task.get("report"),
        engine_mode=task.get("engine_mode"),
        research_plan=task.get("research_plan", []),
        research_claims=task.get("research_claims", []),
        research_gaps=task.get("research_gaps", []),
        planner=task.get("planner"),
        sequential_thinking=task.get("sequential_thinking"),
        sequential_thought_loop=task.get("sequential_thought_loop"),
        sequential_plan_review=task.get("sequential_plan_review"),
        follow_up_tasks=task.get("follow_up_tasks", []),
        research_rounds=task.get("research_rounds", []),
        tool_traces=public_tool_traces(task.get("tool_traces", [])),
        report_export_path=task.get("report_export_path"),
        active_interrupt=get_active_interrupt(task),
        interrupts=public_interrupts(task),
        human_actions=task.get("human_actions", []),
    )


@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str, request: ResumeTaskRequest):
    """上传财报解析成功后继续执行等待中的财务任务。"""
    if not ensure_task_loaded(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    active_interrupt = get_active_interrupt(task)
    if task.get("agent_state") not in {"waiting_upload", "waiting_human"} or (active_interrupt and active_interrupt.get("type") != "upload_material"):
        raise HTTPException(status_code=400, detail="当前任务不处于等待上传状态")

    if not request.parsed_financial_data:
        raise HTTPException(status_code=400, detail="缺少解析后的财务数据")

    if active_interrupt and active_interrupt.get("type") == "upload_material":
        resolve_interrupt(task, active_interrupt["interrupt_id"], {"action": "upload_and_resume", "parsed_financial_data": True})
        persist_task(task_id)
    asyncio.create_task(resume_financial_task_with_uploaded_data(task_id, request.parsed_financial_data))
    return {"task_id": task_id, "status": "resuming"}


@router.get("/tasks/{task_id}/interrupts")
async def get_task_interrupts(task_id: str):
    """获取任务的人机协同中断列表。"""
    if not ensure_task_loaded(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")
    task = tasks[task_id]
    return {
        "task_id": task_id,
        "active_interrupt": get_active_interrupt(task),
        "interrupts": public_interrupts(task),
        "human_actions": task.get("human_actions", []),
    }


@router.post("/tasks/{task_id}/interrupts/{interrupt_id}/resume")
async def resume_interrupt(task_id: str, interrupt_id: str, request: ResumeInterruptRequest):
    """解决一个人机协同中断并恢复任务。"""
    if not ensure_task_loaded(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    active = get_active_interrupt(task)
    if not active and interrupt_id == "active" and task.get("agent_state") == "waiting_human":
        if not (task.get("research_state") or {}).get("tasks"):
            task["research_state"] = _minimal_research_state_from_plan(task)
        active = _create_plan_confirmation_interrupt(task, task.get("research_state") or {})
    if not active or (interrupt_id != "active" and active.get("interrupt_id") != interrupt_id):
        raise HTTPException(status_code=400, detail="当前没有匹配的待处理人工中断")

    resolution = request.resolution or {}
    action = resolution.get("action") or "confirm"
    interrupt_type = active.get("type")

    try:
        resolve_interrupt(task, active["interrupt_id"], resolution)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if interrupt_type == "confirm_entity":
        company_name = str(resolution.get("enterprise_name") or "").strip()
        if action == "edit_company_name" and company_name:
            task["enterprise_name"] = company_name
            task.setdefault("input_parse", {})["enterprise_name"] = company_name
        append_timeline(
            task_id,
            "Human Review",
            "已确认尽调主体",
            f"后续研究主体：{task.get('enterprise_name')}",
            "completed",
            "action",
        )
        task["agent_state"] = "planning"
        schedule_task_background(task_id, delay_seconds=0.1)
        notify_task_update(task_id)
        return {"task_id": task_id, "status": "resuming", "action": action}

    if interrupt_type == "approve_plan":
        if action == "cancel_task":
            task["agent_state"] = "completed"
            task["error"] = "用户暂不执行研究计划"
            append_timeline(task_id, "Human Review", "暂停执行研究计划", "用户选择暂不执行外部检索和专项分析。", "completed", "action")
            notify_task_update(task_id)
            return {"task_id": task_id, "status": "cancelled", "action": action}

        research_state = task.get("research_state") or _minimal_research_state_from_plan(task)
        comment = str(resolution.get("comment") or "").strip()
        if action == "revise_plan" and comment:
            research_state["objective"] = f"{research_state.get('objective') or '完整贷前尽调'}；人工补充要求：{comment}"
            research_state.setdefault("timeline", []).append({
                "id": uuid.uuid4().hex,
                "time": datetime.now().strftime("%H:%M:%S"),
                "agent": "Human Review",
                "content": "补充研究要求",
                "detail": comment[:240],
                "status": "completed",
                "type": "analysis",
            })
        task["plan_approved"] = True
        task["approved_research_state"] = research_state
        task["agent_state"] = "calling_tools"
        append_timeline(task_id, "Human Review", "已确认研究计划", "开始按已确认的研究问题执行工商、财务、司法、行业、内部知识库和公开资料采集。", "completed", "action")
        schedule_task_background(task_id, delay_seconds=0.1)
        notify_task_update(task_id)
        return {"task_id": task_id, "status": "resuming", "action": action}

    if interrupt_type == "upload_material":
        if action == "continue_public_pre_dd":
            task["agent_state"] = "completed" if task.get("report") else "forming_conclusion"
            append_timeline(task_id, "Human Review", "确认按公开资料预尽调", "未上传财报，报告将保留数据边界和待补充材料清单。", "completed", "action")
            if task.get("pending_report"):
                _publish_pending_report(task_id)
            notify_task_update(task_id)
            return {"task_id": task_id, "status": "continued_public_pre_dd"}
        task["agent_state"] = "waiting_human"
        notify_task_update(task_id)
        return {"task_id": task_id, "status": "waiting_upload"}

    if interrupt_type == "approve_gap":
        if action == "upload_materials":
            _create_financial_upload_interrupt(task, reason="请补充能够覆盖二轮补证缺口的财务、合同、公告或审查材料。")
            notify_task_update(task_id)
            return {"task_id": task_id, "status": "waiting_upload"}
        _publish_pending_report(task_id)
        if action == "mark_manual_review" and task.get("report"):
            task["report"]["manual_review_required"] = True
            task["report"]["manual_review_comment"] = resolution.get("comment") or "二轮补证后仍存在证据缺口，需人工复核。"
        notify_task_update(task_id)
        return {"task_id": task_id, "status": "completed", "action": action}

    task["agent_state"] = "completed" if task.get("report") else "planning"
    notify_task_update(task_id)
    return {"task_id": task_id, "status": "resumed", "action": action}


@router.get("/tasks/{task_id}/report")
async def get_task_report(task_id: str):
    """获取任务报告"""
    if not ensure_task_loaded(task_id):
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]

    if not task.get("report"):
        raise HTTPException(status_code=404, detail="报告尚未生成")

    report = dict(task["report"])
    if task.get("tool_traces") and not report.get("tool_traces"):
        report["tool_traces"] = public_tool_traces(task.get("tool_traces", []))
    return report
