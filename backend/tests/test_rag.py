# backend/tests/test_rag.py
"""RAG 知识库测试"""
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from langchain_core.documents import Document

from app.rag.vector_store import VectorStoreManager
from app.rag.knowledge_base import KnowledgeBase
from app.rag.retriever import KnowledgeRetriever


@pytest.fixture
def mock_embedding():
    """Mock Embedding 模型"""
    embedding = MagicMock()
    embedding.embed_query.return_value = [0.1, 0.2, 0.3]
    embedding.embed_documents.return_value = [[0.1, 0.2, 0.3]]
    return embedding


@pytest.fixture
def mock_vectorstore():
    """Mock 向量库"""
    vectorstore = MagicMock()
    vectorstore.similarity_search.return_value = [
        Document(
            page_content="测试内容",
            metadata={"source": "test.md", "category": "test"},
        )
    ]
    return vectorstore


def test_vector_store_manager_init(mock_embedding):
    """测试向量存储管理器初始化"""
    manager = VectorStoreManager(mock_embedding, persist_dir="/tmp/test_chroma")
    assert manager.embedding == mock_embedding
    assert manager.persist_dir == "/tmp/test_chroma"


def test_knowledge_retriever_search(mock_vectorstore):
    """测试知识检索器"""
    # 创建 mock 知识库
    kb = MagicMock()
    kb.search.return_value = [
        Document(
            page_content="测试内容",
            metadata={"source": "test.md"},
        )
    ]

    retriever = KnowledgeRetriever(kb)
    results = retriever.search("测试查询", "all", 5)

    assert len(results) == 1
    assert results[0].page_content == "测试内容"


def test_knowledge_retriever_search_formatted(mock_vectorstore):
    """测试知识检索器格式化输出"""
    kb = MagicMock()
    kb.search.return_value = [
        Document(
            page_content="测试内容",
            metadata={"source": "test.md", "header1": "测试标题"},
        )
    ]

    retriever = KnowledgeRetriever(kb)
    result = retriever.search_formatted("测试查询", "all", 5)

    assert "测试内容" in result
    assert "test.md" in result


def test_knowledge_retriever_empty_result():
    """测试空检索结果"""
    kb = MagicMock()
    kb.search.return_value = []

    retriever = KnowledgeRetriever(kb)
    result = retriever.search_formatted("测试查询", "all", 5)

    assert result == "未找到相关知识"


def test_knowledge_base_category_map():
    """测试知识类型映射"""
    assert KnowledgeBase.CATEGORY_MAP["regulations"] == "regulation"
    assert KnowledgeBase.CATEGORY_MAP["case_studies"] == "case"
    assert KnowledgeBase.CATEGORY_MAP["risk_frameworks"] == "framework"
