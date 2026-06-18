"""Public search post-processing pipeline.

This module turns raw search-provider results into auditable Evidence:
clean -> dedupe -> optional page reading -> field extraction -> evidence.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Tuple
from urllib.parse import urldefrag, urlparse
import re

from app.agents.evidence import normalize_evidence
from app.agents.evidence.source_intelligence import collect_result_text, enrich_public_result

from app.config import settings


NOISE_DOMAINS = {
    "hanyuguoxue.com",
    "zdic.net",
    "zidian.911cha.com",
}

NOISE_TITLE_PATTERNS = [
    r"^[\u4e00-\u9fa5]（汉语汉字）",
    r"^[\u4e00-\u9fa5]的意思",
    r"^[\u4e00-\u9fa5]的解释",
    r"^[\u4e00-\u9fa5]_百度百科$",
    r"笔顺",
    r"拼音",
    r"部首",
]


def _get_crawl4ai_reader():
    """Return the crawl4ai reader function if available, otherwise None.

    Extracted to module level so tests can monkeypatch it.
    """
    try:
        from app.agents.tools.crawl4ai_reader_tool import fetch_url_with_crawl4ai
        return fetch_url_with_crawl4ai
    except ImportError:
        return None


def process_public_search_results(
    *,
    provider_results: Iterable[Dict[str, Any]],
    category: str,
    query: str,
    agent: str | None = None,
    crawl_enabled: bool | None = None,
    max_results: int = 8,
    max_crawl_pages: int | None = None,
) -> Dict[str, Any]:
    """Convert raw search results into normalized evidence and crawl attempts."""
    agent_name = agent or category or "general"
    raw_results = list(provider_results or [])
    cleaned, filtered = clean_and_dedupe_results(raw_results, max_results=max_results)
    evidence: List[Dict[str, Any]] = []
    for item in cleaned:
        evidence.append(normalize_evidence(_search_result_evidence(item, category, query), agent=agent_name, domain=category))

    attempts: List[Dict[str, Any]] = []
    if settings.ENABLE_CRAWL4AI_READER if crawl_enabled is None else crawl_enabled:
        fetch_url_with_crawl4ai = _get_crawl4ai_reader()
        selected = select_results_for_crawl(cleaned, category, max_pages=max_crawl_pages or settings.CRAWL4AI_MAX_PAGES_PER_TASK)
        for item in selected:
            url = item.get("url") or item.get("source_url")
            if fetch_url_with_crawl4ai is None:
                attempts.append({"url": url, "success": False, "error": "crawl4ai_reader_tool not available"})
                continue
            result = fetch_url_with_crawl4ai(url=url, query_context=query, max_chars=8000)
            attempts.append({"url": url, "success": result.get("success"), "error": result.get("error")})
            if not result.get("success"):
                continue
            evidence.append(normalize_evidence(_crawled_page_evidence(item, result, category, query), agent=agent_name, domain=category))

    return {
        "evidence": evidence,
        "cleaned_results": cleaned,
        "filtered_results": filtered,
        "crawl_attempts": attempts,
        "stats": {
            "input_count": len(raw_results),
            "cleaned_count": len(cleaned),
            "filtered_count": len(filtered),
            "evidence_count": len(evidence),
            "crawl_attempt_count": len(attempts),
        },
    }


def clean_and_dedupe_results(results: Iterable[Dict[str, Any]], max_results: int = 8) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    cleaned: List[Dict[str, Any]] = []
    filtered: List[Dict[str, Any]] = []
    seen_urls = set()
    for item in results or []:
        if not isinstance(item, dict):
            continue
        normalized_url = _normalize_url(item.get("url") or item.get("source_url") or "")
        if normalized_url and normalized_url in seen_urls:
            filtered.append({**item, "filter_reason": "duplicate_url"})
            continue
        if _is_noise_result(item):
            filtered.append({**item, "filter_reason": "noise_result"})
            continue
        if normalized_url:
            seen_urls.add(normalized_url)
        cleaned.append({**item, "url": item.get("url") or item.get("source_url"), "normalized_url": normalized_url})
        if len(cleaned) >= max_results:
            break
    cleaned.sort(key=_result_rank_score, reverse=True)
    return cleaned, filtered


def select_results_for_crawl(results: List[Dict[str, Any]], category: str, max_pages: int = 3) -> List[Dict[str, Any]]:
    selected = []
    for item in results:
        if not item.get("url"):
            continue
        enrichment = enrich_public_result(item, category)
        source_type = item.get("source_type") or enrichment.get("source_type") or ""
        trust = item.get("trust_level") or enrichment.get("trust_level") or "low"
        if trust == "high" or source_type in {"exchange_announcement", "public_disclosure", "official_judicial_source", "official_business_registry"}:
            selected.append(item)
        elif category in {"industry", "financial", "legal"} and trust in {"medium", "low_to_medium"}:
            selected.append(item)
        if len(selected) >= max(1, int(max_pages or 3)):
            break
    return selected


def _search_result_evidence(item: Dict[str, Any], category: str, query: str) -> Dict[str, Any]:
    enrichment = enrich_public_result(item, category)
    title = item.get("title") or item.get("label") or item.get("url") or "公开资料线索"
    label = _label_for_category(category, crawled=False)
    return {
        "label": label,
        "value": title,
        "claim": f"公开资料检索命中：{title}",
        "source": item.get("source") or item.get("url") or item.get("provider") or "公开资料检索",
        "source_name": item.get("site_name") or item.get("source_name") or _domain(item.get("url") or "") or "公开资料检索",
        "source_url": item.get("url"),
        "source_type": item.get("source_type") or enrichment.get("source_type") or "public_web_search_clue",
        "confidence": item.get("confidence") or enrichment.get("confidence"),
        "trust_level": item.get("trust_level") or enrichment.get("trust_level"),
        "requires_manual_review": item.get("requires_manual_review") if "requires_manual_review" in item else enrichment.get("trust_level") != "high",
        "metadata": {
            **item,
            **enrichment,
            "query": query,
            "pipeline_stage": "search_result",
            "display_tool_name": "公开资料检索",
        },
    }


def _crawled_page_evidence(base_item: Dict[str, Any], crawl_result: Dict[str, Any], category: str, query: str) -> Dict[str, Any]:
    markdown = crawl_result.get("cleaned_markdown") or ""
    pseudo_item = {
        "url": crawl_result.get("url") or base_item.get("url"),
        "title": crawl_result.get("title") or base_item.get("title"),
        "content": markdown,
        "raw_content": markdown,
        "source": base_item.get("source") or base_item.get("url"),
        "source_name": base_item.get("source_name") or base_item.get("site_name"),
    }
    enrichment = enrich_public_result(pseudo_item, category)
    title = crawl_result.get("title") or base_item.get("title") or base_item.get("url")
    return {
        "label": _label_for_category(category, crawled=True),
        "value": title,
        "claim": f"已读取公开网页正文：{title}",
        "source": base_item.get("source") or base_item.get("url") or "网页正文解析",
        "source_name": base_item.get("source_name") or base_item.get("site_name") or _domain(base_item.get("url") or "") or "网页正文解析",
        "source_url": base_item.get("url") or crawl_result.get("url"),
        "source_type": "crawled_web_page",
        "confidence": base_item.get("confidence") or enrichment.get("confidence") or 0.72,
        "trust_level": base_item.get("trust_level") or enrichment.get("trust_level") or "medium",
        "requires_manual_review": (base_item.get("trust_level") or enrichment.get("trust_level")) != "high",
        "metadata": {
            "query": query,
            "pipeline_stage": "crawled_page",
            "display_tool_name": "网页正文解析",
            "cleaned_markdown": markdown,
            "text_excerpt": crawl_result.get("text_excerpt") or collect_result_text(pseudo_item)[:800],
            "page_metadata": crawl_result.get("metadata") or {},
            "extracted_fields": enrichment.get("extracted_fields") or {},
            "base_search_result": base_item,
        },
    }


def _is_noise_result(item: Dict[str, Any]) -> bool:
    title = str(item.get("title") or item.get("label") or "")
    url = str(item.get("url") or item.get("source_url") or "")
    domain = _domain(url)
    if domain in NOISE_DOMAINS:
        return True
    if "baike.baidu.com" in domain and _single_character_baike(title):
        return True
    return any(re.search(pattern, title) for pattern in NOISE_TITLE_PATTERNS)


def _single_character_baike(title: str) -> bool:
    return bool(re.match(r"^[\u4e00-\u9fa5]（汉语汉字）", title or ""))


def _normalize_url(url: str) -> str:
    if not url:
        return ""
    clean, _ = urldefrag(str(url).strip())
    return clean.rstrip("/")


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return ""


def _label_for_category(category: str, crawled: bool) -> str:
    if crawled:
        return {
            "financial": "财报/公告网页正文",
            "legal": "司法/合规网页正文",
            "industry": "行业/经营网页正文",
            "business": "工商网页正文",
        }.get(category, "公开网页正文")
    return {
        "financial": "财报/业绩公开资料",
        "legal": "司法/合规公开线索",
        "industry": "行业/经营公开线索",
        "business": "工商公开线索",
    }.get(category, "公开搜索线索")


def _result_rank_score(item: Dict[str, Any]) -> float:
    trust = item.get("trust_level") or ""
    trust_score = {"high": 3, "medium": 2, "low_to_medium": 1.5, "low": 1}.get(trust, 1)
    source_type = item.get("source_type") or ""
    authority_bonus = 1 if source_type in {"exchange_announcement", "public_disclosure", "official_judicial_source", "official_business_registry"} else 0
    provider_score = float(item.get("score") or 0.5)
    return trust_score + authority_bonus + provider_score
