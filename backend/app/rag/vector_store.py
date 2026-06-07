# backend/app/rag/vector_store.py
"""向量存储模块"""
from langchain_community.vectorstores import Chroma
from pathlib import Path
from typing import Optional

from app.config import settings


class VectorStoreManager:
    """向量存储管理器"""

    def __init__(self, embedding_model, persist_dir: Optional[str] = None):
        """
        初始化向量存储管理器

        Args:
            embedding_model: Embedding 模型
            persist_dir: 持久化目录
        """
        self.embedding = embedding_model
        self.persist_dir = persist_dir or str(settings.DB_DIR / "chroma")
        self.vectorstore: Optional[Chroma] = None

    def initialize(self) -> Chroma:
        """
        初始化向量库

        Returns:
            Chroma: 向量库实例
        """
        # 确保目录存在
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        self.vectorstore = Chroma(
            persist_directory=self.persist_dir,
            embedding_function=self.embedding,
        )

        return self.vectorstore

    def get_vectorstore(self) -> Chroma:
        """
        获取向量库实例

        Returns:
            Chroma: 向量库实例
        """
        if self.vectorstore is None:
            self.initialize()
        return self.vectorstore

    def get_retriever(self, search_kwargs: dict = None):
        """
        获取检索器

        Args:
            search_kwargs: 搜索参数

        Returns:
            Retriever: 检索器实例
        """
        vectorstore = self.get_vectorstore()

        if search_kwargs is None:
            search_kwargs = {"k": 5}

        return vectorstore.as_retriever(search_kwargs=search_kwargs)
