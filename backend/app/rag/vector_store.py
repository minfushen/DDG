# backend/app/rag/vector_store.py
"""向量存储模块"""
import os

import chromadb
from chromadb.config import Settings as ChromaSettings
from langchain_community.vectorstores import Chroma
from pathlib import Path
from typing import Optional

from app.config import settings

# chromadb 1.1.x 默认 chroma_api_impl=chromadb.api.rust.RustBindingsAPI，
# 其 Rust sqlite 绑定在读取某些状态时会发生 panic
# (pyo3_runtime.PanicException: range start index 10 out of range for slice of length 9)，
# 直接崩掉整个研究进程。改走 SegmentAPI（Python SqliteDB + chroma-hnswlib），
# 规避 Rust 绑定崩溃。如需回退 Rust，设环境变量 CHROMA_API_IMPL 即可覆盖。
CHROMA_API_IMPL = os.getenv(
    "CHROMA_API_IMPL",
    "chromadb.api.segment.SegmentAPI",
)


class VectorStoreManager:
    """向量存储管理器"""

    def __init__(
        self,
        embedding_model,
        persist_dir: Optional[str] = None,
        collection_name: Optional[str] = None,
    ):
        """
        初始化向量存储管理器

        Args:
            embedding_model: Embedding 模型
            persist_dir: 持久化目录
            collection_name: Chroma collection 名称；不同企业使用不同 collection 实现隔离
        """
        self.embedding = embedding_model
        self.persist_dir = persist_dir or str(settings.DB_DIR / "chroma")
        self.collection_name = collection_name or "default"
        self.vectorstore: Optional[Chroma] = None

    def initialize(self) -> Chroma:
        """
        初始化向量库

        Returns:
            Chroma: 向量库实例
        """
        # 确保目录存在
        Path(self.persist_dir).mkdir(parents=True, exist_ok=True)

        # 显式指定 chroma_api_impl，规避 Rust 绑定 panic（见模块顶部说明）
        client_settings = ChromaSettings(
            chroma_api_impl=CHROMA_API_IMPL,
            is_persistent=True,
            persist_directory=self.persist_dir,
        )

        self.vectorstore = Chroma(
            persist_directory=self.persist_dir,
            embedding_function=self.embedding,
            collection_name=self.collection_name,
            client_settings=client_settings,
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
