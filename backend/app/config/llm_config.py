# ========================================
# LLM 配置
# ========================================

from langchain_openai import ChatOpenAI
from functools import lru_cache

from app.config import settings


@lru_cache()
def get_llm() -> ChatOpenAI:
    """获取 LLM 实例

    Returns:
        ChatOpenAI: LLM 实例
    """
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=0.3,
        max_tokens=4096,
        timeout=settings.LLM_TIMEOUT_SECONDS,
        max_retries=settings.LLM_MAX_RETRIES,
    )


