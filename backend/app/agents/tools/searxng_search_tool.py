"""SearXNG aggregated search provider.

SearXNG is treated as a public search aggregation gateway. It discovers
candidate evidence, but does not replace authoritative business, legal, or
financial data sources.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse

import httpx

from app.agents.tools.bocha_search_tool import source_confidence
from app.config import settings


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


def _normalize_item(item: Dict[str, Any], query: str, index: int) -> Dict[str, Any]:
    url = item.get("url") or ""
    trust_level, confidence, source_type = source_confidence(url)
    content = item.get("content") or item.get("snippet") or ""
    engines = item.get("engines") or item.get("engine") or []
    if isinstance(engines, str):
        engines = [engines]
    return {
        "title": item.get("title") or f"聚合搜索结果{index}",
        "url": url,
        "display_url": item.get("parsed_url") or url,
        "content": content,
        "snippet": content,
        "summary": content,
        "raw_content": content,
        "site_name": _domain(url),
        "published_at": item.get("publishedDate") or item.get("published_date") or "",
        "rank": index,
        "score": item.get("score") or max(0.2, 1 - (index - 1) * 0.05),
        "source": url or "SearXNG Search Gateway",
        "provider": "searxng",
        "source_type": source_type,
        "trust_level": trust_level,
        "confidence": confidence,
        "requires_manual_review": trust_level not in {"high"},
        "query": query,
        "metadata": {
            "engines": engines,
            "category": item.get("category"),
            "template": item.get("template"),
        },
    }


def search_with_searxng(
    query: str,
    max_results: Optional[int] = None,
    categories: Optional[str] = None,
    language: str = "zh-CN",
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Search through a SearXNG instance and normalize JSON results."""
    root = (base_url or settings.SEARXNG_BASE_URL or "").rstrip("/") + "/"
    if not root.strip("/"):
        return {"success": False, "provider": "searxng", "query": query, "error": "SEARXNG_BASE_URL not configured", "results": []}
    limit = max(1, min(int(max_results or settings.SEARXNG_MAX_RESULTS or 8), 50))
    params: Dict[str, Any] = {
        "q": query,
        "format": "json",
        "language": language or "zh-CN",
    }
    if categories:
        params["categories"] = categories

    try:
        response = httpx.get(urljoin(root, "search"), params=params, timeout=settings.SEARXNG_TIMEOUT_SECONDS)
    except Exception as exc:
        return {"success": False, "provider": "searxng", "query": query, "error": f"{type(exc).__name__}: {exc}", "results": []}

    content_type = response.headers.get("content-type", "")
    text_sample = response.text[:200].strip()
    if "text/html" in content_type or text_sample.lower().startswith("<!doctype html") or text_sample.lower().startswith("<html"):
        return {
            "success": False,
            "provider": "searxng",
            "query": query,
            "status_code": response.status_code,
            "error": "SearXNG returned HTML; enable JSON format in settings.yml search.formats.",
            "results": [],
        }
    if response.status_code >= 400:
        return {
            "success": False,
            "provider": "searxng",
            "query": query,
            "status_code": response.status_code,
            "error": f"SearXNG HTTP {response.status_code}: {text_sample}",
            "results": [],
        }

    try:
        data = response.json()
    except Exception as exc:
        return {"success": False, "provider": "searxng", "query": query, "error": f"Invalid JSON: {type(exc).__name__}: {exc}", "results": []}

    raw_results = data.get("results") or []
    if not isinstance(raw_results, list):
        return {"success": False, "provider": "searxng", "query": query, "error": "SearXNG JSON missing results array", "results": []}
    results = [_normalize_item(item, query, index) for index, item in enumerate(raw_results[:limit], 1) if isinstance(item, dict)]
    return {
        "success": bool(results),
        "provider": "searxng",
        "query": data.get("query") or query,
        "results": results,
        "unresponsive_engines": data.get("unresponsive_engines") or [],
        "suggestions": data.get("suggestions") or [],
        "answers": data.get("answers") or [],
    }
