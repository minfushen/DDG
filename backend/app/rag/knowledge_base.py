# backend/app/rag/knowledge_base.py
"""知识库模块"""
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_core.documents import Document
from pathlib import Path
from typing import List, Optional, Dict

from app.rag.vector_store import VectorStoreManager


class KnowledgeBase:
    """尽调知识库"""

    # 知识类型映射
    CATEGORY_MAP = {
        "regulations": "regulation",
        "industry_guides": "guide",
        "analysis_templates": "template",
        "case_studies": "case",
        "risk_frameworks": "framework",
    }

    def __init__(self, vector_store_manager: VectorStoreManager):
        """
        初始化知识库

        Args:
            vector_store_manager: 向量存储管理器
        """
        self.manager = vector_store_manager
        self.text_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=[
                ("#", "header1"),
                ("##", "header2"),
                ("###", "header3"),
                ("####", "header4"),
            ]
        )

    def ingest_markdown(self, file_path: str, category: str) -> int:
        """
        导入 Markdown 文档

        Args:
            file_path: 文件路径
            category: 知识类型

        Returns:
            int: 导入的文档块数量
        """
        content = Path(file_path).read_text(encoding="utf-8")

        # 按标题分块
        splits = self.text_splitter.split_text(content)

        # 添加元数据
        docs = []
        for split in splits:
            doc = Document(
                page_content=split.page_content,
                metadata={
                    **split.metadata,
                    "source": file_path,
                    "category": category,
                    "filename": Path(file_path).name,
                }
            )
            docs.append(doc)

        # 写入向量库
        vectorstore = self.manager.get_vectorstore()
        vectorstore.add_documents(docs)

        return len(docs)

    def ingest_directory(self, directory: str) -> Dict[str, int]:
        """
        导入目录下所有 Markdown 文档

        Args:
            directory: 目录路径

        Returns:
            Dict: 各类型导入数量
        """
        dir_path = Path(directory)
        results = {}

        for subdir in dir_path.iterdir():
            if not subdir.is_dir():
                continue

            category = self.CATEGORY_MAP.get(subdir.name, subdir.name)
            count = 0

            for md_file in subdir.glob("*.md"):
                count += self.ingest_markdown(str(md_file), category)

            results[category] = count

        return results

    def search(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 5,
    ) -> List[Document]:
        """
        检索知识库

        Args:
            query: 检索查询
            category: 知识类型过滤
            top_k: 返回数量

        Returns:
            List[Document]: 检索结果
        """
        vectorstore = self.manager.get_vectorstore()

        # 构建过滤条件
        filter_dict = {"category": category} if category else None

        results = vectorstore.similarity_search(
            query=query,
            k=top_k,
            filter=filter_dict,
        )

        return results

    def search_with_score(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 5,
    ) -> List[tuple]:
        """
        检索知识库（带分数）

        Args:
            query: 检索查询
            category: 知识类型过滤
            top_k: 返回数量

        Returns:
            List[tuple]: (Document, score) 列表
        """
        vectorstore = self.manager.get_vectorstore()

        filter_dict = {"category": category} if category else None

        results = vectorstore.similarity_search_with_score(
            query=query,
            k=top_k,
            filter=filter_dict,
        )

        return results
