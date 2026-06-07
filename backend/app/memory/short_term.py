# ========================================
# 短期记忆
# 用于存储对话历史和临时数据
# ========================================

from typing import Dict, Any, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """记忆条目"""
    id: str
    timestamp: str
    role: str  # user/assistant/system/tool
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ShortTermMemory:
    """短期记忆"""

    def __init__(self, max_entries: int = 100):
        """初始化短期记忆

        Args:
            max_entries: 最大条目数
        """
        self.max_entries = max_entries
        self.entries: List[MemoryEntry] = []

    def add(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """添加记忆条目

        Args:
            role: 角色
            content: 内容
            metadata: 元数据

        Returns:
            MemoryEntry: 记忆条目
        """
        entry = MemoryEntry(
            id=f"mem_{len(self.entries) + 1}",
            timestamp=datetime.now().isoformat(),
            role=role,
            content=content,
            metadata=metadata or {},
        )

        self.entries.append(entry)

        # 超过最大条目数时删除最早的条目
        if len(self.entries) > self.max_entries:
            self.entries = self.entries[-self.max_entries:]

        return entry

    def get_recent(self, n: int = 10) -> List[MemoryEntry]:
        """获取最近的 n 条记忆

        Args:
            n: 条目数

        Returns:
            List[MemoryEntry]: 记忆条目列表
        """
        return self.entries[-n:]

    def get_by_role(self, role: str) -> List[MemoryEntry]:
        """按角色获取记忆

        Args:
            role: 角色

        Returns:
            List[MemoryEntry]: 记忆条目列表
        """
        return [e for e in self.entries if e.role == role]

    def search(self, query: str) -> List[MemoryEntry]:
        """搜索记忆

        Args:
            query: 搜索查询

        Returns:
            List[MemoryEntry]: 匹配的记忆条目列表
        """
        query_lower = query.lower()
        return [
            e for e in self.entries
            if query_lower in e.content.lower()
        ]

    def clear(self):
        """清空记忆"""
        self.entries = []

    def to_messages(self) -> List[Dict[str, str]]:
        """转换为消息格式

        Returns:
            List[Dict[str, str]]: 消息列表
        """
        return [
            {"role": e.role, "content": e.content}
            for e in self.entries
        ]

    def get_context(self, max_tokens: int = 4000) -> str:
        """获取上下文

        Args:
            max_tokens: 最大 token 数

        Returns:
            str: 上下文文本
        """
        context_parts = []
        current_length = 0

        # 从最新的记忆开始
        for entry in reversed(self.entries):
            text = f"[{entry.role}]: {entry.content}"
            if current_length + len(text) > max_tokens:
                break
            context_parts.insert(0, text)
            current_length += len(text)

        return "\n".join(context_parts)
