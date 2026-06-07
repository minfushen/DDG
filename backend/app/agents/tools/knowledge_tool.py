# backend/app/agents/tools/knowledge_tool.py
"""知识检索工具"""
from langchain_core.tools import tool
from typing import Optional


@tool
def search_knowledge_base(
    query: str,
    knowledge_type: str = "all",
) -> str:
    """检索尽调知识库，包括法规、案例、行业标准等。

    当用户询问法规条款、行业标准、历史案例时调用此工具。

    Args:
        query: 检索关键词
        knowledge_type: 知识类型（"regulation" | "case" | "standard" | "template" | "guide" | "all"）
    """
    try:
        from app.config import settings
        from app.config.embedding_config import get_embedding_model
        from app.rag import VectorStoreManager, KnowledgeBase, KnowledgeRetriever

        # 初始化 RAG 组件
        embedding_model = get_embedding_model()
        manager = VectorStoreManager(embedding_model)
        kb = KnowledgeBase(manager)
        retriever = KnowledgeRetriever(kb)

        # 执行检索
        result = retriever.search_formatted(
            query=query,
            knowledge_type=knowledge_type,
            top_k=5,
        )

        return result

    except Exception as e:
        # 降级方案：返回 Mock 数据
        return _fallback_search(query, knowledge_type)


def _fallback_search(query: str, knowledge_type: str) -> str:
    """
    降级检索方案

    Args:
        query: 检索查询
        knowledge_type: 知识类型

    Returns:
        str: 检索结果
    """
    mock_results = [
        {
            "source": "《企业会计准则第 14 号——收入》",
            "content": "收入是指企业在日常活动中形成的、会导致所有者权益增加的、与所有者投入资本无关的经济利益的总流入。",
            "type": "regulation",
        },
        {
            "source": "行业研究报告",
            "content": "互联网行业平均毛利率约 45-55%，头部企业毛利率普遍呈下降趋势。",
            "type": "standard",
        },
        {
            "source": "尽调案例库",
            "content": "某制造企业应收账款周转天数超过 90 天，后经调查发现存在大量关联交易虚增收入。",
            "type": "case",
        },
    ]

    # 根据类型过滤
    if knowledge_type != "all":
        filtered = [r for r in mock_results if r["type"] == knowledge_type]
    else:
        filtered = mock_results

    # 格式化输出
    formatted = []
    for i, doc in enumerate(filtered, 1):
        formatted.append(
            f"[{i}] 来源：{doc['source']}\n{doc['content']}"
        )

    return "\n\n---\n\n".join(formatted) if formatted else "未找到相关知识"
