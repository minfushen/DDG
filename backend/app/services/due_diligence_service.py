# ========================================
# 服务层 — 深度尽调任务服务
# 封装核心引擎的完整尽调流程，供 Dify 编排调用
# ========================================

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.agents.planning.intent_extractor import fast_extract_user_intent
from app.agents.research_engine import run_deep_research_due_diligence
from app.agents.state import SSEEvent
from app.api.task_store import load_task_snapshot, save_task_snapshot

logger = logging.getLogger(__name__)


class DueDiligenceService:
    """深度尽调任务服务 — 管理完整的尽调任务生命周期。

    提供任务创建、状态查询、中断处理、报告获取等原子操作，
    供 Dify 工作流编排调用。
    """

    def __init__(self):
        self._tasks: Dict[str, Dict[str, Any]] = {}
        self._task_events: Dict[str, asyncio.Event] = {}

    # ─── 任务创建 ───────────────────────────────────────────

    async def create_task(
        self,
        enterprise_name: str,
        template_name: str = "full",
        engine_mode: str = "deepresearch",
    ) -> Dict[str, Any]:
        """创建尽调任务。

        Returns:
            {"task_id": str, "status": "created", "enterprise_name": str}
        """
        task_id = datetime.now().strftime("%Y%m%d%H%M%S") + uuid.uuid4().hex[:8]
        input_parse = fast_extract_user_intent(enterprise_name)
        enterprise_name = input_parse["enterprise_name"]

        task = {
            "task_id": task_id,
            "enterprise_name": enterprise_name,
            "original_input": enterprise_name,
            "input_parse": input_parse,
            "template_name": template_name,
            "engine_mode": engine_mode,
            "agent_state": "created",
            "timeline": [],
            "plan": [],
            "evidence": [],
            "report": None,
            "error": None,
            "created_at": datetime.now().isoformat(),
        }

        self._tasks[task_id] = task
        self._task_events[task_id] = asyncio.Event()
        save_task_snapshot(task)

        logger.info("[DueDiligenceService] 任务创建: %s enterprise=%s", task_id, enterprise_name)

        return {
            "task_id": task_id,
            "status": "created",
            "enterprise_name": enterprise_name,
            "next_action": "start_execution",
        }

    async def start_execution(self, task_id: str) -> Dict[str, Any]:
        """启动任务执行（后台运行）。"""
        task = self._tasks.get(task_id)
        if not task:
            return {"success": False, "error": "任务不存在"}

        task["agent_state"] = "running"
        save_task_snapshot(task)

        # 后台执行（异步，不阻塞）
        asyncio.create_task(self._run_task(task_id))

        return {
            "task_id": task_id,
            "status": "running",
            "next_action": "poll_status",
        }

    async def _run_task(self, task_id: str) -> None:
        """后台执行尽调任务。"""
        task = self._tasks.get(task_id)
        if not task:
            return

        try:
            result = await run_deep_research_due_diligence(
                task,
                task_id=task_id,
            )
            task["agent_state"] = "completed"
            task["report"] = result.get("report")
            task["full_due_diligence_context"] = result
        except Exception as exc:
            logger.error("[DueDiligenceService] 任务执行失败: %s", exc)
            task["agent_state"] = "failed"
            task["error"] = str(exc)

        save_task_snapshot(task)

        # 通知等待者
        event = self._task_events.get(task_id)
        if event:
            event.set()

    # ─── 状态查询 ───────────────────────────────────────────

    async def get_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态（简化版，供 Dify 轮询）。"""
        task = self._tasks.get(task_id)
        if not task:
            # 尝试从数据库加载
            snapshot = load_task_snapshot(task_id)
            if snapshot:
                task = snapshot
                self._tasks[task_id] = task

        if not task:
            return {"success": False, "error": "任务不存在"}

        agent_state = task.get("agent_state", "unknown")
        has_interrupt = agent_state in ("waiting_human", "waiting_confirm")

        # 计算进度
        timeline = task.get("timeline", [])
        total_steps = 10  # 预估总步骤
        completed_steps = len(timeline)
        progress = f"{min(completed_steps, total_steps)}/{total_steps}"

        # 中断信息
        interrupt_info = None
        if has_interrupt:
            interrupts = task.get("interrupts", [])
            active = task.get("active_interrupt")
            if active:
                interrupt_info = {
                    "type": active.get("interrupt_type"),
                    "title": active.get("title"),
                    "message": active.get("message"),
                }

        return {
            "task_id": task_id,
            "status": "running" if agent_state in ("creating_task", "running", "researching") else agent_state,
            "agent_state": agent_state,
            "progress": progress,
            "next_expected": self._next_expected_text(agent_state),
            "has_interrupt": has_interrupt,
            "interrupt_info": interrupt_info,
            "report_ready": agent_state == "completed",
            "error": task.get("error"),
        }

    def _next_expected_text(self, agent_state: str) -> str:
        """生成人类可读的下一步预期。"""
        mapping = {
            "created": "任务已创建，等待启动执行",
            "running": "正在执行深度研究，请等待",
            "researching": "正在进行多轮研究检索",
            "analyzing": "正在分析检索结果",
            "reporting": "正在生成尽调报告",
            "waiting_human": "等待用户输入（HITL中断）",
            "waiting_confirm": "等待用户确认",
            "completed": "任务已完成，可获取报告",
            "failed": "任务执行失败",
        }
        return mapping.get(agent_state, "状态未知")

    # ─── 报告获取 ───────────────────────────────────────────

    async def get_report(self, task_id: str) -> Dict[str, Any]:
        """获取任务报告（简化版，供 Dify 展示）。"""
        task = self._tasks.get(task_id)
        if not task:
            snapshot = load_task_snapshot(task_id)
            if snapshot:
                task = snapshot

        if not task:
            return {"success": False, "error": "任务不存在"}

        report = task.get("report") or {}
        context = task.get("full_due_diligence_context") or {}

        return {
            "task_id": task_id,
            "enterprise_name": task.get("enterprise_name", ""),
            "report_status": task.get("agent_state", ""),
            "executive_summary": report.get("executive_summary", ""),
            "sections": report.get("sections", []),
            "key_metrics": report.get("key_metrics", {}),
            "risk_level": context.get("risk_level", "未知"),
            "risk_score": context.get("risk_score", 0),
            "diagnostics": context.get("diagnostics", []),
            "evidence_summary": [e.get("source") for e in task.get("evidence", [])][:10],
            "data_gaps": context.get("data_gaps", []),
            "report_url": f"/api/v1/tasks/{task_id}/report",
        }

    # ─── HITL 中断处理 ───────────────────────────────────────────

    async def get_interrupts(self, task_id: str) -> Dict[str, Any]:
        """获取任务中断列表。"""
        task = self._tasks.get(task_id)
        if not task:
            return {"success": False, "error": "任务不存在"}

        interrupts = task.get("interrupts", [])
        active = task.get("active_interrupt")

        return {
            "task_id": task_id,
            "interrupts": interrupts,
            "active": active,
            "has_interrupt": active is not None,
        }

    async def resume_interrupt(
        self,
        task_id: str,
        interrupt_id: str,
        action: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """恢复中断任务。"""
        task = self._tasks.get(task_id)
        if not task:
            return {"success": False, "error": "任务不存在"}

        # 处理中断恢复逻辑
        # TODO: 需要与现有 HITL 系统对接
        task["agent_state"] = "running"
        save_task_snapshot(task)

        return {
            "task_id": task_id,
            "status": "resumed",
            "next_action": "poll_status",
        }


# 单例
_due_diligence_service: Optional[DueDiligenceService] = None


def get_due_diligence_service() -> DueDiligenceService:
    """获取尽调服务单例。"""
    global _due_diligence_service
    if _due_diligence_service is None:
        _due_diligence_service = DueDiligenceService()
    return _due_diligence_service
