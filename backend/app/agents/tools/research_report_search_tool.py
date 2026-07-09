"""研报搜索工具模块。

组合 Bocha 与 SearXNG 搜索能力，专门用于检索中文行业/券商研报。
优先使用 Bocha（若配置 API Key），失败时回退到 SearXNG。
结果统一归一化、按研报相关度打分排序并去重。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from app.agents.tools.bocha_search_tool import search_with_bocha
from app.agents.tools.searxng_search_tool import search_with_searxng
from app.config.settings import settings


# 研报相关关键词（用于打分）
_REPORT_KEYWORDS = ["研报", "研究报告", "深度", "行业", "证券"]

# 高相关域名（券商、研究所、财经平台）
_REPORT_DOMAINS = [
    "证券", "研究所", "券商",
    "eastmoney.com", "东方财富",
    "sina.com.cn", "新浪财经",
    "10jqka.com.cn", "同花顺",
    "qq.com", "腾讯自选股",
]


def _is_report_domain(url: str) -> bool:
    """判断 URL 域名是否属于高相关财经/券商来源。"""
    try:
        domain = urlparse(url).netloc.lower().lstrip("www.")
    except Exception:
        return False
    return any(kw in domain for kw in _REPORT_DOMAINS)


def _normalize_report_result(item: dict, query: str) -> dict:
    """从 Bocha/SearXNG 结果中统一提取研报字段。

    返回字段：
        rank, title, url, source, date, snippet, is_pdf, query
    """
    url = (item.get("url") or "").strip()
    title = (item.get("title") or "").strip()
    snippet = (item.get("snippet") or item.get("summary") or item.get("content") or "").strip()

    # 日期优先顺序：publishedDate / published_date / date
    date = (
        item.get("publishedDate")
        or item.get("published_date")
        or item.get("date")
        or item.get("published_at")
        or ""
    )
    if isinstance(date, str):
        date = date.strip()

    # 来源优先顺序：siteName / source / domain
    source = (
        item.get("siteName")
        or item.get("site_name")
        or item.get("source")
        or ""
    )
    if not source and url:
        try:
            source = urlparse(url).netloc.lower().lstrip("www.")
        except Exception:
            source = ""

    is_pdf = False
    if url.lower().endswith(".pdf"):
        is_pdf = True
    if "pdf" in title.lower():
        is_pdf = True

    return {
        "rank": item.get("rank") or 0,
        "title": title,
        "url": url,
        "source": source,
        "date": date,
        "snippet": snippet,
        "is_pdf": is_pdf,
        "query": query,
    }


def _rank_reports(results: list, query: str, max_results: int = 8) -> list:
    """按研报相关度打分排序，返回前 max_results 条。

    加分项：
        - 标题含研报关键词（研报/研究报告/深度/行业/证券）
        - 来源域名属于券商/研究所/财经平台
        - 有日期信息
        - 是 PDF 文件
    """
    scored = []
    for item in results:
        score = 0.0
        title = item.get("title") or ""
        url = item.get("url") or ""
        date = item.get("date") or ""
        is_pdf = item.get("is_pdf", False)

        # 标题关键词匹配
        title_lower = title.lower()
        for kw in _REPORT_KEYWORDS:
            if kw in title_lower:
                score += 2.0

        # 高相关域名
        if _is_report_domain(url):
            score += 1.5

        # 有日期
        if date:
            score += 1.0

        # PDF 文件
        if is_pdf:
            score += 1.0

        scored.append((score, item))

    scored.sort(key=lambda x: (-x[0], x[1].get("rank", 0)))
    return [item for _, item in scored[:max_results]]


def search_research_reports(query: str, max_results: int = 8) -> dict:
    """搜索研报，优先 Bocha，失败回退 SearXNG。

    Args:
        query: 搜索关键词。
        max_results: 返回结果数量上限。

    Returns:
        {
            "success": bool,
            "provider": str,
            "query": str,
            "results": [...],
            "total": int,
            "error": str (可选),
        }
    """
    provider = "bocha"
    raw_results: List[Dict[str, Any]] = []
    error_msg: Optional[str] = None

    # 优先 Bocha
    if settings.BOCHA_API_KEY:
        bocha_resp = search_with_bocha(query, max_results=max_results, summary=True)
        if bocha_resp.get("success"):
            raw_results = bocha_resp.get("results") or []
        else:
            error_msg = bocha_resp.get("error") or "Bocha search failed"
            provider = "searxng"
    else:
        provider = "searxng"

    # 回退 SearXNG
    if not raw_results:
        searxng_resp = search_with_searxng(query, max_results=max_results)
        if searxng_resp.get("success"):
            raw_results = searxng_resp.get("results") or []
        else:
            fallback_error = searxng_resp.get("error") or "SearXNG search failed"
            error_msg = f"{error_msg}; fallback: {fallback_error}" if error_msg else fallback_error

    if not raw_results:
        return {
            "success": False,
            "provider": provider,
            "query": query,
            "results": [],
            "total": 0,
            "error": error_msg or "No results",
        }

    # 归一化并过滤（要求 title 或 snippet 非空）
    normalized = []
    for item in raw_results:
        if not isinstance(item, dict):
            continue
        norm = _normalize_report_result(item, query)
        if norm["title"] or norm["snippet"]:
            normalized.append(norm)

    # 按相关度排序
    ranked = _rank_reports(normalized, query, max_results=max_results)

    # 按 URL 去重
    seen_urls: set[str] = set()
    deduped: list = []
    for item in ranked:
        url = item.get("url", "")
        if url and url in seen_urls:
            continue
        seen_urls.add(url)
        deduped.append(item)

    return {
        "success": bool(deduped),
        "provider": provider,
        "query": query,
        "results": deduped,
        "total": len(deduped),
        "error": error_msg if not deduped else None,
    }


def search_industry_research_reports(industry_name: str, max_results: int = 5) -> dict:
    """搜索指定行业的研报，组合多个查询词后合并去重。

    Args:
        industry_name: 行业名称。
        max_results: 返回结果数量上限。

    Returns:
        与 search_research_reports 返回格式一致的字典。
    """
    queries = [
        f"{industry_name} 行业研究报告 券商研报",
        f"{industry_name} 行业深度报告 PDF",
    ]

    all_results: list = []
    seen_urls: set[str] = set()

    for q in queries:
        resp = search_research_reports(q, max_results=max_results * 2)
        if not resp.get("success"):
            continue
        for item in resp.get("results", []):
            url = item.get("url", "")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            all_results.append(item)

    # 按原有相关度分数重新排序并截断
    ranked = _rank_reports(all_results, industry_name, max_results=max_results)

    # 再次确保去重（保险）
    final_seen: set[str] = set()
    final: list = []
    for item in ranked:
        url = item.get("url", "")
        if url and url in final_seen:
            continue
        if url:
            final_seen.add(url)
        final.append(item)

    return {
        "success": bool(final),
        "provider": "combined",
        "query": industry_name,
        "results": final,
        "total": len(final),
    }
