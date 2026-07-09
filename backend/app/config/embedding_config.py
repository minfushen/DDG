# backend/app/config/embedding_config.py
"""Embedding 模型配置"""
import json
import unicodedata
from typing import List
from urllib import error, request

from functools import lru_cache

from app.config import settings
from app.config.rag_loader import get_embedding_config


class SiliconFlowEmbeddings:
    """Minimal LangChain-compatible embeddings client for SiliconFlow."""

    def __init__(
        self,
        api_key: str,
        base_url: str,
        model: str,
        batch_size: int | None = None,
        max_chars: int | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        emb_cfg = get_embedding_config()
        self.batch_size = batch_size if batch_size is not None else emb_cfg.get("batch_size", 1)
        self.max_chars = max_chars if max_chars is not None else emb_cfg.get("max_chars", 500)
        self.timeout = timeout if timeout is not None else emb_cfg.get("timeout_seconds", 60)

    def _embed_batch(self, texts: List[str]) -> List[List[float]]:
        payload = json.dumps({"model": self.model, "input": texts}).encode("utf-8")
        req = request.Request(
            f"{self.base_url}/embeddings",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"SiliconFlow embedding request failed: {exc.code} {detail}") from exc
        return [item["embedding"] for item in sorted(result.get("data", []), key=lambda x: x.get("index", 0))]

    def _embed(self, texts: List[str]) -> List[List[float]]:
        vectors: List[List[float]] = []
        cleaned = [
            (unicodedata.normalize("NFKC", text).strip() or "空白文本")[:self.max_chars]
            for text in texts
        ]
        for index in range(0, len(cleaned), self.batch_size):
            vectors.extend(self._embed_batch(cleaned[index:index + self.batch_size]))
        return vectors

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._embed(texts)

    def embed_query(self, text: str) -> List[float]:
        return self._embed([text])[0]


@lru_cache()
def get_embedding_model():
    """
    获取 Embedding 模型实例

    Returns:
        Embedding 模型实例
    """
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "siliconflow":
        return SiliconFlowEmbeddings(
            api_key=settings.EMBEDDING_API_KEY,
            base_url=settings.EMBEDDING_BASE_URL,
            model=settings.EMBEDDING_MODEL_ID,
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
