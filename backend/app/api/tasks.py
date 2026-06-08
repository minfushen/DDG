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

from app.agents.orchestrator_v2 import run_orchestrator_v2, form_conclusion, generate_report
from app.agents.state import SSEEvent

router = APIRouter()

# 任务存储（生产环境应使用数据库）
tasks: Dict[str, Dict[str, Any]] = {}
task_events: Dict[str, asyncio.Event] = {}


async def run_task_background(task_id: str):
    """后台执行任务并更新内存状态。"""
    task = tasks[task_id]

    try:
        async for event in run_orchestrator_v2(
            task_id=task_id,
            enterprise_name=task["enterprise_name"],
            template_name=task.get("template_name", "due_diligence_report_template"),
        ):
            if event.type == "state":
                tasks[task_id].update(event.data)
            elif event.type == "error":
                tasks[task_id].update({
                    "agent_state": "completed",
                    "error": event.data.get("error", "任务执行失败"),
                })

            notify_task_update(task_id)

    except Exception as e:
        tasks[task_id].update({
            "agent_state": "completed",
            "error": str(e),
        })
        notify_task_update(task_id)


def notify_task_update(task_id: str):
    """通知 SSE 订阅者任务状态已变化。"""
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
            "agent_state": task.get("agent_state"),
            "timeline": task.get("timeline", []),
            "plan": task.get("plan", []),
            "evidence": task.get("evidence", []),
            "report": task.get("report"),
            "error": task.get("error"),
            "upload_required": task.get("agent_state") == "waiting_upload",
            "full_due_diligence_context": task.get("full_due_diligence_context"),
        },
    )


class CreateTaskRequest(BaseModel):
    """创建任务请求"""
    enterprise_name: str = Field(..., description="企业名称")
    template_name: str = Field(
        default="due_diligence_report_template",
        description="尽调报告模板名称"
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


class ResumeTaskRequest(BaseModel):
    """恢复任务请求"""
    parsed_financial_data: Dict[str, Any]


async def resume_financial_task_with_uploaded_data(
    task_id: str,
    parsed_financial_data: Dict[str, Any],
):
    """基于上传财报恢复财务任务。"""
    from app.agents.sub_agents.financial_agent import run_financial_agent_with_uploaded_data
    from app.agents.crew.full_due_diligence_runner import run_full_due_diligence

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
        context_timeline_len = len(context.get("timeline", []))
        context_evidence_len = len(context.get("evidence", []))
        append_timeline(
            task_id,
            "系统",
            "恢复完整尽调综合报告生成",
            "沿用已完成的工商、司法、行业专项结果，并补齐财务专项",
            "completed",
            "action",
        )
        full_result = await run_full_due_diligence(
            enterprise_name=task["enterprise_name"],
            parsed_financial_data=parsed_financial_data,
            existing_context=context,
        )
        task["timeline"] = previous_timeline + full_result.get("timeline", [])[context_timeline_len:]
        task["evidence"] = previous_evidence + full_result.get("evidence", [])[context_evidence_len:]
        if not full_result.get("success"):
            task.update({
                "agent_state": "waiting_upload",
                "error": full_result.get("error", "完整尽调恢复失败"),
                "full_due_diligence_context": full_result.get("full_due_diligence_context", task.get("full_due_diligence_context")),
            })
            notify_task_update(task_id)
            return

        task.update({
            "agent_state": "completed",
            "report": full_result.get("report"),
            "error": None,
            "full_due_diligence_context": full_result.get("full_due_diligence_context"),
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
    task["evidence"] = task.get("evidence", []) + result.get("evidence", [])

    if not result.get("success"):
        task.update({
            "agent_state": "waiting_upload",
            "error": result.get("error", "上传财报分析失败"),
        })
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

    state = {
        "task_id": task_id,
        "enterprise_name": task["enterprise_name"],
        "template_name": task.get("template_name", "due_diligence_report_template"),
        "agent_state": task["agent_state"],
        "timeline": task["timeline"],
        "plan": task.get("plan", []),
        "evidence": task["evidence"],
        "report": task.get("report"),
        "error": task.get("error"),
        "execution_plan": None,
        "crew_result": None,
        "context": None,
        "intent": {"type": "single", "target": "financial"},
    }

    state = form_conclusion(state)
    task.update({key: state.get(key) for key in ["agent_state", "timeline", "plan", "evidence", "report", "error"]})
    notify_task_update(task_id)

    state = generate_report(state)
    task.update({key: state.get(key) for key in ["agent_state", "timeline", "plan", "evidence", "report", "error"]})
    notify_task_update(task_id)

    task["agent_state"] = "completed"
    notify_task_update(task_id)


@router.post("/tasks", response_model=CreateTaskResponse)
async def create_task(request: CreateTaskRequest):
    """创建尽调任务"""
    task_id = datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:8]

    # 创建任务记录
    tasks[task_id] = {
        "task_id": task_id,
        "enterprise_name": request.enterprise_name,
        "template_name": request.template_name,
        "agent_state": "creating_task",
        "timeline": [],
        "plan": [],
        "evidence": [],
        "report": None,
        "error": None,
        "execution_started": True,
        "full_due_diligence_context": None,
        "created_at": datetime.now().isoformat(),
    }
    task_events[task_id] = asyncio.Event()
    asyncio.create_task(run_task_background(task_id))

    return CreateTaskResponse(
        task_id=task_id,
        enterprise_name=request.enterprise_name,
        status="created",
    )


@router.get("/tasks/{task_id}/stream")
async def stream_task(task_id: str):
    """SSE流式获取任务执行状态"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    async def event_generator():
        """SSE事件生成器：只订阅状态，不重新执行任务。"""
        try:
            yield f"data: {make_task_state_event(task_id).model_dump_json()}\n\n"

            while task_id in tasks and tasks[task_id].get("agent_state") not in {"waiting_confirm", "completed"}:
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
    if task_id not in tasks:
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
    )


@router.post("/tasks/{task_id}/resume")
async def resume_task(task_id: str, request: ResumeTaskRequest):
    """上传财报解析成功后继续执行等待中的财务任务。"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]
    if task.get("agent_state") != "waiting_upload":
        raise HTTPException(status_code=400, detail="当前任务不处于等待上传状态")

    if not request.parsed_financial_data:
        raise HTTPException(status_code=400, detail="缺少解析后的财务数据")

    asyncio.create_task(resume_financial_task_with_uploaded_data(task_id, request.parsed_financial_data))
    return {"task_id": task_id, "status": "resuming"}


@router.get("/tasks/{task_id}/report")
async def get_task_report(task_id: str):
    """获取任务报告"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]

    if not task.get("report"):
        raise HTTPException(status_code=404, detail="报告尚未生成")

    return task["report"]
