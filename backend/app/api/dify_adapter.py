# ========================================
# Dify 适配层 — 统一入口
# 为 Dify 工作流编排提供专用的 API 端点
# 设计原则：Dify 只通过本文件交互，不直接调用内部 API
# ========================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.search_service import get_search_service
from app.services.business_service import get_business_service
from app.services.legal_service import get_legal_service
from app.services.financial_service import get_financial_service
from app.services.industry_service import get_industry_service
from app.services.due_diligence_service import get_due_diligence_service

router = APIRouter(prefix="/dify")
logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# Request / Response schemas
# ═══════════════════════════════════════════════════════════════════

class DifyInvokeRequest(BaseModel):
    """Dify 统一调用请求。"""
    action: str = Field(
        ...,
        description="操作类型：create_due_diligence | query_tool | get_report | get_status | get_interrupts | resume_interrupt | simple_qa"
    )
    task_id: Optional[str] = Field(default=None, description="任务ID")
    enterprise_name: Optional[str] = Field(default=None, description="企业名称")
    template_name: Optional[str] = Field(default="full", description="尽调模板")
    tool_name: Optional[str] = Field(default=None, description="工具名称（searxng/business/legal/financial/industry）")
    query: Optional[str] = Field(default=None, description="查询关键词")
    category: Optional[str] = Field(default="enterprise", description="查询类别")
    inputs: Optional[Dict[str, Any]] = Field(default=None, description="用户输入（HITL恢复用）")
    interrupt_id: Optional[str] = Field(default=None, description="中断ID")
    action_choice: Optional[str] = Field(default=None, description="用户选择的动作")
    max_results: int = Field(default=8, ge=1, le=50, description="返回结果数量")


class DifyInvokeResponse(BaseModel):
    """Dify 统一调用响应。"""
    success: bool = Field(default=True)
    data: Dict[str, Any] = Field(default_factory=dict)
    message: Optional[str] = Field(default=None, description="人类可读的状态说明")
    next_action: Optional[str] = Field(default=None, description="提示 Dify 下一步该做什么")
    error: Optional[str] = Field(default=None)


class DifyStatusResponse(BaseModel):
    """Dify 任务状态查询响应。"""
    task_id: str
    status: str  # running | completed | waiting_human | failed | created
    agent_state: str
    progress: str
    next_expected: str
    has_interrupt: bool
    interrupt_type: Optional[str] = None
    interrupt_title: Optional[str] = None
    report_ready: bool
    error: Optional[str] = None


class DifyReportResponse(BaseModel):
    """Dify 报告获取响应（简化版）。"""
    task_id: str
    enterprise_name: str
    report_status: str
    executive_summary: str
    sections: List[Dict[str, Any]]
    key_metrics: Dict[str, Any]
    risk_level: str
    risk_score: int
    diagnostics: List[Dict[str, Any]]
    evidence_summary: List[str]
    data_gaps: List[str]
    report_url: Optional[str] = None


class DifyInterruptsResponse(BaseModel):
    """Dify 中断查询响应。"""
    task_id: str
    has_interrupt: bool
    interrupts: List[Dict[str, Any]]
    active: Optional[Dict[str, Any]] = None


class DifyToolResponse(BaseModel):
    """Dify 工具直接调用响应。"""
    success: bool
    tool_name: str
    data: Dict[str, Any]
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════
# 统一入口：/api/v1/dify/invoke
# ═══════════════════════════════════════════════════════════════════

@router.post("/invoke", response_model=DifyInvokeResponse, tags=["dify"])
async def dify_invoke(request: DifyInvokeRequest):
    """Dify 统一入口 — 所有操作通过 action 路由。

    Dify 的 HTTP 工具节点只需配置这一个端点，
    通过不同的 action 参数实现不同的功能。

    示例：
        {"action": "create_due_diligence", "enterprise_name": "华为技术有限公司"}
        {"action": "get_status", "task_id": "20240101120000abc123"}
        {"action": "query_tool", "tool_name": "searxng", "query": "华为 年报"}
    """
    action = request.action
    logger.info("[DifyAdapter] action=%s task_id=%s", action, request.task_id)

    try:
        if action == "create_due_diligence":
            return await _handle_create_due_diligence(request)
        elif action == "get_status":
            return await _handle_get_status(request)
        elif action == "get_report":
            return await _handle_get_report(request)
        elif action == "get_interrupts":
            return await _handle_get_interrupts(request)
        elif action == "resume_interrupt":
            return await _handle_resume_interrupt(request)
        elif action == "query_tool":
            return await _handle_query_tool(request)
        elif action == "simple_qa":
            return await _handle_simple_qa(request)
        else:
            return DifyInvokeResponse(
                success=False,
                error=f"未知的 action: {action}。支持的 action: create_due_diligence, get_status, get_report, get_interrupts, resume_interrupt, query_tool, simple_qa"
            )
    except Exception as exc:
        logger.error("[DifyAdapter] 处理失败: %s", exc, exc_info=True)
        return DifyInvokeResponse(
            success=False,
            error=f"服务器内部错误: {str(exc)}"
        )


# ─── 处理器 ───────────────────────────────────────────────────────

async def _handle_create_due_diligence(request: DifyInvokeRequest) -> DifyInvokeResponse:
    """创建尽调任务。"""
    if not request.enterprise_name:
        return DifyInvokeResponse(success=False, error="enterprise_name 不能为空")

    dd_service = get_due_diligence_service()
    result = await dd_service.create_task(
        enterprise_name=request.enterprise_name,
        template_name=request.template_name or "full",
    )

    task_id = result["task_id"]
    # 自动启动执行
    await dd_service.start_execution(task_id)

    return DifyInvokeResponse(
        success=True,
        data={"task_id": task_id, "enterprise_name": result["enterprise_name"], "status": "running"},
        message=f"已创建尽调任务: {result['enterprise_name']}。任务ID: {task_id}",
        next_action="poll_status",
    )


async def _handle_get_status(request: DifyInvokeRequest) -> DifyInvokeResponse:
    """查询任务状态。"""
    if not request.task_id:
        return DifyInvokeResponse(success=False, error="task_id 不能为空")

    dd_service = get_due_diligence_service()
    status = await dd_service.get_status(request.task_id)

    if not status.get("success", True):
        return DifyInvokeResponse(success=False, error=status.get("error"))

    agent_state = status.get("agent_state", "")

    # 根据状态决定 next_action
    next_action = "poll_status"
    if agent_state == "completed":
        next_action = "show_report"
    elif agent_state in ("waiting_human", "waiting_confirm"):
        next_action = "ask_human"
    elif agent_state == "failed":
        next_action = "handle_error"

    return DifyInvokeResponse(
        success=True,
        data=status,
        message=status.get("next_expected", ""),
        next_action=next_action,
    )


async def _handle_get_report(request: DifyInvokeRequest) -> DifyInvokeResponse:
    """获取任务报告。"""
    if not request.task_id:
        return DifyInvokeResponse(success=False, error="task_id 不能为空")

    dd_service = get_due_diligence_service()
    report = await dd_service.get_report(request.task_id)

    if not report.get("success", True):
        return DifyInvokeResponse(success=False, error=report.get("error"))

    return DifyInvokeResponse(
        success=True,
        data=report,
        message="报告已生成",
        next_action="end",
    )


async def _handle_get_interrupts(request: DifyInvokeRequest) -> DifyInvokeResponse:
    """查询任务中断。"""
    if not request.task_id:
        return DifyInvokeResponse(success=False, error="task_id 不能为空")

    dd_service = get_due_diligence_service()
    interrupts = await dd_service.get_interrupts(request.task_id)

    if not interrupts.get("success", True):
        return DifyInvokeResponse(success=False, error=interrupts.get("error"))

    return DifyInvokeResponse(
        success=True,
        data=interrupts,
        message="请查看中断信息并选择操作",
        next_action="ask_human" if interrupts.get("has_interrupt") else "poll_status",
    )


async def _handle_resume_interrupt(request: DifyInvokeRequest) -> DifyInvokeResponse:
    """恢复中断任务。"""
    if not request.task_id:
        return DifyInvokeResponse(success=False, error="task_id 不能为空")

    dd_service = get_due_diligence_service()
    result = await dd_service.resume_interrupt(
        task_id=request.task_id,
        interrupt_id=request.interrupt_id or "",
        action=request.action_choice or "",
        inputs=request.inputs or {},
    )

    return DifyInvokeResponse(
        success=result.get("success", True),
        data=result,
        message="任务已恢复",
        next_action="poll_status",
    )


async def _handle_query_tool(request: DifyInvokeRequest) -> DifyInvokeResponse:
    """直接调用工具。"""
    tool_name = request.tool_name
    query = request.query or ""

    if not tool_name:
        return DifyInvokeResponse(success=False, error="tool_name 不能为空")

    try:
        if tool_name == "searxng":
            service = get_search_service()
            result = await service.search(query=query, max_results=request.max_results)
        elif tool_name == "business":
            service = get_business_service()
            result = await service.query(query)
        elif tool_name == "legal":
            service = get_legal_service()
            result = await service.query(query)
        elif tool_name == "financial":
            service = get_financial_service()
            result = await service.analyze_summary(query)
        elif tool_name == "industry":
            service = get_industry_service()
            result = await service.analyze_summary(query)
        else:
            return DifyInvokeResponse(success=False, error=f"未知的工具: {tool_name}")

        return DifyInvokeResponse(
            success=True,
            data=result,
            message=f"工具 {tool_name} 调用完成",
            next_action="end",
        )
    except Exception as exc:
        logger.warning("[DifyAdapter] 工具调用失败: %s", exc)
        return DifyInvokeResponse(
            success=False,
            error=f"工具调用失败: {str(exc)}"
        )


async def _handle_simple_qa(request: DifyInvokeRequest) -> DifyInvokeResponse:
    """简单问答 — 直接返回知识库或搜索结果（不走尽调引擎）。"""
    query = request.query or ""
    if not query:
        return DifyInvokeResponse(success=False, error="query 不能为空")

    # 先搜索，再返回结果
    service = get_search_service()
    result = await service.search(query=query, max_results=5)

    return DifyInvokeResponse(
        success=True,
        data=result,
        message="简单问答已处理，请结合搜索结果由 LLM 生成回答",
        next_action="end",
    )


# ═══════════════════════════════════════════════════════════════════
# 辅助端点：状态查询、报告获取、中断处理（供 Dify 直接使用）
# ═══════════════════════════════════════════════════════════════════

@router.get("/status/{task_id}", response_model=DifyStatusResponse, tags=["dify"])
async def dify_status(task_id: str):
    """Dify 状态查询 — 简化版，返回标准化状态。"""
    dd_service = get_due_diligence_service()
    status = await dd_service.get_status(task_id)

    if not status.get("success", True):
        raise HTTPException(status_code=404, detail=status.get("error", "任务不存在"))

    return DifyStatusResponse(
        task_id=task_id,
        status=status.get("status", "unknown"),
        agent_state=status.get("agent_state", "unknown"),
        progress=status.get("progress", "0/0"),
        next_expected=status.get("next_expected", ""),
        has_interrupt=status.get("has_interrupt", False),
        interrupt_type=status.get("interrupt_info", {}).get("type") if status.get("interrupt_info") else None,
        interrupt_title=status.get("interrupt_info", {}).get("title") if status.get("interrupt_info") else None,
        report_ready=status.get("report_ready", False),
        error=status.get("error"),
    )


@router.get("/report/{task_id}", response_model=DifyReportResponse, tags=["dify"])
async def dify_report(task_id: str):
    """Dify 报告获取 — 简化版，返回结构化报告。"""
    dd_service = get_due_diligence_service()
    report = await dd_service.get_report(task_id)

    if not report.get("success", True):
        raise HTTPException(status_code=404, detail=report.get("error", "报告不存在"))

    return DifyReportResponse(
        task_id=task_id,
        enterprise_name=report.get("enterprise_name", ""),
        report_status=report.get("report_status", ""),
        executive_summary=report.get("executive_summary", ""),
        sections=report.get("sections", []),
        key_metrics=report.get("key_metrics", {}),
        risk_level=report.get("risk_level", "未知"),
        risk_score=report.get("risk_score", 0),
        diagnostics=report.get("diagnostics", []),
        evidence_summary=report.get("evidence_summary", []),
        data_gaps=report.get("data_gaps", []),
        report_url=report.get("report_url"),
    )


@router.get("/interrupts/{task_id}", response_model=DifyInterruptsResponse, tags=["dify"])
async def dify_interrupts(task_id: str):
    """Dify 中断查询。"""
    dd_service = get_due_diligence_service()
    interrupts = await dd_service.get_interrupts(task_id)

    if not interrupts.get("success", True):
        raise HTTPException(status_code=404, detail=interrupts.get("error", "任务不存在"))

    return DifyInterruptsResponse(
        task_id=task_id,
        has_interrupt=interrupts.get("has_interrupt", False),
        interrupts=interrupts.get("interrupts", []),
        active=interrupts.get("active"),
    )


@router.post("/interrupts/{task_id}/resume", response_model=DifyInvokeResponse, tags=["dify"])
async def dify_resume_interrupt(
    task_id: str,
    interrupt_id: str = Query(..., description="中断ID"),
    action: str = Query(..., description="用户选择的动作"),
    inputs: Optional[Dict[str, Any]] = None,
):
    """Dify 中断恢复。"""
    dd_service = get_due_diligence_service()
    result = await dd_service.resume_interrupt(
        task_id=task_id,
        interrupt_id=interrupt_id,
        action=action,
        inputs=inputs or {},
    )

    return DifyInvokeResponse(
        success=result.get("success", True),
        data=result,
        message="任务已恢复",
        next_action="poll_status",
    )


# ═══════════════════════════════════════════════════════════════════
# 工具直接调用端点
# ═══════════════════════════════════════════════════════════════════

@router.post("/tools/{tool_name}", response_model=DifyToolResponse, tags=["dify"])
async def dify_tool_call(
    tool_name: str,
    request: DifyInvokeRequest,
):
    """Dify 工具直接调用 — 不走尽调引擎，直接调用底层工具。"""
    logger.info("[DifyAdapter] tool_call tool_name=%s", tool_name)

    try:
        if tool_name == "searxng":
            service = get_search_service()
            result = await service.search(
                query=request.query or "",
                max_results=request.max_results,
                category=request.category or "enterprise",
            )
        elif tool_name == "business":
            service = get_business_service()
            result = await service.query(request.query or "")
        elif tool_name == "legal":
            service = get_legal_service()
            result = await service.query(request.query or "")
        elif tool_name == "financial":
            service = get_financial_service()
            result = await service.analyze_summary(request.query or "")
        elif tool_name == "industry":
            service = get_industry_service()
            result = await service.analyze_summary(request.query or "")
        else:
            raise HTTPException(status_code=400, detail=f"未知的工具: {tool_name}")

        return DifyToolResponse(
            success=result.get("success", True),
            tool_name=tool_name,
            data=result.get("data", {}),
            error=result.get("error"),
        )
    except Exception as exc:
        logger.warning("[DifyAdapter] 工具调用失败: %s", exc)
        raise HTTPException(status_code=500, detail=f"工具调用失败: {str(exc)}")
