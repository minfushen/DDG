# ========================================
# 短期记忆（ShortTermMemory）
# 用于缓存对话历史、工具结果、临时上下文
# 支持：添加、查询、搜索、清空、截断
# ========================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.config import settings

from .memory_store import (
    memory_add,
    memory_get_recent,
    memory_search,
    memory_stats,
)

logger = logging.getLogger(__name__)


class ShortTermMemory:
    """短期记忆 — 当前会话有效，结束后可丢弃。

    存储内容：
    - 用户输入 / AI 回复
    - 工具调用结果（成功/失败）
    - 缓存命中记录（复用了之前的搜索结果）
    - 临时上下文（如中间计算结果）

    特点：
    - 默认按会话(session_id) + 任务(task_id) 隔离
    - 支持按会话/任务查询最近记录
    - 支持全文搜索
    - 不自动过期，可手动清理
    """

    def __init__(self, session_id: str, task_id: Optional[str] = None):
        """初始化短期记忆。

        Args:
            session_id: 会话 ID（如用户会话、WebSocket 连接）
            task_id: 可选的任务 ID（如研究任务 ID）
        """
        self.session_id = session_id
        self.task_id = task_id
        self.enabled = settings.ENABLE_SHORT_TERM_MEMORY

        if not self.enabled:
            logger.debug("短期记忆已禁用（ENABLE_SHORT_TERM_MEMORY=False）")

    # ─── 写入 ───────────────────────────────────────────

    def add(
        self,
        content: str,
        role: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """添加一条短期记忆。

        Args:
            content: 记忆内容
            role: 角色标记（user/assistant/system/tool）
            metadata: 额外元数据（如 tool_name, cache_hit, error 等）

        Returns:
            记忆 ID，或 None（如果禁用）
        """
        if not self.enabled:
            return None

        # 自动构建更丰富的内容描述
        if role:
            content = f"[{role}] {content}"

        # 组装元数据
        meta = metadata or {}
        if role:
            meta["role"] = role

        return memory_add(
            content=content,
            category="session",
            session_id=self.session_id,
            task_id=self.task_id,
            metadata=meta,
        )

    def add_user_message(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """记录用户输入。"""
        return self.add(message, role="user", metadata=metadata)

    def add_assistant_message(self, message: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """记录 AI 回复。"""
        return self.add(message, role="assistant", metadata=metadata)

    def add_tool_result(
        self,
        tool_name: str,
        result_summary: str,
        success: bool = True,
        cache_hit: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """记录工具调用结果。

        Args:
            tool_name: 工具名称
            result_summary: 结果摘要
            success: 是否成功
            cache_hit: 是否命中缓存
            metadata: 额外元数据
        """
        meta = metadata or {}
        meta.update({
            "tool_name": tool_name,
            "success": success,
            "cache_hit": cache_hit,
        })

        content = f"工具调用 {tool_name}: {result_summary}"
        if cache_hit:
            content = f"[缓存命中] 工具调用 {tool_name}: {result_summary}"
        elif not success:
            content = f"[失败] 工具调用 {tool_name}: {result_summary}"

        return self.add(content, role="tool", metadata=meta)

    def add_llm_cache_hit(
        self,
        prompt_summary: str,
        model: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """记录 LLM 缓存命中（复用了之前的 LLM 响应）。"""
        meta = metadata or {}
        meta.update({
            "model": model,
            "cache_hit": True,
            "type": "llm_cache",
        })

        content = f"[LLM缓存命中] 模型={model}, 提示摘要={prompt_summary}"
        return self.add(content, role="system", metadata=meta)

    def add_system_event(self, event: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[int]:
        """记录系统事件（如任务状态变化、错误等）。"""
        return self.add(event, role="system", metadata=metadata)

    # ─── 读取 ───────────────────────────────────────────

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """获取最近 N 条记忆。"""
        if not self.enabled:
            return []
        return memory_get_recent(
            limit=n,
            category="session",
            session_id=self.session_id,
            task_id=self.task_id,
        )

    def get_by_role(self, role: str, n: int = 10) -> List[Dict[str, Any]]:
        """按角色获取最近 N 条记忆。"""
        if not self.enabled:
            return []
        results = memory_get_recent(
            limit=n * 3,  # 多取一些再过滤
            category="session",
            session_id=self.session_id,
            task_id=self.task_id,
        )
        return [r for r in results if role in r.get("content", "")]

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索记忆。"""
        if not self.enabled:
            return []
        return memory_search(
            query=query,
            limit=limit,
            category="session",
            session_id=self.session_id,
            task_id=self.task_id,
        )

    def get_context(self, max_entries: int = 20) -> str:
        """获取上下文文本，适合注入 Prompt。

        格式：每行 [role] content
        """
        if not self.enabled:
            return ""

        entries = memory_get_recent(
            limit=max_entries,
            category="session",
            session_id=self.session_id,
            task_id=self.task_id,
        )

        if not entries:
            return ""

        lines = []
        for e in entries:
            content = e.get("content", "")
            # 提取 [role] 标记
            if content.startswith("[") and "]" in content:
                role = content[1:content.index("]")]
                text = content[content.index("]") + 1:].strip()
                lines.append(f"[{role}]: {text}")
            else:
                lines.append(content)

        return "\n".join(lines)

    def to_messages(self, max_entries: int = 20) -> List[Dict[str, str]]:
        """转换为 LangChain 消息格式 [{"role": ..., "content": ...}]。"""
        if not self.enabled:
            return []

        entries = memory_get_recent(
            limit=max_entries,
            category="session",
            session_id=self.session_id,
            task_id=self.task_id,
        )

        messages = []
        for e in entries:
            content = e.get("content", "")
            if content.startswith("[") and "]" in content:
                role = content[1:content.index("]")]
                text = content[content.index("]") + 1:].strip()
                # 标准化角色名
                role_map = {
                    "user": "human",
                    "assistant": "ai",
                    "system": "system",
                    "tool": "system",
                }
                messages.append({
                    "role": role_map.get(role, role),
                    "content": text,
                })
            else:
                messages.append({"role": "system", "content": content})

        return messages

    # ─── 管理 ───────────────────────────────────────────

    def clear(self) -> None:
        """清空当前会话的短期记忆（标记为 archived）。

        注意：不物理删除，只标记为 archived，支持"时间旅行"查询。
        """
        if not self.enabled:
            return

        from .memory_store import _get_conn
        from datetime import datetime

        now = datetime.now().isoformat()
        with _get_conn() as conn:
            cur = conn.cursor()
            cur.execute(
                """UPDATE memory_meta
                    SET category = 'archived', frozen = 0, valid_until = ?
                    WHERE category = 'session'
                    AND session_id = ?""",
                (now, self.session_id) if not self.task_id else (now, self.session_id),
            )
            # 如果有 task_id，也过滤
            if self.task_id:
                cur.execute(
                    """UPDATE memory_meta
                        SET category = 'archived', frozen = 0, valid_until = ?
                        WHERE category = 'session'
                        AND session_id = ?
                        AND task_id = ?""",
                    (now, self.session_id, self.task_id),
                )

        logger.info("已清空会话 %s 的短期记忆", self.session_id)

    def stats(self) -> Dict[str, Any]:
        """返回当前会话的统计。"""
        if not self.enabled:
            return {"enabled": False}

        all_stats = memory_stats()
        return {
            "enabled": True,
            "session_id": self.session_id,
            "task_id": self.task_id,
            "total": all_stats.get("total", 0),
            "by_category": all_stats.get("by_category", {}),
        }
