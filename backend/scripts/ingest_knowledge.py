#!/usr/bin/env python3
"""
知识库导入脚本
将 Markdown 文档导入到 ChromaDB 向量数据库
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.config.embedding_config import get_embedding_model
from app.rag import VectorStoreManager, KnowledgeBase


def main():
    """主函数"""
    print("🚀 开始导入知识库文档...")

    # 初始化 Embedding 模型
    print("📦 初始化 Embedding 模型...")
    embedding_model = get_embedding_model()

    # 初始化向量存储
    print("📦 初始化向量存储...")
    manager = VectorStoreManager(embedding_model)

    # 初始化知识库
    kb = KnowledgeBase(manager)

    # 知识库目录
    knowledge_dir = settings.KNOWLEDGE_BASE_DIR

    if not knowledge_dir.exists():
        print(f"❌ 知识库目录不存在: {knowledge_dir}")
        return

    # 导入文档
    print(f"📂 导入目录: {knowledge_dir}")
    results = kb.ingest_directory(str(knowledge_dir))

    # 打印结果
    print("\n✅ 导入完成！")
    print("=" * 50)
    total = 0
    for category, count in results.items():
        print(f"  {category}: {count} 个文档块")
        total += count
    print("=" * 50)
    print(f"  总计: {total} 个文档块")

    # 测试检索
    print("\n🔍 测试检索...")
    test_queries = [
        "应收账款周转天数",
        "行业景气度",
        "授信建议",
        "风险评估",
    ]

    for query in test_queries:
        results = kb.search(query, top_k=2)
        print(f"\n查询: {query}")
        for i, doc in enumerate(results, 1):
            source = doc.metadata.get("source", "未知来源")
            print(f"  [{i}] {source}")


if __name__ == "__main__":
    main()
