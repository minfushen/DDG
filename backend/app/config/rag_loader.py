# backend/app/config/rag_loader.py
"""Unified loader for RAG configuration stored in config/rag.yaml.

Keeps retrieval top-k, embedding client tunables and ingestion flags out of
source code.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

from app.config import settings


DEFAULT_RAG_PATH: Path = settings.BASE_DIR / "config" / "rag.yaml"


@lru_cache()
def _load_rag_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Load and cache the RAG YAML config."""
    path = Path(config_path) if config_path else DEFAULT_RAG_PATH
    if not path.exists():
        raise FileNotFoundError(f"RAG config not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    if not isinstance(config, dict):
        raise ValueError(f"RAG config root must be a mapping: {path}")
    return config


def get_rag_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Return the full RAG config dictionary."""
    return _load_rag_config(config_path)


def get_legal_search_top_k(variant: str = "default", config_path: Path | str | None = None) -> int:
    """Return legal-search top_k for a given variant.

    Args:
        variant: ``default`` or ``summary``.
    """
    config = _load_rag_config(config_path)
    retrieval = config.get("retrieval") or {}
    legal = retrieval.get("legal_search") or {}
    key = f"{variant}_top_k"
    value = legal.get(key)
    return int(value) if isinstance(value, (int, float)) else (10 if variant == "default" else 5)


def get_knowledge_retrieval_top_k(
    variant: str = "financial",
    config_path: Path | str | None = None,
) -> int:
    """Return knowledge-retrieval top_k for a given variant.

    Args:
        variant: One of ``financial``, ``industry``, ``research``.
    """
    config = _load_rag_config(config_path)
    retrieval = config.get("retrieval") or {}
    knowledge = retrieval.get("knowledge") or {}
    key = f"{variant}_default"
    value = knowledge.get(key)
    return int(value) if isinstance(value, (int, float)) else 5


def get_knowledge_fallback_split_ratio(config_path: Path | str | None = None) -> float:
    """Return the fallback split ratio used when reducing top_k."""
    config = _load_rag_config(config_path)
    retrieval = config.get("retrieval") or {}
    knowledge = retrieval.get("knowledge") or {}
    value = knowledge.get("fallback_split_ratio")
    return float(value) if isinstance(value, (int, float)) else 0.5


def get_embedding_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Return embedding client tunables."""
    config = _load_rag_config(config_path)
    return config.get("embedding") or {}


def get_vector_store_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Return vector-store settings."""
    config = _load_rag_config(config_path)
    return config.get("vector_store") or {}


def get_ingestion_config(config_path: Path | str | None = None) -> Dict[str, Any]:
    """Return ingestion/auto-ingest settings."""
    config = _load_rag_config(config_path)
    return config.get("ingestion") or {}
