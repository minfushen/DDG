"""舆情/声誉风险监测工具。

通过公开网络搜索（Bocha 为主、SearXNG 兜底）发现企业负面/正面舆情线索，
按正/中/负分类并标注来源可信度。失败的搜索安全降级，不伪造结论。

注：公开搜索仅作为舆情线索，不替代司法/工商/财务权威源；重大负面需人工复核。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


NEGATIVE_KEYWORDS = [
    "处罚", "行政处罚", "诉讼", "被执行", "失信", "限高", "投诉", "维权", "举报",
    "监管", "立案", "退市", "造假", "欺诈", "负面", "舆情", "拖欠", "违约", "查封",
    "冻结", "警示", "问询函", "通报批评", "环境处罚", "税务处罚",
]
POSITIVE_KEYWORDS = [
    "中标", "增长", "获奖", "合作", "扩产", "利好", "突破", "获批", "签约",
    "增持", "回购", "入选", "认证", "订单", "盈利", "扭亏",
]


def classify_sentiment(text: str) -> str:
    """返回 negative / positive / neutral。"""
    text = (text or "").lower()
    neg = sum(1 for k in NEGATIVE_KEYWORDS if k.lower() in text)
    pos = sum(1 for k in POSITIVE_KEYWORDS if k.lower() in text)
    if neg > pos:
        return "negative"
    if pos > neg:
        return "positive"
    return "neutral"


def _normalize(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for r in results or []:
        if not isinstance(r, dict):
            continue
        title = r.get("title") or r.get("name") or ""
        snippet = r.get("snippet") or r.get("description") or r.get("summary") or r.get("content") or ""
        url = r.get("url") or r.get("link") or ""
        combined = f"{title} {snippet}"
        items.append({
            "title": title,
            "url": url,
            "snippet": snippet[:300],
            "source": r.get("source") or r.get("site") or (_domain(url) if url else "公开搜索"),
            "date": r.get("date") or r.get("published_at") or r.get("time") or "",
            "sentiment": classify_sentiment(combined),
        })
    return items


def _domain(url: str) -> str:
    try:
        from urllib.parse import urlparse

        net = urlparse(url).netloc
        return net.replace("www.", "") or url
    except Exception:
        return url


def search_enterprise_sentiment(enterprise_name: str, max_results: int = 10) -> Dict[str, Any]:
    """检索企业舆情线索并按情感分类。"""
    try:
        from app.agents.tools.bocha_search_tool import search_with_bocha

        query = f"{enterprise_name} 负面新闻 处罚 诉讼 失信 被执行 投诉 舆情 监管"
        res = search_with_bocha(query=query, max_results=max_results, freshness="noLimit", summary=True)
        if res.get("success"):
            items = _normalize(res.get("results", []))
            return {
                "success": True,
                "provider": "bocha",
                "enterprise_name": enterprise_name,
                "results": items,
                "error": "",
            }
        # SearXNG 兜底
        try:
            from app.agents.tools.searxng_search_tool import search_with_searxng

            res2 = search_with_searxng(query=query, max_results=max_results)
            if res2.get("success"):
                return {
                    "success": True,
                    "provider": "searxng",
                    "enterprise_name": enterprise_name,
                    "results": _normalize(res2.get("results", [])),
                    "error": "",
                }
        except Exception as exc:
            logger.warning("searxng sentiment fallback failed: %s", exc)
        return {
            "success": False,
            "provider": "bocha",
            "enterprise_name": enterprise_name,
            "results": [],
            "error": res.get("error") or "公开搜索未返回结果",
        }
    except Exception as exc:
        logger.warning("sentiment search failed: %s", exc)
        return {
            "success": False,
            "enterprise_name": enterprise_name,
            "results": [],
            "error": str(exc),
        }
