# backend/app/config/embedding_config.py
"""Embedding 模型配置"""
from functools import lru_cache

from app.config import settings


@lru_cache()
def get_embedding_model():
    """
    获取 Embedding 模型实例

    Returns:
        Embedding 模型实例
    """
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "siliconflow":
        # SiliconFlow（OpenAI 兼容格式）
        try:
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL_ID,
                api_key=settings.EMBEDDING_API_KEY,
                base_url=settings.EMBEDDING_BASE_URL,
                # SiliconFlow 嵌入维度为 1024
                # 不需要指定 dimensions，模型返回固定维度
            )
        except ImportError:
            raise ImportError(
                "SiliconFlow embedding 需要 langchain-openai。"
                "请运行: pip install langchain-openai"
            )

    elif provider == "dashscope":
        # 阿里云 DashScope
        try:
            from langchain_community.embeddings import DashScopeEmbeddings

            return DashScopeEmbeddings(
                model=settings.EMBEDDING_MODEL,
                dashscope_api_key=settings.LLM_API_KEY,
            )
        except ImportError:
            pass

    # 兜底：本地 Embedding（无需 API Key，离线可用）
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings

        return HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese",
        )
    except ImportError:
        raise ImportError(
            "未找到可用的 Embedding 提供者。"
            "请安装 langchain-openai（SiliconFlow/DashScope）或 "
            "langchain-community（本地 HuggingFace）"
        )
