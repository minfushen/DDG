# ========================================
# Agent 记忆系统
# ========================================
#
# 设计参考：Feynman Build Workshop 01
# 核心架构：SQLite + FTS5 (trigram) 全文索引
# 三分类：persistent（跨会话） / session（当前会话） / archived（归档）
# 时效管理：created_at + valid_until + superseded_by + last_accessed + access_count
# Frozen Snapshot：冻结稳定记忆，保护 Prefix Cache，降低 Token 成本
#
# 使用方式：
#   from app.memory import ShortTermMemory, LongTermMemory, MemoryManager
#   stm = ShortTermMemory(session_id="sess_001", task_id="task_001")
#   stm.add_tool_result(tool_name="searxng", result_summary="找到3条结果", cache_hit=True)
#   ltm = LongTermMemory()
#   ltm.add_enterprise_profile("腾讯控股", "大型互联网科技公司...")
#
# 配置开关（settings.py）：
#   ENABLE_SHORT_TERM_MEMORY = True
#   ENABLE_LONG_TERM_MEMORY = True
#   MEMORY_FREEZE_DAYS = 3
#   MEMORY_CONSOLIDATION_DAYS = 7
#   MEMORY_STALE_DAYS = 30
# ========================================

from __future__ import annotations

from typing import Optional

from .long_term import LongTermMemory
from .memory_store import (
    archive_stale_memories,
    freeze_stable_memories,
    get_frozen_snapshot,
    init_memory_db,
    memory_stats,
)
from .short_term import ShortTermMemory

# 统一入口：MemoryManager
class MemoryManager:
    """记忆管理统一入口。

    同时提供短期记忆和长期记忆，支持一键初始化。
    """

    def __init__(self, session_id: str, task_id: Optional[str] = None):
        self.short_term = ShortTermMemory(session_id, task_id)
        self.long_term = LongTermMemory()

    @staticmethod
    def init_db():
        """初始化记忆数据库。"""
        init_memory_db()

__all__ = [
    "ShortTermMemory",
    "LongTermMemory",
    "MemoryManager",
    "init_memory_db",
    "freeze_stable_memories",
    "archive_stale_memories",
    "get_frozen_snapshot",
    "memory_stats",
]
