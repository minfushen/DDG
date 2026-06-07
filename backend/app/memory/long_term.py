# ========================================
# 长期记忆
# 用于存储知识沉淀和历史分析结果
# ========================================

from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime
from pydantic import BaseModel, Field
import json


class KnowledgeEntry(BaseModel):
    """知识条目"""
    id: str
    category: str  # enterprise/industry/risk/case
    title: str
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class LongTermMemory:
    """长期记忆"""

    def __init__(self, storage_dir: Optional[str] = None):
        """初始化长期记忆

        Args:
            storage_dir: 存储目录
        """
        if storage_dir is None:
            storage_dir = str(Path(__file__).parent.parent.parent / "db" / "memory")

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.entries: Dict[str, KnowledgeEntry] = {}

        # 加载已有记忆
        self._load()

    def _load(self):
        """加载记忆"""
        memory_file = self.storage_dir / "long_term_memory.json"
        if memory_file.exists():
            try:
                with open(memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for entry_id, entry_data in data.items():
                        self.entries[entry_id] = KnowledgeEntry(**entry_data)
            except Exception as e:
                print(f"加载长期记忆失败: {e}")

    def _save(self):
        """保存记忆"""
        memory_file = self.storage_dir / "long_term_memory.json"
        try:
            data = {
                entry_id: entry.model_dump()
                for entry_id, entry in self.entries.items()
            }
            with open(memory_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存长期记忆失败: {e}")

    def add(
        self,
        category: str,
        title: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> KnowledgeEntry:
        """添加知识条目

        Args:
            category: 类别
            title: 标题
            content: 内容
            metadata: 元数据

        Returns:
            KnowledgeEntry: 知识条目
        """
        now = datetime.now().isoformat()
        entry = KnowledgeEntry(
            id=f"knowledge_{len(self.entries) + 1}",
            category=category,
            title=title,
            content=content,
            metadata=metadata or {},
            created_at=now,
            updated_at=now,
        )

        self.entries[entry.id] = entry
        self._save()

        return entry

    def get(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """获取知识条目

        Args:
            entry_id: 条目 ID

        Returns:
            KnowledgeEntry: 知识条目
        """
        return self.entries.get(entry_id)

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[KnowledgeEntry]:
        """搜索知识

        Args:
            query: 搜索查询
            category: 类别过滤
            limit: 返回数量限制

        Returns:
            List[KnowledgeEntry]: 匹配的知识条目列表
        """
        query_lower = query.lower()
        results = []

        for entry in self.entries.values():
            # 类别过滤
            if category and entry.category != category:
                continue

            # 内容匹配
            if (
                query_lower in entry.title.lower()
                or query_lower in entry.content.lower()
            ):
                results.append(entry)

            if len(results) >= limit:
                break

        return results

    def get_by_category(self, category: str) -> List[KnowledgeEntry]:
        """按类别获取知识

        Args:
            category: 类别

        Returns:
            List[KnowledgeEntry]: 知识条目列表
        """
        return [
            entry for entry in self.entries.values()
            if entry.category == category
        ]

    def update(self, entry_id: str, content: str) -> Optional[KnowledgeEntry]:
        """更新知识条目

        Args:
            entry_id: 条目 ID
            content: 新内容

        Returns:
            KnowledgeEntry: 更新后的知识条目
        """
        entry = self.entries.get(entry_id)
        if entry:
            entry.content = content
            entry.updated_at = datetime.now().isoformat()
            self._save()
        return entry

    def delete(self, entry_id: str) -> bool:
        """删除知识条目

        Args:
            entry_id: 条目 ID

        Returns:
            bool: 是否删除成功
        """
        if entry_id in self.entries:
            del self.entries[entry_id]
            self._save()
            return True
        return False

    def get_context(
        self,
        query: str,
        max_tokens: int = 4000,
    ) -> str:
        """获取上下文

        Args:
            query: 查询
            max_tokens: 最大 token 数

        Returns:
            str: 上下文文本
        """
        results = self.search(query, limit=10)

        context_parts = []
        current_length = 0

        for entry in results:
            text = f"[{entry.category}] {entry.title}: {entry.content}"
            if current_length + len(text) > max_tokens:
                break
            context_parts.append(text)
            current_length += len(text)

        return "\n".join(context_parts)
