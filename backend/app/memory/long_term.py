# ========================================
# 长期记忆（LongTermMemory）
# 用于存储企业知识沉淀、历史分析结果、用户偏好
# 支持：添加、搜索、更新、冻结、归纳
# ========================================

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.config import settings

from .memory_store import (
    archive_stale_memories,
    freeze_stable_memories,
    get_frozen_snapshot,
    memory_add,
    memory_get_recent,
    memory_search,
    memory_stats,
    memory_update_content,
)

logger = logging.getLogger(__name__)


class LongTermMemory:
    """长期记忆 — 跨会话持久化的知识沉淀。

    存储内容：
    - 企业画像（工商/财务/司法/行业多维画像）
    - 分析结论（历史分析结果、风险评估、建议）
    - 用户偏好（分析风格、重点关注领域、报告格式偏好）
    - 技术决策（数据源配置、工具使用策略、评分模型参数）
    - 踩坑/教训（历史失败案例、规避策略）

    特点：
    - 默认 category = persistent
    - 支持 FTS5 全文搜索
    - 支持 Frozen Snapshot（冻结稳定记忆，保护 Prefix Cache）
    - 支持按类别/企业/关键词检索
    - 定期归档（通过 archive_stale_memories）
    """

    def __init__(self, namespace: Optional[str] = None):
        """初始化长期记忆。

        Args:
            namespace: 命名空间，用于隔离不同租户/环境的数据。
                      默认空 = 全局共享。
        """
        self.namespace = namespace or "global"
        self.enabled = settings.ENABLE_LONG_TERM_MEMORY

        if not self.enabled:
            logger.debug("长期记忆已禁用（ENABLE_LONG_TERM_MEMORY=False）")

    # ─── 写入 ───────────────────────────────────────────

    def add(
        self,
        content: str,
        title: Optional[str] = None,
        category: str = "persistent",
        enterprise: Optional[str] = None,
        valid_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """添加一条长期记忆。

        Args:
            content: 记忆内容
            title: 标题（用于摘要展示）
            category: persistent / enterprise / industry / risk / preference / decision
            enterprise: 企业名称（可选，用于关联企业画像）
            valid_days: 有效天数（None = 永久）
            metadata: 额外元数据

        Returns:
            记忆 ID，或 None（如果禁用）
        """
        if not self.enabled:
            return None

        # 组装内容
        if title:
            full_content = f"[{title}] {content}"
        else:
            full_content = content

        # 组装元数据
        meta = metadata or {}
        if enterprise:
            meta["enterprise"] = enterprise
        if title:
            meta["title"] = title
        meta["namespace"] = self.namespace

        # 计算过期时间
        valid_until = None
        if valid_days is not None and valid_days > 0:
            from datetime import datetime, timedelta
            valid_until = (datetime.now() + timedelta(days=valid_days)).isoformat()

        return memory_add(
            content=full_content,
            category=category,
            valid_until=valid_until,
            metadata=meta,
        )

    def add_enterprise_profile(
        self,
        enterprise_name: str,
        profile: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """添加企业画像。

        如果已有该企业画像，则更新（旧记录标记 superseded）。
        """
        # 先搜索现有记录
        existing = self.search_by_enterprise(enterprise_name, limit=1)
        if existing:
            # 更新现有记录
            old_id = existing[0]["id"]
            return self.update(old_id, profile, metadata=metadata)

        return self.add(
            content=profile,
            title=f"企业画像: {enterprise_name}",
            category="enterprise",
            enterprise=enterprise_name,
            valid_days=90,  # 3个月有效期
            metadata=metadata,
        )

    def add_analysis_conclusion(
        self,
        enterprise_name: str,
        conclusion: str,
        analysis_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """添加分析结论。

        Args:
            enterprise_name: 企业名称
            conclusion: 结论内容
            analysis_type: 分析类型（financial/legal/industry/risk/general）
            metadata: 额外元数据
        """
        return self.add(
            content=conclusion,
            title=f"分析结论: {enterprise_name} ({analysis_type})",
            category="persistent",
            enterprise=enterprise_name,
            valid_days=180,  # 6个月有效期
            metadata={
                "analysis_type": analysis_type,
                **(metadata or {}),
            },
        )

    def add_user_preference(
        self,
        preference: str,
        preference_type: str = "general",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """添加用户偏好。"""
        return self.add(
            content=preference,
            title=f"用户偏好: {preference_type}",
            category="preference",
            valid_days=365,  # 1年有效期
            metadata={
                "preference_type": preference_type,
                **(metadata or {}),
            },
        )

    def add_lesson_learned(
        self,
        lesson: str,
        context: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """记录踩坑/教训。"""
        content = lesson
        if context:
            content = f"{lesson}\n\n场景: {context}"

        return self.add(
            content=content,
            title="教训/踩坑",
            category="persistent",
            valid_days=365,
            metadata=metadata,
        )

    # ─── 读取 ───────────────────────────────────────────

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        enterprise: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """搜索长期记忆。

        Args:
            query: 搜索关键词
            category: 类别过滤
            enterprise: 企业名称过滤
            limit: 返回数量
        """
        if not self.enabled:
            return []

        # 先 FTS5 搜索
        results = memory_search(
            query=query,
            limit=limit * 2,  # 多取一些，再过滤
            category=category,
            include_expired=False,
            prefer_frozen=True,
        )

        # 企业过滤
        if enterprise:
            results = [
                r for r in results
                if enterprise in r.get("content", "")
                or (r.get("metadata_json") and enterprise in r.get("metadata_json", ""))
            ]

        return results[:limit]

    def search_by_enterprise(
        self,
        enterprise_name: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """搜索某企业的所有长期记忆。"""
        return self.search(
            query=enterprise_name,
            limit=limit,
        )

    def get_enterprise_profile(self, enterprise_name: str) -> Optional[Dict[str, Any]]:
        """获取企业画像（最新的一条）。"""
        results = self.search_by_enterprise(enterprise_name, limit=1)
        if results:
            return results[0]
        return None

    def get_recent(self, n: int = 10) -> List[Dict[str, Any]]:
        """获取最近 N 条长期记忆。"""
        if not self.enabled:
            return []
        return memory_get_recent(
            limit=n,
            category="persistent",
        )

    def get_frozen_context(self, max_entries: int = 20) -> str:
        """获取冻结记忆上下文，用于注入 System Prompt 的 Stable Prefix。

        这是降低 Token 成本的关键：冻结的记忆放在 Prompt 头部，
        动态内容放在尾部，确保 Prefix Cache 命中。
        """
        if not self.enabled:
            return ""

        snapshot = get_frozen_snapshot(max_entries=max_entries)
        if not snapshot:
            return ""

        lines = []
        for s in snapshot:
            content = s.get("content", "")
            category = s.get("category", "")
            lines.append(f"[{category}] {content}")

        return "\n".join(lines)

    # ─── 更新 ───────────────────────────────────────────

    def update(
        self,
        meta_id: int,
        new_content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[int]:
        """更新记忆内容（创建新记录，旧记录标记 superseded）。"""
        if not self.enabled:
            return None

        return memory_update_content(meta_id, new_content)

    # ─── 管理 ───────────────────────────────────────────

    def freeze(self, inactivity_days: Optional[int] = None) -> int:
        """冻结稳定记忆。"""
        if not self.enabled:
            return 0

        days = inactivity_days or settings.MEMORY_FREEZE_DAYS
        return freeze_stable_memories(days)

    def archive_stale(self, stale_days: Optional[int] = None) -> int:
        """归档过期记忆。"""
        if not self.enabled:
            return 0

        days = stale_days or settings.MEMORY_STALE_DAYS
        return archive_stale_memories(days)

    def consolidate(
        self,
        consolidation_days: Optional[int] = None,
    ) -> Dict[str, int]:
        """运行归纳：去重 + 冲突检测 + 归档。

        返回统计：
        {
            "frozen": 冻结数量,
            "archived": 归档数量,
        }
        """
        if not self.enabled:
            return {"frozen": 0, "archived": 0}

        days = consolidation_days or settings.MEMORY_CONSOLIDATION_DAYS

        # 冻结稳定记忆
        frozen_count = freeze_stable_memories(inactivity_days=days)

        # 归档过期记忆
        archived_count = archive_stale_memories(stale_days=days * 2)

        return {
            "frozen": frozen_count,
            "archived": archived_count,
        }

    def stats(self) -> Dict[str, Any]:
        """返回长期记忆统计。"""
        if not self.enabled:
            return {"enabled": False}

        all_stats = memory_stats()
        return {
            "enabled": True,
            "namespace": self.namespace,
            "total": all_stats.get("total", 0),
            "by_category": all_stats.get("by_category", {}),
            "superseded": all_stats.get("superseded", 0),
            "frozen": all_stats.get("frozen", 0),
        }
