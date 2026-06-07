# backend/app/rag/retriever.py
"""知识检索器"""
from typing import List, Optional, Dict, Any
from langchain_core.documents import Document

from app.rag.knowledge_base import KnowledgeBase
from app.rag.vector_store import VectorStoreManager


class KnowledgeRetriever:
    """知识检索器"""

    def __init__(self, knowledge_base: KnowledgeBase):
        """
        初始化检索器

        Args:
            knowledge_base: 知识库实例
        """
        self.kb = knowledge_base

    def search(
        self,
        query: str,
        knowledge_type: str = "all",
        top_k: int = 5,
    ) -> List[Document]:
        """
        检索知识库

        Args:
            query: 检索查询
            knowledge_type: 知识类型
            top_k: 返回数量

        Returns:
            List[Document]: 检索结果
        """
        # 类型映射
        type_map = {
            "regulation": "regulation",
            "case": "case",
            "standard": "framework",
            "template": "template",
            "guide": "guide",
            "all": None,
        }

        category = type_map.get(knowledge_type)

        results = self.kb.search(
            query=query,
            category=category,
            top_k=top_k,
        )

        return results

    def search_formatted(
        self,
        query: str,
        knowledge_type: str = "all",
        top_k: int = 5,
    ) -> str:
        """
        检索知识库并格式化输出

        Args:
            query: 检索查询
            knowledge_type: 知识类型
            top_k: 返回数量

        Returns:
            str: 格式化的检索结果
        """
        results = self.search(query, knowledge_type, top_k)

        if not results:
            return "未找到相关知识"

        formatted = []
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("source", "未知来源")
            header = doc.metadata.get("header1", "")
            content = doc.page_content[:500]  # 限制长度

            formatted.append(
                f"[{i}] 来源：{source}\n"
                f"标题：{header}\n"
                f"内容：{content}\n"
            )

        return "\n---\n\n".join(formatted)
