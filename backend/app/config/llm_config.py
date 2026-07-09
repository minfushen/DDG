# ========================================
# LLM 配置
# ========================================

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any, Optional, Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from app.api import cache_store
from app.config import settings

logger = logging.getLogger(__name__)


# provider -> 默认连接配置。api_key 统一使用 settings.LLM_API_KEY；
# 原生 SDK 分支以 "sdk" 标识，调用时延迟导入对应依赖。
_LLM_PROVIDER_PRESETS: dict[str, dict] = {
    "openai": {"base_url": None},                      # 走 settings.LLM_BASE_URL
    "openai_compatible": {"base_url": None},           # 走 settings.LLM_BASE_URL
    "dashscope": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    "qwen": {"base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1"},
    "deepseek": {"base_url": "https://api.deepseek.com/v1"},
    "ollama": {"base_url": "http://localhost:11434/v1"},
    "zhipu": {"sdk": "zhipu"},
    "glm": {"sdk": "zhipu"},
    "anthropic": {"sdk": "anthropic"},
    "claude": {"sdk": "anthropic"},
    "gemini": {"sdk": "gemini"},
}


def _resolve_provider(provider: str | None) -> str:
    """解析 provider 标识，未知值回落到 openai_compatible。"""
    if not provider:
        provider = settings.LLM_PROVIDER or "openai_compatible"
    provider = provider.lower().strip()
    if provider not in _LLM_PROVIDER_PRESETS:
        logger.warning("未知 LLM_PROVIDER=%r，回落到 openai_compatible", provider)
        return "openai_compatible"
    return provider


def _build_client(
    provider: str,
    *,
    model: str,
    api_key: str,
    base_url: str | None,
    temperature: float,
    max_tokens: int,
    timeout: int,
    max_retries: int,
    model_kwargs: dict | None = None,
) -> BaseChatModel:
    """按 provider 构造对应的对话模型客户端。"""
    preset = _LLM_PROVIDER_PRESETS[provider]
    sdk = preset.get("sdk")

    if sdk == "zhipu":
        try:
            from langchain_community.chat_models import ChatZhipuAI
        except ImportError as exc:
            raise ImportError(
                "使用 zhipu/glm 供应商需安装 langchain-community：pip install langchain-community"
            ) from exc
        return ChatZhipuAI(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **(model_kwargs or {}),
        )
    if sdk == "anthropic":
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise ImportError(
                "使用 anthropic/claude 供应商需安装 langchain-anthropic：pip install langchain-anthropic"
            ) from exc
        return ChatAnthropic(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **(model_kwargs or {}),
        )
    if sdk == "gemini":
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
        except ImportError as exc:
            raise ImportError(
                "使用 gemini 供应商需安装 langchain-google-genai：pip install langchain-google-genai"
            ) from exc
        return ChatGoogleGenerativeAI(
            model=model,
            google_api_key=api_key,
            temperature=temperature,
            max_output_tokens=max_tokens,
            timeout=timeout,
            max_retries=max_retries,
            **(model_kwargs or {}),
        )

    # OpenAI 兼容分支（openai / dashscope / deepseek / ollama / openai_compatible）
    resolved_base_url = base_url or preset.get("base_url") or settings.LLM_BASE_URL
    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=resolved_base_url,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        max_retries=max_retries,
        **(model_kwargs or {}),
    )


@lru_cache(maxsize=64)
def get_llm(
    *,
    model: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: int | None = None,
    max_retries: int | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    response_format: str | None = None,
    provider: str | None = None,
) -> BaseChatModel:
    """获取 LLM 实例（集中配置 + 多 provider 抽象 + 参数覆盖 + 缓存复用）。

    所有 LLM 调用都应经由本函数构造，避免各处自行 ``new ChatOpenAI``
    导致的配置漂移。相同参数组合共享同一实例（lru_cache）。

    provider 决定底层后端 SDK 与默认连接配置（仿 embedding_config 的多
    provider 模式）：

    - ``openai_compatible`` / ``openai``：ChatOpenAI，连接 ``LLM_BASE_URL``。
    - ``dashscope`` / ``qwen``：ChatOpenAI 兼容网关（DashScope compatible-mode）。
    - ``deepseek``：ChatOpenAI 兼容网关（api.deepseek.com）。
    - ``ollama``：ChatOpenAI 兼容网关（本地 11434）。
    - ``zhipu`` / ``glm``：ChatZhipuAI（需 ``pip install langchain-community``）。
    - ``anthropic`` / ``claude``：ChatAnthropic（需 ``pip install langchain-anthropic``）。
    - ``gemini``：ChatGoogleGenerativeAI（需 ``pip install langchain-google-genai``）。

    显式传入的 model / api_key / base_url 始终优先于 provider 预设。

    Args:
        model: 模型 ID，默认 ``settings.LLM_MODEL``。
        temperature: 采样温度，默认 ``0.3``。
        max_tokens: 生成上限，默认 ``4096``。
        timeout: 超时秒数，默认 ``settings.LLM_TIMEOUT_SECONDS``。
        max_retries: 失败重试次数，默认 ``settings.LLM_MAX_RETRIES``。
        api_key / base_url: 覆盖主配置（备用 LLM / 研究规划器等）。
        response_format: 传 ``"json_object"`` 时注入 model_kwargs 要求结构化输出。
        provider: 供应商标识，默认 ``settings.LLM_PROVIDER``。
    """
    eff_provider = _resolve_provider(provider)
    model_kwargs: dict[str, Any] = {}
    if response_format:
        model_kwargs["response_format"] = {"type": response_format}

    return _build_client(
        eff_provider,
        model=model or settings.LLM_MODEL,
        api_key=api_key or settings.LLM_API_KEY,
        base_url=base_url,
        temperature=temperature if temperature is not None else 0.3,
        max_tokens=max_tokens or 4096,
        timeout=timeout or settings.LLM_TIMEOUT_SECONDS,
        max_retries=max_retries if max_retries is not None else settings.LLM_MAX_RETRIES,
        model_kwargs=model_kwargs,
    )


@lru_cache()
def get_analysis_llm_pool() -> list[tuple[str, ChatOpenAI]]:
    """分析诊断 LLM 池：返回 (model_id, ChatOpenAI) 列表。

    池按 ``settings.ANALYSIS_LLM_MODELS``（逗号分隔）实例化，复用主 LLM 的
    API key / base_url。用于年报经营讨论章节深度归因抽取、财务/行业叙述
    多模型竞速，降低单模型失败或额度耗尽风险。

    池中第一个模型视作"主力深读"模型（max 系列，长上下文稳健），其余为
    竞速/兜底选手。当列表为空或配置缺失时返回空列表，由调用方决定回退。
    """
    raw_models = (settings.ANALYSIS_LLM_MODELS or "").strip()
    if not raw_models or not settings.LLM_API_KEY or not settings.LLM_BASE_URL:
        return []
    model_ids = [m.strip() for m in raw_models.split(",") if m.strip()]
    pool: list[tuple[str, ChatOpenAI]] = []
    for model_id in model_ids:
        try:
            pool.append((
                model_id,
                get_llm(
                    model=model_id,
                    temperature=0,
                    max_tokens=settings.ANALYSIS_LLM_MAX_TOKENS,
                    timeout=settings.ANALYSIS_LLM_TIMEOUT_SECONDS,
                    max_retries=1,
                    response_format="json_object",
                ),
            ))
        except Exception as exc:  # 配置异常不应阻塞整个池
            logger.warning("Failed to init analysis LLM %s: %s", model_id, exc)
    return pool


def get_primary_attribution_llm() -> tuple[str, ChatOpenAI] | None:
    """归因抽取的主力深读模型（池中第一个 max 系列）。"""
    pool = get_analysis_llm_pool()
    for name, llm in pool:
        if "max" in name:
            return name, llm
    return pool[0] if pool else None


def _serialize_llm_response(response: BaseMessage) -> dict[str, Any]:
    """Serialize a LangChain BaseMessage for cache storage."""
    return {
        "content": str(getattr(response, "content", "")),
        "type": getattr(response, "type", "ai"),
        "response_metadata": getattr(response, "response_metadata", {}) or {},
        "id": getattr(response, "id", None),
        "name": getattr(response, "name", None),
        "tool_calls": getattr(response, "tool_calls", None),
    }


def _deserialize_llm_response(data: dict[str, Any]) -> BaseMessage:
    """Reconstruct a BaseMessage-like object from cached data."""
    from langchain_core.messages import AIMessage

    return AIMessage(
        content=data.get("content", ""),
        response_metadata=data.get("response_metadata", {}) or {},
        id=data.get("id"),
        name=data.get("name"),
        tool_calls=data.get("tool_calls"),
    )


def cached_invoke(
    llm: BaseChatModel,
    prompt: Union[str, list[Any]],
    *,
    cache_key: Optional[str] = None,
    ttl_seconds: Optional[int] = None,
    use_cache: Optional[bool] = None,
    session_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> BaseMessage:
    """Invoke *llm* with optional response caching.

    The cache key is derived from the model name, temperature, and the prompt
    content unless an explicit *cache_key* is provided.  This is useful for
    deterministic, high-cost calls such as research planning and narrative
    generation during development and repeated due-diligence runs.

    When *session_id* is provided and short-term memory is enabled, the prompt
    and response summaries are recorded so that downstream reasoning steps can
    see what has already been asked/answered.
    """
    if use_cache is None:
        use_cache = settings.ENABLE_LLM_CACHE

    key = cache_key
    if use_cache:
        key = key or cache_store.llm_cache_key(
            getattr(llm, "model_name", ""),
            llm.temperature,
            prompt,
        )
        cached = cache_store.get_llm_cache(key)
        if cached is not None:
            return _deserialize_llm_response(cached["response"])

    stm = None
    if settings.ENABLE_SHORT_TERM_MEMORY and session_id:
        from app.memory import ShortTermMemory

        stm = ShortTermMemory(session_id=session_id, task_id=task_id)
        try:
            prompt_summary = str(prompt)[:240]
            stm.add_user_message(f"LLM prompt: {prompt_summary}")
        except Exception as exc:
            logger.debug("Failed to record LLM prompt in STM: %s", exc)

    response = llm.invoke(prompt)

    if stm is not None:
        try:
            content_summary = str(getattr(response, "content", response))[:240]
            stm.add_assistant_message(f"LLM response: {content_summary}")
        except Exception as exc:
            logger.debug("Failed to record LLM response in STM: %s", exc)

    if use_cache and key is not None:
        try:
            cache_store.set_llm_cache(
                key,
                getattr(llm, "model_name", ""),
                prompt,
                _serialize_llm_response(response),
                ttl_seconds or settings.LLM_CACHE_TTL_SECONDS,
            )
        except Exception as exc:
            logger.warning("Failed to write LLM cache: %s", exc)

    return response
