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

from app.agents.orchestrator_v2 import run_orchestrator_v2
from app.agents.state import SSEEvent

router = APIRouter()

# 任务存储（生产环境应使用数据库）
tasks: Dict[str, Dict[str, Any]] = {}


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
        "created_at": datetime.now().isoformat(),
    }

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

    task = tasks[task_id]

    async def event_generator():
        """SSE事件生成器"""
        try:
            async for event in run_orchestrator_v2(
                task_id=task_id,
                enterprise_name=task["enterprise_name"],
                template_name=task.get("template_name", "due_diligence_report_template"),
            ):
                # 更新任务状态
                if event.type == "state":
                    tasks[task_id].update(event.data)

                # 发送SSE事件
                yield f"data: {event.model_dump_json()}\n\n"

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


@router.get("/tasks/{task_id}/report")
async def get_task_report(task_id: str):
    """获取任务报告"""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="任务不存在")

    task = tasks[task_id]

    if not task.get("report"):
        raise HTTPException(status_code=404, detail="报告尚未生成")

    return task["report"]
