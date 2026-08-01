"""舆情/声誉风险分析报告生成器。"""

from __future__ import annotations

from typing import Any, Dict, List

_HIGH_TRUST_SUFFIX = ("gov.cn", "court.gov.cn", "creditchina.gov.cn", "gsxt.gov.cn", "cninfo.com.cn", "sse.cn", "szse.cn")


def _is_high_trust(source: str) -> bool:
    src = (source or "").lower()
    return any(src.endswith(s) or s in src for s in _HIGH_TRUST_SUFFIX)


def _risk_level(neg_count: int, neg_high_trust: int, pos_count: int) -> tuple[str, int, str]:
    if neg_high_trust > 0:
        return "high", 45, "检测到权威源（监管/司法/公示）负面舆情，建议授信前人工复核并关注后续进展。"
    if neg_count >= 3:
        return "high", 50, "负面舆情线索较多，建议核实事项真实性、影响范围与整改情况后审慎推进。"
    if neg_count >= 1:
        return "medium", 65, "存在负面舆情线索，建议结合权威源复核并纳入贷后监测。"
    if pos_count > 0:
        return "low", 85, "舆情整体偏正面，可结合权威渠道持续关注。"
    return "low", 80, "未检索到明显负面舆情，仍建议持续监测公开信息。"


def build_sentiment_report(enterprise_name: str, sentiment: Dict[str, Any]) -> Dict[str, Any]:
    enterprise_name = sentiment.get("enterprise_name") or enterprise_name
    items = sentiment.get("results", []) or []
    negative = [i for i in items if i.get("sentiment") == "negative"]
    positive = [i for i in items if i.get("sentiment") == "positive"]
    neutral = [i for i in items if i.get("sentiment") == "neutral"]
    neg_high_trust = [i for i in negative if _is_high_trust(i.get("source"))]

    rating, score, recommendation = _risk_level(len(negative), len(neg_high_trust), len(positive))

    summary = {
        "检索结果": len(items),
        "负面": len(negative),
        "正面": len(positive),
        "中性": len(neutral),
        "权威源负面": len(neg_high_trust),
    }

    risk_tags: List[Dict[str, str]] = []
    if neg_high_trust:
        risk_tags.append({"tag": "权威源负面舆情", "level": "high", "detail": f"{len(neg_high_trust)}条来自监管/司法/公示渠道的负面舆情，需重点复核。"})
    elif negative:
        risk_tags.append({"tag": "负面舆情线索", "level": "medium", "detail": f"检索到{len(negative)}条负面舆情线索，需结合权威源核实。"})
    else:
        risk_tags.append({"tag": "舆情平稳", "level": "low", "detail": "未检索到明显负面舆情。"})

    risk_summary = [t["detail"] for t in risk_tags]

    sections = [
        {
            "title": "一、舆情概览",
            "summary": [
                {"label": "检索结果", "value": len(items)},
                {"label": "负面", "value": len(negative)},
                {"label": "正面", "value": len(positive)},
                {"label": "权威源负面", "value": len(neg_high_trust)},
            ],
            "analysis": [
                f"基于{sentiment.get('provider', '公开搜索')}检索{enterprise_name}相关公开舆情，共{len(items)}条结果。",
                "公开搜索仅作舆情线索，重大负面需以监管/司法/公示权威源人工复核为准。",
            ],
        },
        {
            "title": "二、负面舆情线索",
            "items": [
                {"title": i.get("title"), "source": i.get("source"), "date": i.get("date"), "url": i.get("url")}
                for i in negative[:10]
            ] if negative else [],
            "analysis": [f"共{len(negative)}条负面线索" + (f"，其中{len(neg_high_trust)}条来自权威源。" if neg_high_trust else "。")],
        },
        {
            "title": "三、正面舆情线索",
            "items": [
                {"title": i.get("title"), "source": i.get("source"), "date": i.get("date")}
                for i in positive[:6]
            ] if positive else [],
        },
        {
            "title": "四、声誉风险评级",
            "summary": [{"label": "风险评级", "value": rating}, {"label": "风险评分", "value": score}],
            "tags": risk_tags,
        },
    ]

    evidence = [
        {"label": "声誉风险评级", "value": f"{rating}/{score}", "source": sentiment.get("provider", "公开搜索")},
        {"label": "负面舆情", "value": f"{len(negative)}条", "source": "公开搜索"},
    ]

    return {
        "report_type": "sentiment_analysis",
        "enterprise_name": enterprise_name,
        "generated_from": f"{sentiment.get('provider', '公开搜索')}舆情监测",
        "risk_rating": rating,
        "risk_score": score,
        "recommendation": recommendation,
        "summary": summary,
        "negative_items": negative,
        "positive_items": positive,
        "neutral_items": neutral,
        "sections": sections,
        "risk_tags": risk_tags,
        "risk_summary": risk_summary,
        "evidence": evidence,
    }
