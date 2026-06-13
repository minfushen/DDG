"""Bocha web search provider.

Bocha is used as a Chinese public-web perception tool. It should discover
candidate public evidence, not replace authoritative registry, judicial, or
financial data providers.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type
from urllib.parse import urlparse
import json

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import httpx

from app.config import settings


BOCHA_WEB_SEARCH_URL = "https://api.bocha.cn/v1/web-search"

HIGH_TRUST_DOMAINS = [
    "gov.cn",
    "court.gov.cn",
    "wenshu.court.gov.cn",
    "zxgk.court.gov.cn",
    "creditchina.gov.cn",
    "gsxt.gov.cn",
    "cninfo.com.cn",
    "static.cninfo.com.cn",
    "sse.com.cn",
    "szse.cn",
    "neeq.com.cn",
]
MEDIUM_TRUST_DOMAINS = [
    "eastmoney.com",
    "cs.com.cn",
    "cnstock.com",
    "stcn.com",
    "qcc.com",
    "tianyancha.com",
    "aiqicha.baidu.com",
    "aiqicha.com",
    "qixin.com",
    "jiansheku.com",
]
LOW_TRUST_DOMAINS = [
    "renrendoc.com",
    "doc88.com",
    "wenku.baidu.com",
    "sohu.com",
    "toutiao.com",
]


class BochaWebSearchInput(BaseModel):
    query: str = Field(description="搜索关键词")
    count: int = Field(default=8, description="返回结果数量，1-50")
    freshness: str = Field(default="noLimit", description="时间范围：noLimit/oneDay/oneWeek/oneMonth/oneYear/日期范围")
    summary: bool = Field(default=True, description="是否返回网页摘要")
    include: str = Field(default="", description="限定搜索域名，多个用 | 或 , 分隔")
    exclude: str = Field(default="", description="排除搜索域名，多个用 | 或 , 分隔")


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


def _domain_matches(domain: str, candidates: List[str]) -> bool:
    return any(domain == item or domain.endswith("." + item) or item in domain for item in candidates)


def source_confidence(url: str) -> tuple[str, float, str]:
    domain = _domain(url)
    if _domain_matches(domain, HIGH_TRUST_DOMAINS):
        return "high", 0.86, "official_or_authoritative_public_source"
    if _domain_matches(domain, MEDIUM_TRUST_DOMAINS):
        return "medium", 0.72, "commercial_or_mainstream_public_source"
    if _domain_matches(domain, LOW_TRUST_DOMAINS):
        return "low", 0.42, "low_reliability_public_source"
    return "low_to_medium", 0.58, "public_web_search_clue"


def _normalize_time(value: Any) -> str:
    text = str(value or "").strip()
    if text.endswith("Z") and "T" in text:
        # Bocha v1 notes dateLastCrawled is actually UTC+8 despite the Z suffix.
        return text[:-1] + "+08:00"
    return text


def _normalize_item(item: Dict[str, Any], query: str, index: int) -> Dict[str, Any]:
    url = item.get("url") or ""
    trust_level, confidence, source_type = source_confidence(url)
    content = item.get("summary") or item.get("snippet") or ""
    published_at = _normalize_time(item.get("datePublished") or item.get("dateLastCrawled"))
    return {
        "title": item.get("name") or item.get("title") or f"博查搜索结果{index}",
        "url": url,
        "display_url": item.get("displayUrl") or url,
        "content": content,
        "snippet": item.get("snippet") or "",
        "summary": item.get("summary") or "",
        "raw_content": content,
        "site_name": item.get("siteName") or _domain(url),
        "site_icon": item.get("siteIcon"),
        "published_at": published_at,
        "date_published": _normalize_time(item.get("datePublished")),
        "date_last_crawled": _normalize_time(item.get("dateLastCrawled")),
        "language": item.get("language"),
        "rank": index,
        "score": max(0.2, 1 - (index - 1) * 0.06),
        "source": url or "Bocha Web Search",
        "provider": "bocha",
        "source_type": source_type,
        "trust_level": trust_level,
        "confidence": confidence,
        "requires_manual_review": trust_level not in {"high"},
        "query": query,
    }


def search_with_bocha(
    query: str,
    max_results: int = 8,
    freshness: str = "noLimit",
    summary: bool = True,
    include: str = "",
    exclude: str = "",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """Search public web pages through Bocha and normalize results."""
    key = api_key or settings.BOCHA_API_KEY
    if not key:
        return {"success": False, "provider": "bocha", "error": "BOCHA_API_KEY not configured", "results": []}

    count = max(1, min(int(max_results or 8), 50))
    payload: Dict[str, Any] = {
        "query": query,
        "freshness": freshness or "noLimit",
        "summary": bool(summary),
        "count": count,
    }
    if include:
        payload["include"] = include
    if exclude:
        payload["exclude"] = exclude

    try:
        response = httpx.post(
            BOCHA_WEB_SEARCH_URL,
            json=payload,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=settings.BOCHA_SEARCH_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        return {"success": False, "provider": "bocha", "query": query, "error": f"{type(exc).__name__}: {exc}", "results": []}

    if data.get("code") not in (None, 200):
        return {
            "success": False,
            "provider": "bocha",
            "query": query,
            "error": data.get("msg") or f"Bocha API code={data.get('code')}",
            "log_id": data.get("log_id"),
            "results": [],
        }

    web_pages = ((data.get("data") or {}).get("webPages") or {})
    values = web_pages.get("value") or []
    results = [_normalize_item(item, query, index) for index, item in enumerate(values[:count], 1) if isinstance(item, dict)]
    return {
        "success": bool(results),
        "provider": "bocha",
        "query": query,
        "results": results,
        "total_estimated_matches": web_pages.get("totalEstimatedMatches"),
        "some_results_removed": web_pages.get("someResultsRemoved"),
        "original_query": ((data.get("data") or {}).get("queryContext") or {}).get("originalQuery") or query,
        "log_id": data.get("log_id"),
        "raw_code": data.get("code"),
    }


class BochaWebSearchTool(BaseTool):
    name: str = "bocha_web_search"
    description: str = "通过博查 Web Search 搜索中文公开网页线索，适合企业公告、司法风险、工商线索、行业资料和舆情检索。"
    args_schema: Type[BaseModel] = BochaWebSearchInput

    def _run(self, query: str, count: int = 8, freshness: str = "noLimit", summary: bool = True, include: str = "", exclude: str = "") -> str:
        return json.dumps(
            search_with_bocha(
                query=query,
                max_results=count,
                freshness=freshness,
                summary=summary,
                include=include,
                exclude=exclude,
            ),
            ensure_ascii=False,
        )


bocha_web_search = BochaWebSearchTool()
